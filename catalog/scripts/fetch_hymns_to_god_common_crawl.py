#!/usr/bin/env python3
"""Fill HymnsToGod cache gaps from a pinned Common Crawl collection."""

from __future__ import annotations

import argparse
import base64
import gzip
import hashlib
import json
from pathlib import Path
import time
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from inventory_hymns_to_god import (
    USER_AGENT,
    _url_key,
    choose_source_variant,
    load_cdx_snapshots,
    parse_index,
    parse_page,
)


DEFAULT_INDEX = "CC-MAIN-2026-30"


class CommonCrawlError(ValueError):
    """Raised when a Common Crawl record cannot be verified and extracted."""


def _get(url: str, *, headers: dict[str, str] | None = None) -> bytes:
    request_headers = {"User-Agent": USER_AGENT, **(headers or {})}
    last_error: Exception | None = None
    for attempt in range(1, 4):
        try:
            with urlopen(Request(url, headers=request_headers), timeout=60) as response:
                return response.read()
        except Exception as exc:
            last_error = exc
            if attempt < 3:
                time.sleep(2 ** (attempt - 1))
    raise CommonCrawlError(f"Could not retrieve {url}: {last_error}")


def query_index(url: str, collection: str) -> dict[str, str]:
    query = urlencode({"url": url, "output": "json"})
    index_url = f"https://index.commoncrawl.org/{collection}-index?{query}"
    lines = _get(index_url).decode("utf-8").splitlines()
    records = [json.loads(line) for line in lines if line.strip()]
    candidates = [record for record in records if record.get("status") == "200"]
    if not candidates:
        raise CommonCrawlError(
            f"{collection} contains no successful capture for {url}."
        )
    return max(candidates, key=lambda record: str(record["timestamp"]))


def load_index_records(paths: list[Path]) -> dict[tuple[str, str], dict[str, str]]:
    records: dict[tuple[str, str], dict[str, str]] = {}
    for path in paths:
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip().startswith("{"):
                continue
            record = json.loads(line)
            key = _url_key(str(record["url"]))
            current = records.get(key)
            if current is None or str(record["timestamp"]) > str(
                current["timestamp"]
            ):
                records[key] = record
    return records


def extract_warc_response(data: bytes, expected_digest: str) -> bytes:
    try:
        expanded = gzip.decompress(data)
    except gzip.BadGzipFile as exc:
        raise CommonCrawlError("Common Crawl range is not a gzip member.") from exc
    sections = expanded.split(b"\r\n\r\n", 2)
    if len(sections) != 3 or not sections[1].startswith(b"HTTP/1.1 200"):
        raise CommonCrawlError("Common Crawl WARC has no successful HTTP payload.")
    body = sections[2]
    if body.endswith(b"\r\n\r\n"):
        body = body[:-4]
    digest = base64.b32encode(hashlib.sha1(body).digest()).decode("ascii")
    if digest.rstrip("=") != expected_digest:
        raise CommonCrawlError(
            f"Common Crawl payload digest mismatch: {digest} != {expected_digest}."
        )
    return body


def fetch_record(record: dict[str, str]) -> bytes:
    offset = int(record["offset"])
    length = int(record["length"])
    range_end = offset + length - 1
    data_url = f"https://data.commoncrawl.org/{record['filename']}"
    compressed = _get(
        data_url,
        headers={"Range": f"bytes={offset}-{range_end}"},
    )
    return extract_warc_response(compressed, str(record["digest"]))


def _provenance(record: dict[str, str]) -> dict[str, str]:
    return {
        "collection": str(record["filename"]).split("/", 2)[1],
        "digest": str(record["digest"]),
        "filename": str(record["filename"]),
        "length": str(record["length"]),
        "method": "common_crawl_warc",
        "offset": str(record["offset"]),
        "timestamp": str(record["timestamp"]),
        "url": str(record["url"]),
    }


def fill_cache(
    *,
    output_root: Path,
    index_file: Path,
    index_url: str,
    cdx_files: list[Path],
    collection: str,
    page_index_files: list[Path] | None = None,
    source_index_files: list[Path] | None = None,
) -> dict[str, object]:
    entries = parse_index(index_file.read_bytes(), index_url)
    snapshots = load_cdx_snapshots(cdx_files)
    page_index = load_index_records(page_index_files or [])
    source_index = load_index_records(source_index_files or [])
    raw_root = output_root / "raw"
    retrievals: dict[str, dict[str, str]] = {}
    results: list[dict[str, str]] = []
    for entry in entries:
        page_path = raw_root / "pages" / f"{entry.arrangement_id}.html"
        source_path = raw_root / "mup" / f"{entry.arrangement_id}.mup"
        if page_path.is_file() and source_path.is_file():
            continue
        if (
            page_path.is_file()
            and not source_path.is_file()
            and page_index
            and _url_key(entry.page_url) not in page_index
            and not source_index
        ):
            continue
        if (
            not page_path.is_file()
            and _url_key(entry.page_url) in snapshots
            and not page_index
        ):
            continue
        result = {
            "arrangement_id": entry.arrangement_id,
            "page_url": entry.page_url,
        }
        try:
            if page_path.is_file():
                page_data = page_path.read_bytes()
            else:
                page_record = page_index.get(_url_key(entry.page_url))
                if page_record is None and page_index:
                    raise CommonCrawlError(
                        f"Bulk index has no capture for {entry.page_url}."
                    )
                page_record = page_record or query_index(
                    entry.page_url, collection
                )
                page_data = fetch_record(page_record)
                page_path.parent.mkdir(parents=True, exist_ok=True)
                page_path.write_bytes(page_data)
                retrievals[entry.page_url] = _provenance(page_record)
            page = parse_page(page_data, entry.page_url)
            selected = choose_source_variant(list(page["source_variants"]))
            if selected is None:
                raise CommonCrawlError("Captured page offers no Mup source.")
            source_url = selected["url"]
            if not source_path.is_file():
                source_record = source_index.get(_url_key(source_url))
                source_record = source_record or query_index(
                    source_url, collection
                )
                source_data = fetch_record(source_record)
                source_path.parent.mkdir(parents=True, exist_ok=True)
                source_path.write_bytes(source_data)
                retrievals[source_url] = _provenance(source_record)
            result["disposition"] = "cached"
            result["source_url"] = source_url
        except (CommonCrawlError, OSError, ValueError) as exc:
            result["disposition"] = "common_crawl_hold"
            result["hold_reason"] = str(exc)
        results.append(result)

    report: dict[str, object] = {
        "schema_version": 1,
        "collection": collection,
        "retrievals": retrievals,
        "records": results,
        "summary": {
            disposition: sum(
                record["disposition"] == disposition for record in results
            )
            for disposition in sorted(
                {record["disposition"] for record in results}
            )
        },
    }
    output_root.mkdir(parents=True, exist_ok=True)
    (output_root / "common-crawl-retrieval.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--index-file", required=True, type=Path)
    parser.add_argument(
        "--index-url",
        default="https://hymnstogod.org/Hymns-PD/ZZ-CompletePDHymnList.html",
    )
    parser.add_argument("--cdx-file", action="append", default=[], type=Path)
    parser.add_argument("--collection", default=DEFAULT_INDEX)
    parser.add_argument("--page-index-file", action="append", default=[], type=Path)
    parser.add_argument("--source-index-file", action="append", default=[], type=Path)
    args = parser.parse_args()
    try:
        report = fill_cache(
            output_root=args.output_root.resolve(),
            index_file=args.index_file.resolve(),
            index_url=args.index_url,
            cdx_files=[path.resolve() for path in args.cdx_file],
            collection=args.collection,
            page_index_files=[path.resolve() for path in args.page_index_file],
            source_index_files=[path.resolve() for path in args.source_index_file],
        )
    except (CommonCrawlError, OSError, ValueError) as exc:
        print(f"Common Crawl cache fill failed: {exc}")
        return 2
    print(f"Common Crawl cache fill: {report['summary']}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Inventory every HymnsToGod public-domain page and its Mup source variants.

The public-domain index lists arrangements, not merely unique hymn titles. This
inventory therefore assigns both a work identity and a page/arrangement identity.
Layout-specific Mup files remain source variants of one arrangement until their
notation fingerprints prove otherwise.
"""

from __future__ import annotations

import argparse
import base64
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from datetime import date
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import subprocess
from threading import Lock
import time
import unicodedata
from typing import Callable
from urllib.error import HTTPError, URLError
from urllib.parse import unquote, urljoin, urlparse
from urllib.request import Request, urlopen


INDEX_URL = "https://hymnstogod.org/Hymns-PD/ZZ-CompletePDHymnList.html"
DATASET_ID = "hymns-to-god-public-domain-usa"
USER_AGENT = "Transposify catalog audit/1.0 (+https://transposify.com/)"
PUBLIC_DOMAIN_DECLARATION = "Public Domain - USA"
DONATION_RE = re.compile(
    rb"this (?:mup )?(?:source code|code|file) is donated to the public domain\.",
    re.IGNORECASE,
)


class InventoryError(ValueError):
    """Raised when upstream content cannot form a deterministic inventory."""


@dataclass(frozen=True)
class IndexEntry:
    arrangement_id: str
    work_id: str
    title: str
    index_label: str
    arrangement_label: str
    page_url: str


@dataclass(frozen=True)
class PageRow:
    label: str
    text: str
    links: tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class CdxSnapshot:
    timestamp: str
    original_url: str
    digest: str

    @property
    def replay_url(self) -> str:
        return (
            f"https://web.archive.org/web/{self.timestamp}id_/"
            f"{self.original_url}"
        )


class _IndexParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._in_dt = False
        self._in_anchor = False
        self._href: str | None = None
        self._anchor_text: list[str] = []
        self._dt_text: list[str] = []
        self.raw_entries: list[tuple[str, str, str]] = []

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        if tag == "dt":
            self._in_dt = True
            self._href = None
            self._anchor_text = []
            self._dt_text = []
        elif tag == "a" and self._in_dt:
            self._in_anchor = True
            self._href = dict(attrs).get("href")

    def handle_data(self, data: str) -> None:
        if not self._in_dt:
            return
        self._dt_text.append(data)
        if self._in_anchor:
            self._anchor_text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "a":
            self._in_anchor = False
        elif tag == "dt" and self._in_dt:
            href = self._href or ""
            if re.search(r"(?:^|/)[A-Z]-Hymns/.*\.html$", href):
                title = _clean_text("".join(self._anchor_text))
                label = _clean_text("".join(self._dt_text))
                if title:
                    self.raw_entries.append((title, label, href))
            self._in_dt = False


class _PageTableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._in_title = False
        self._title_text: list[str] = []
        self._in_row = False
        self._cell: str | None = None
        self._cell_text: list[str] = []
        self._cell_links: list[tuple[str, str]] = []
        self._link_href: str | None = None
        self._link_text: list[str] = []
        self._row_cells: list[tuple[str, str, tuple[tuple[str, str], ...]]] = []
        self.rows: list[PageRow] = []

    @property
    def page_title(self) -> str:
        return _clean_text("".join(self._title_text))

    def _finish_link(self) -> None:
        if self._link_href is None:
            return
        self._cell_links.append(
            (_clean_text("".join(self._link_text)), self._link_href)
        )
        self._link_href = None
        self._link_text = []

    def _finish_cell(self) -> None:
        if self._cell is None:
            return
        self._finish_link()
        self._row_cells.append(
            (
                self._cell,
                _clean_text("".join(self._cell_text)).strip(" |"),
                tuple(self._cell_links),
            )
        )
        self._cell = None

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        if tag == "title":
            self._in_title = True
        elif tag == "tr":
            self._in_row = True
            self._row_cells = []
        elif self._in_row and tag in {"th", "td"}:
            # Many source pages omit </td>; HTML starts the next cell implicitly.
            self._finish_cell()
            self._cell = tag
            self._cell_text = []
            self._cell_links = []
        elif self._cell is not None and tag == "a":
            self._link_href = dict(attrs).get("href")
            self._link_text = []

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self._title_text.append(data)
        if self._cell is None:
            return
        self._cell_text.append(data)
        if self._link_href is not None:
            self._link_text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self._in_title = False
        elif tag == "a" and self._link_href is not None:
            self._finish_link()
        elif tag in {"th", "td"} and self._cell == tag:
            self._finish_cell()
        elif tag == "tr" and self._in_row:
            self._finish_cell()
            labels = [cell for cell in self._row_cells if cell[0] == "th"]
            values = [cell for cell in self._row_cells if cell[0] == "td"]
            if labels and values:
                label = labels[0][1].rstrip(":")
                text = " ".join(value[1] for value in values if value[1])
                links = tuple(link for value in values for link in value[2])
                self.rows.append(PageRow(label=label, text=text, links=links))
            self._in_row = False


def _clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _slug(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii").lower()
    return re.sub(r"[^a-z0-9]+", "-", ascii_value).strip("-")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha1_base32(data: bytes) -> str:
    return base64.b32encode(hashlib.sha1(data).digest()).decode("ascii").rstrip("=")


def _verified_retrieval(
    data: bytes,
    *,
    canonical_url: str,
    retrieval: dict[str, str],
    was_cached: bool,
) -> dict[str, object]:
    result: dict[str, object] = dict(retrieval)
    result["content_sha256"] = _sha256(data)
    method = retrieval.get("method")
    expected_digest = ""
    if method == "internet_archive_snapshot":
        expected_digest = retrieval.get("archive_digest", "")
    elif method == "common_crawl_warc":
        expected_digest = retrieval.get("digest", "")
    if expected_digest:
        actual_digest = _sha1_base32(data)
        if actual_digest == expected_digest:
            result["content_digest_verified"] = True
            result["sha1_base32"] = actual_digest
            return result
        if not was_cached:
            raise InventoryError(
                f"Retrieved content digest mismatch for {canonical_url}: "
                f"{actual_digest} != {expected_digest}."
            )
        return {
            "content_digest_verified": False,
            "content_sha256": _sha256(data),
            "method": "cached_official_url_content",
            "url": canonical_url,
        }
    if was_cached:
        result["method"] = "cached_official_url_content"
        result["url"] = canonical_url
    return result


def _url_key(url: str) -> tuple[str, str]:
    parsed = urlparse(url)
    return unquote(parsed.path).casefold().rstrip("/"), parsed.query


def load_cdx_snapshots(paths: list[Path]) -> dict[tuple[str, str], CdxSnapshot]:
    snapshots: dict[tuple[str, str], CdxSnapshot] = {}
    for path in paths:
        rows = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(rows, list) or not rows:
            raise InventoryError(f"Invalid empty CDX response in {path}.")
        header = rows[0]
        if header != ["timestamp", "original", "digest"]:
            raise InventoryError(f"Unexpected CDX columns in {path}: {header!r}.")
        for row in rows[1:]:
            if not isinstance(row, list) or len(row) != 3:
                raise InventoryError(f"Invalid CDX row in {path}: {row!r}.")
            snapshot = CdxSnapshot(
                timestamp=str(row[0]),
                original_url=str(row[1]),
                digest=str(row[2]),
            )
            key = _url_key(snapshot.original_url)
            current = snapshots.get(key)
            if current is None or snapshot.timestamp > current.timestamp:
                snapshots[key] = snapshot
    return snapshots


def _retrieval(
    url: str,
    *,
    snapshots: dict[tuple[str, str], CdxSnapshot],
    prefer_archive: bool,
    cached_retrievals: dict[str, dict[str, str]],
) -> tuple[str, dict[str, str]]:
    cached = cached_retrievals.get(url)
    if cached is not None:
        return url, cached
    snapshot = snapshots.get(_url_key(url)) if prefer_archive else None
    if snapshot is None:
        return url, {"method": "origin", "url": url}
    return snapshot.replay_url, {
        "archive_digest": snapshot.digest,
        "archive_original_url": snapshot.original_url,
        "archive_timestamp": snapshot.timestamp,
        "method": "internet_archive_snapshot",
        "url": snapshot.replay_url,
    }


def parse_index(data: bytes, index_url: str = INDEX_URL) -> list[IndexEntry]:
    parser = _IndexParser()
    parser.feed(data.decode("utf-8", errors="replace"))
    raw_entries = parser.raw_entries
    if not raw_entries:
        raise InventoryError("The public-domain index contains no hymn pages.")

    work_counts: dict[str, int] = {}
    for title, _, _ in raw_entries:
        work_id = _slug(title)
        work_counts[work_id] = work_counts.get(work_id, 0) + 1

    entries: list[IndexEntry] = []
    seen_arrangements: set[str] = set()
    for title, index_label, href in raw_entries:
        page_url = urljoin(index_url, href)
        arrangement_id = _slug(Path(urlparse(page_url).path).stem)
        if not arrangement_id or arrangement_id in seen_arrangements:
            raise InventoryError(
                f"Duplicate or empty arrangement identity for {page_url!r}."
            )
        seen_arrangements.add(arrangement_id)
        work_id = _slug(title)
        suffix = index_label.removeprefix(title).strip().lstrip("-").strip()
        arrangement_label = suffix
        if not arrangement_label and work_counts[work_id] > 1:
            arrangement_label = arrangement_id
        entries.append(
            IndexEntry(
                arrangement_id=arrangement_id,
                work_id=work_id,
                title=title,
                index_label=index_label,
                arrangement_label=arrangement_label,
                page_url=page_url,
            )
        )
    return entries


def parse_page(data: bytes, page_url: str) -> dict[str, object]:
    parser = _PageTableParser()
    parser.feed(data.decode("utf-8", errors="replace"))
    rows = {_slug(row.label): row for row in parser.rows}

    def row_text(*names: str) -> str:
        for name in names:
            row = rows.get(_slug(name))
            if row is not None:
                return row.text
        return ""

    variants: list[dict[str, str]] = []
    for row in parser.rows:
        for label, href in row.links:
            url = urljoin(page_url, href)
            if urlparse(url).path.lower().endswith(".mup"):
                variants.append({"label": label or "Mup", "url": url})

    copyright_text = row_text("Copyright")
    return {
        "arranger": row_text("Arranger", "Arranged by", "Arrangement"),
        "composer": row_text("Music", "Composer"),
        "lyricist": row_text("Lyrics", "Words", "Author"),
        "page_title": parser.page_title,
        "page_rights_declaration": (
            f"Copyright: {copyright_text}" if copyright_text else ""
        ),
        "source_variants": variants,
    }


def choose_source_variant(
    variants: list[dict[str, str]],
) -> dict[str, str] | None:
    if not variants:
        return None

    def rank(variant: dict[str, str]) -> tuple[int, str]:
        label = variant["label"].lower()
        if "letter" in label:
            priority = 0
        elif "hymn page" in label:
            priority = 1
        elif "6x9" in label:
            priority = 2
        elif "booklet" in label:
            priority = 3
        elif "landscape" in label:
            priority = 4
        elif "projection" in label:
            priority = 9
        else:
            priority = 5
        return priority, variant["url"]

    return min(variants, key=rank)


def split_source_arrangements(
    entry: IndexEntry,
    variants: list[dict[str, str]],
) -> list[tuple[str, str, list[dict[str, str]]]]:
    """Separate musical settings while retaining layout files as variants."""
    if not variants:
        return [(entry.arrangement_id, entry.arrangement_label, [])]
    by_directory: dict[str, list[dict[str, str]]] = {}
    for variant in variants:
        parent = str(Path(unquote(urlparse(variant["url"]).path)).parent)
        by_directory.setdefault(parent, []).append(variant)
    if len(by_directory) == 1:
        return [(entry.arrangement_id, entry.arrangement_label, variants)]

    result: list[tuple[str, str, list[dict[str, str]]]] = []
    for parent, grouped_variants in sorted(by_directory.items()):
        arrangement_id = _slug(Path(parent).name)
        if not arrangement_id:
            raise InventoryError(
                f"Could not derive sub-arrangement identity from {parent!r}."
            )
        number_match = re.search(r"(?:^|-)arr(?:angement)?-(\d+)$", arrangement_id)
        arrangement_label = (
            f"Arrangement {number_match.group(1)}"
            if number_match
            else arrangement_id.replace("-", " ").title()
        )
        result.append((arrangement_id, arrangement_label, grouped_variants))
    return result


def _fetch(url: str, *, attempts: int = 4, timeout: float = 30.0) -> bytes:
    request = Request(url, headers={"User-Agent": USER_AGENT})
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            with urlopen(request, timeout=timeout) as response:
                return response.read()
        except (HTTPError, URLError, TimeoutError) as exc:
            last_error = exc
            if attempt < attempts:
                time.sleep(float(2 ** (attempt - 1)))
    raise InventoryError(f"Could not download {url}: {last_error}")


class _RateLimitedFetcher:
    """Apply one collection-wide minimum interval between request starts."""

    def __init__(
        self,
        minimum_interval: float,
        fetch: Callable[[str], bytes] = _fetch,
    ) -> None:
        if minimum_interval < 0:
            raise ValueError("request delay cannot be negative")
        self.minimum_interval = minimum_interval
        self.fetch = fetch
        self._lock = Lock()
        self._next_request = 0.0

    def __call__(self, url: str) -> bytes:
        with self._lock:
            now = time.monotonic()
            delay = max(0.0, self._next_request - now)
            if delay:
                time.sleep(delay)
            self._next_request = time.monotonic() + self.minimum_interval
        return self.fetch(url)


class _CurlFetcher:
    """Use curl's mature retry and HTTP/2 handling for unstable CDNs."""

    def __init__(self, executable: Path) -> None:
        self.executable = executable

    def __call__(self, url: str) -> bytes:
        completed = subprocess.run(
            [
                str(self.executable),
                "-fL",
                "--silent",
                "--show-error",
                "--retry",
                "3",
                "--retry-all-errors",
                "--retry-delay",
                "1",
                "--connect-timeout",
                "15",
                "--max-time",
                "60",
                url,
            ],
            check=False,
            capture_output=True,
        )
        if completed.returncode != 0:
            detail = completed.stderr.decode("utf-8", errors="replace").strip()
            raise InventoryError(f"Could not download {url} with curl: {detail}")
        return completed.stdout


def _write_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def _cached_or_fetch(
    path: Path,
    url: str,
    fetcher: Callable[[str], bytes],
) -> bytes:
    if path.is_file():
        return path.read_bytes()
    data = fetcher(url)
    _write_bytes(path, data)
    return data


def inventory_collection(
    *,
    output_root: Path,
    index_url: str = INDEX_URL,
    index_file: Path | None = None,
    audit_date: str | None = None,
    max_workers: int = 1,
    request_delay: float = 0.25,
    limit: int | None = None,
    fetcher: Callable[[str], bytes] | None = None,
    cdx_files: list[Path] | None = None,
    prefer_archive: bool = False,
    retrieval_files: list[Path] | None = None,
    curl_executable: Path | None = None,
) -> dict[str, object]:
    if max_workers < 1:
        raise ValueError("max_workers must be at least 1")
    raw_root = output_root / "raw"
    index_cache = raw_root / "index.html"
    network_fetcher: Callable[[str], bytes] = (
        _CurlFetcher(curl_executable) if curl_executable else _fetch
    )
    active_fetcher = fetcher or _RateLimitedFetcher(
        request_delay,
        fetch=network_fetcher,
    )
    snapshots = load_cdx_snapshots(cdx_files or [])
    cached_retrievals: dict[str, dict[str, str]] = {}
    for retrieval_file in retrieval_files or []:
        retrieval_report = json.loads(retrieval_file.read_text(encoding="utf-8"))
        cached_retrievals.update(retrieval_report.get("retrievals", {}))
    if index_file:
        index_data = index_file.read_bytes()
    elif index_cache.is_file():
        index_data = index_cache.read_bytes()
    else:
        index_data = active_fetcher(index_url)
    entries = parse_index(index_data, index_url)
    if limit is not None:
        entries = entries[:limit]

    _write_bytes(raw_root / "index.html", index_data)

    page_results: dict[str, bytes | Exception] = {}
    page_retrievals: dict[str, dict[str, str]] = {}
    cached_pages: dict[str, bool] = {}
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {}
        for entry in entries:
            retrieval_url, retrieval = _retrieval(
                entry.page_url,
                snapshots=snapshots,
                prefer_archive=prefer_archive,
                cached_retrievals=cached_retrievals,
            )
            page_retrievals[entry.arrangement_id] = retrieval
            page_path = raw_root / "pages" / f"{entry.arrangement_id}.html"
            cached_pages[entry.arrangement_id] = page_path.is_file()
            future = executor.submit(
                _cached_or_fetch,
                page_path,
                retrieval_url,
                active_fetcher,
            )
            futures[future] = entry
        for future in as_completed(futures):
            entry = futures[future]
            try:
                page_results[entry.arrangement_id] = future.result()
            except Exception as exc:  # Preserve every failed page in the report.
                page_results[entry.arrangement_id] = exc

    selected_sources: dict[str, dict[str, str]] = {}
    records: list[dict[str, object]] = []
    for entry in entries:
        page_result = page_results[entry.arrangement_id]
        base_record: dict[str, object] = asdict(entry)
        if isinstance(page_result, Exception):
            base_record.update(
                disposition="download_hold",
                hold_reason=str(page_result),
            )
            records.append(base_record)
            continue

        page_file = f"pages/{entry.arrangement_id}.html"
        try:
            page_retrieval = _verified_retrieval(
                page_result,
                canonical_url=entry.page_url,
                retrieval=page_retrievals[entry.arrangement_id],
                was_cached=cached_pages[entry.arrangement_id],
            )
        except InventoryError as exc:
            base_record.update(disposition="download_hold", hold_reason=str(exc))
            records.append(base_record)
            continue
        page = parse_page(page_result, entry.page_url)
        base_record.update(
            page,
            page_file=page_file,
            page_retrieval=page_retrieval,
            page_sha256=_sha256(page_result),
        )
        declaration = str(page["page_rights_declaration"])
        rights_basis = ""
        hold_reason = ""
        if declaration == f"Copyright: {PUBLIC_DOMAIN_DECLARATION}":
            rights_basis = "individual_page_declaration"
        elif declaration in {"", "Copyright: Midi"}:
            rights_basis = "complete_public_domain_index"
            base_record["page_rights_declaration"] = (
                f"Copyright: {PUBLIC_DOMAIN_DECLARATION}"
            )
        else:
            hold_reason = (
                "Individual page contradicts or replaces the public-domain "
                "index classification."
            )

        arrangements = split_source_arrangements(
            entry,
            list(page["source_variants"]),  # type: ignore[arg-type]
        )
        for arrangement_id, arrangement_label, variants in arrangements:
            record = {
                **base_record,
                "arrangement_id": arrangement_id,
                "arrangement_label": arrangement_label,
                "source_variants": variants,
            }
            if arrangement_id != entry.arrangement_id:
                record["index_arrangement_id"] = entry.arrangement_id
            if hold_reason:
                record.update(
                    disposition="rights_hold",
                    hold_reason=hold_reason,
                )
                records.append(record)
                continue
            record["rights_basis"] = rights_basis
            selected = choose_source_variant(variants)
            if selected is None:
                record.update(
                    disposition="source_hold",
                    hold_reason="Individual page offers no downloadable Mup source.",
                )
            else:
                selected_sources[arrangement_id] = selected
                record["selected_source"] = selected
                record["disposition"] = "pending_source_download"
            records.append(record)

    seen_arrangement_ids: set[str] = set()
    for ordinal, record in enumerate(records, start=1):
        arrangement_id = str(record["arrangement_id"])
        if arrangement_id in seen_arrangement_ids:
            raise InventoryError(
                f"Duplicate expanded arrangement identity {arrangement_id!r}."
            )
        seen_arrangement_ids.add(arrangement_id)
        record["record_ordinal"] = ordinal

    source_results: dict[str, bytes | Exception] = {}
    source_retrievals: dict[str, dict[str, str]] = {}
    cached_sources: dict[str, bool] = {}
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {}
        for arrangement_id, selected in selected_sources.items():
            retrieval_url, retrieval = _retrieval(
                selected["url"],
                snapshots=snapshots,
                prefer_archive=prefer_archive,
                cached_retrievals=cached_retrievals,
            )
            source_retrievals[arrangement_id] = retrieval
            source_path = raw_root / "mup" / f"{arrangement_id}.mup"
            cached_sources[arrangement_id] = source_path.is_file()
            future = executor.submit(
                _cached_or_fetch,
                source_path,
                retrieval_url,
                active_fetcher,
            )
            futures[future] = arrangement_id
        for future in as_completed(futures):
            arrangement_id = futures[future]
            try:
                source_results[arrangement_id] = future.result()
            except Exception as exc:
                source_results[arrangement_id] = exc

    for record in records:
        arrangement_id = str(record["arrangement_id"])
        if record.get("disposition") != "pending_source_download":
            continue
        source_result = source_results[arrangement_id]
        if isinstance(source_result, Exception):
            record.update(
                disposition="download_hold",
                hold_reason=str(source_result),
            )
            continue
        try:
            source_retrieval = _verified_retrieval(
                source_result,
                canonical_url=str(record["selected_source"]["url"]),
                retrieval=source_retrievals[arrangement_id],
                was_cached=cached_sources[arrangement_id],
            )
        except InventoryError as exc:
            record.update(disposition="download_hold", hold_reason=str(exc))
            continue
        source_file = f"mup/{arrangement_id}.mup"
        donation_found = DONATION_RE.search(source_result) is not None
        record.update(
            disposition="pending_conversion",
            source_code_declaration=(
                "Mup source code donated to the public domain."
                if donation_found
                else "No separate source-code donation found; individual page "
                "declares Public Domain - USA."
            ),
            source_code_donation_found=donation_found,
            source_file=source_file,
            source_retrieval=source_retrieval,
            source_sha256=_sha256(source_result),
            source_url=record["selected_source"]["url"],  # type: ignore[index]
        )

    disposition_counts: dict[str, int] = {}
    for record in records:
        disposition = str(record["disposition"])
        disposition_counts[disposition] = (
            disposition_counts.get(disposition, 0) + 1
        )

    inventory: dict[str, object] = {
        "schema_version": 2,
        "dataset_id": DATASET_ID,
        "audit_date": audit_date or date.today().isoformat(),
        "index": {
            "arrangement_count": len(records),
            "entry_count": len(entries),
            "file": "raw/index.html",
            "sha256": _sha256(index_data),
            "url": index_url,
        },
        "summary": dict(sorted(disposition_counts.items())),
        "records": records,
    }
    output_root.mkdir(parents=True, exist_ok=True)
    (output_root / "inventory.json").write_text(
        json.dumps(inventory, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return inventory


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--index-url", default=INDEX_URL)
    parser.add_argument("--index-file", type=Path)
    parser.add_argument("--audit-date")
    parser.add_argument("--max-workers", type=int, default=1)
    parser.add_argument(
        "--request-delay",
        type=float,
        default=0.25,
        help="Minimum seconds between network request starts (default: 0.25).",
    )
    parser.add_argument("--limit", type=int)
    parser.add_argument(
        "--curl-executable",
        type=Path,
        help="Use curl for resilient HTTP retrieval instead of urllib.",
    )
    parser.add_argument(
        "--cdx-file",
        action="append",
        default=[],
        type=Path,
        help="Internet Archive CDX JSON index; may be provided more than once.",
    )
    parser.add_argument(
        "--prefer-archive",
        action="store_true",
        help="Use indexed Internet Archive snapshots before the origin server.",
    )
    parser.add_argument(
        "--retrieval-file",
        action="append",
        default=[],
        type=Path,
        help="Sidecar retrieval provenance for files already in the raw cache.",
    )
    args = parser.parse_args()
    try:
        inventory = inventory_collection(
            output_root=args.output_root.resolve(),
            index_url=args.index_url,
            index_file=args.index_file.resolve() if args.index_file else None,
            audit_date=args.audit_date,
            max_workers=args.max_workers,
            request_delay=args.request_delay,
            limit=args.limit,
            cdx_files=[path.resolve() for path in args.cdx_file],
            prefer_archive=args.prefer_archive,
            retrieval_files=[path.resolve() for path in args.retrieval_file],
            curl_executable=(
                args.curl_executable.resolve() if args.curl_executable else None
            ),
        )
    except (InventoryError, OSError, ValueError) as exc:
        print(f"HymnsToGod inventory failed: {exc}")
        return 2
    print(
        f"Inventoried {inventory['index']['entry_count']} HymnsToGod pages: "  # type: ignore[index]
        f"{inventory['summary']}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Import the audited Timeless Truths edition of "Nothing Between"."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

from build_open_hymnal_catalog import _write_web_catalog
from normalize_satb_musicxml import (
    TIMELESS_TRUTHS_NORMALIZER_NAME,
    normalize_timeless_truths_musicxml,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
CATALOG_ROOT = REPOSITORY_ROOT / "catalog"
DEFAULT_SOURCE = (
    REPOSITORY_ROOT
    / "data/timeless-truths/raw/Nothing_Between.xml"
)
DEFAULT_CATALOG = CATALOG_ROOT / "catalog.json"
DEFAULT_REPORT = CATALOG_ROOT / "import-report.json"
DEFAULT_MANIFEST = REPOSITORY_ROOT / "data/timeless-truths/manifest.json"
DEFAULT_WEB_CATALOG = (
    REPOSITORY_ROOT / "apps/web/src/lib/catalog.generated.ts"
)

CATALOG_REVISION = "8"
COLLECTION_ID = "timeless-truths-public-domain"
GENERATOR_NAME = "timeless-truths-sibelius-satb"
GENERATOR_VERSION = "1"
RIGHTS_STATUS = "technical_candidate_not_production_approved"
RIGHTS_DECLARATION = "Public Domain Mark 1.0"
SOURCE_PAGE_URL = (
    "https://library.timelesstruths.org/music/Nothing_Between/"
)
SOURCE_MUSICXML_URL = (
    "https://library.timelesstruths.org/library/music/N/"
    "Nothing_Between/Nothing_Between.xml"
)
PUBLIC_DOMAIN_MARK_URL = "https://creativecommons.org/publicdomain/mark/1.0/"
EXPECTED_SOURCE_SHA256 = (
    "785cce66fb51ee98f3b89ab6d04e7053c9cdb05a72cc4a18d3e9d3dbe9885ec7"
)
EXPECTED_NORMALIZED_SHA256 = (
    "9dbd5977d1f4a2110b9af90b466b00746e0d509047a4a1fb2f3c6fe459a8d99a"
)
EXPECTED_BASE_ITEMS = 2225


class TimelessTruthsImportError(ValueError):
    """Raised when the pinned score cannot be imported deterministically."""


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _direct_children(element: ET.Element, name: str) -> list[ET.Element]:
    return [child for child in element if _local_name(child.tag) == name]


def _first_text(root: ET.Element, name: str) -> str:
    return next(
        (
            (element.text or "").strip()
            for element in root.iter()
            if _local_name(element.tag) == name
        ),
        "",
    )


def _score_facts(data: bytes) -> dict[str, object]:
    root = ET.fromstring(data)
    parts = _direct_children(root, "part")
    voices: set[tuple[int, str]] = set()
    lyric_voices: set[tuple[int, str]] = set()
    verse_ids: set[str] = set()
    for part_index, part in enumerate(parts):
        for note in (
            element
            for element in part.iter()
            if _local_name(element.tag) == "note"
        ):
            voice = _first_text(note, "voice")
            if voice:
                voices.add((part_index, voice))
            lyrics = _direct_children(note, "lyric")
            if lyrics:
                lyric_voices.add((part_index, voice))
            if (part_index, voice) == (0, "1"):
                verse_ids.update(lyric.get("number", "1") for lyric in lyrics)
    return {
        "fifths": _first_text(root, "fifths"),
        "mode": _first_text(root, "mode"),
        "parts": len(parts),
        "rights": _first_text(root, "rights"),
        "software": [
            (element.text or "").strip()
            for element in root.iter()
            if _local_name(element.tag) == "software"
        ],
        "title": _first_text(root, "work-title"),
        "verse_ids": sorted(verse_ids, key=int),
        "voice_locations": sorted(voices),
        "lyric_locations": sorted(lyric_voices),
    }


def _validate_facts(facts: dict[str, object]) -> None:
    expected = {
        "fifths": "1",
        "mode": "major",
        "parts": 2,
        "title": "Nothing Between",
        "verse_ids": ["1", "2", "3", "4"],
        "voice_locations": [(0, "1"), (0, "2"), (1, "1"), (1, "2")],
        "lyric_locations": [(0, "1")],
    }
    for field, value in expected.items():
        if facts.get(field) != value:
            raise TimelessTruthsImportError(
                f"normalized {field} drifted: {facts.get(field)!r} != {value!r}"
            )
    if "Public Domain." not in str(facts.get("rights")):
        raise TimelessTruthsImportError(
            "source MusicXML no longer declares the score public domain"
        )
    if "Transposify Timeless Truths normalizer v1" not in facts.get(
        "software", []
    ):
        raise TimelessTruthsImportError(
            "normalized score is missing its generator declaration"
        )


def _catalog_item(
    *,
    source_sha256: str,
    normalized_sha256: str,
    operations: tuple[str, ...],
) -> dict[str, object]:
    return {
        "available_lines": ["SATB", "S", "A", "T", "B"],
        "content_type": "hymn",
        "display": {
            "composer": "Charles A. Tindley",
            "ensemble": "SATB choir",
            "lyricist": "Charles A. Tindley",
            "meter": "10.9.10.9 with refrain",
            "search_terms": [
                "Nothing Between My Soul and the Savior",
                "Nothing Between My Soul and the Saviour",
            ],
            "text_author": "Charles A. Tindley",
            "tune_name": "NOTHING BETWEEN",
        },
        "id": "nothing-between",
        "lyrics": {
            "available": True,
            "scope": "soprano_only",
            "verse_ids": ["1", "2", "3", "4"],
        },
        "original_key": {
            "abc": "G",
            "fifths": 1,
            "mode": "major",
            "name": "G major",
        },
        "rights": {
            "source_attribution": [
                "Words and music: Charles A. Tindley, 1905.",
                "Arrangement: F. A. Clark.",
                "MusicXML published by Timeless Truths.",
            ],
            "source_declaration": RIGHTS_DECLARATION,
            "source_music_reference": SOURCE_MUSICXML_URL,
            "status": RIGHTS_STATUS,
        },
        "score": {
            "canonical_state": "untransposed",
            "generator": {
                "name": GENERATOR_NAME,
                "version": GENERATOR_VERSION,
            },
            "media_type": "application/vnd.recordare.musicxml+xml",
            "normalization": {
                "name": TIMELESS_TRUTHS_NORMALIZER_NAME,
                "operations": list(operations),
                "version": "1",
            },
            "path": "scores/nothing-between.musicxml",
            "sha256": normalized_sha256,
        },
        "source": {
            "arrangement_id": "nothing-between-clark",
            "arrangement_label": "F. A. Clark",
            "artifact_sha256": source_sha256,
            "collection_id": COLLECTION_ID,
            "record_ordinal": 1,
            "record_reference": "nothing-between",
            "record_url": SOURCE_PAGE_URL,
            "work_id": "nothing-between",
        },
        "title": "Nothing Between",
    }


def import_score(
    *,
    source_path: Path = DEFAULT_SOURCE,
    catalog_path: Path = DEFAULT_CATALOG,
    report_path: Path = DEFAULT_REPORT,
    manifest_path: Path = DEFAULT_MANIFEST,
    web_catalog_path: Path = DEFAULT_WEB_CATALOG,
) -> dict[str, int]:
    source_data = source_path.read_bytes()
    source_sha256 = _sha256_bytes(source_data)
    if source_sha256 != EXPECTED_SOURCE_SHA256:
        raise TimelessTruthsImportError(
            f"source hash drifted: {source_sha256} != {EXPECTED_SOURCE_SHA256}"
        )
    normalized = normalize_timeless_truths_musicxml(source_data)
    normalized_sha256 = _sha256_bytes(normalized.data)
    if normalized_sha256 != EXPECTED_NORMALIZED_SHA256:
        raise TimelessTruthsImportError(
            "normalized score hash drifted: "
            f"{normalized_sha256} != {EXPECTED_NORMALIZED_SHA256}"
        )
    facts = _score_facts(normalized.data)
    _validate_facts(facts)

    destination = catalog_path.parent / "scores/nothing-between.musicxml"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(normalized.data)

    manifest = {
        "collection_id": COLLECTION_ID,
        "public_domain_mark_url": PUBLIC_DOMAIN_MARK_URL,
        "record": {
            "arrangement": "F. A. Clark",
            "composer": "Charles A. Tindley",
            "normalized_sha256": normalized_sha256,
            "normalization": {
                "name": TIMELESS_TRUTHS_NORMALIZER_NAME,
                "operations": list(normalized.operations),
                "version": "1",
            },
            "raw_sha256": source_sha256,
            "rights_declaration": RIGHTS_DECLARATION,
            "title": "Nothing Between",
            "year": 1905,
        },
        "schema_version": 1,
        "source_musicxml_url": SOURCE_MUSICXML_URL,
        "source_page_url": SOURCE_PAGE_URL,
        "summary": {"promoted_records": 1, "source_records": 1},
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_bytes = (
        json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    ).encode("utf-8")
    manifest_path.write_bytes(manifest_bytes)
    manifest_sha256 = _sha256_bytes(manifest_bytes)

    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    if str(catalog.get("catalog_revision")) not in {"7", CATALOG_REVISION}:
        raise TimelessTruthsImportError(
            "base catalog must be revision 7 or idempotent revision 8"
        )
    base_items = [
        item
        for item in catalog["items"]
        if item["source"]["collection_id"] != COLLECTION_ID
    ]
    if len(base_items) != EXPECTED_BASE_ITEMS:
        raise TimelessTruthsImportError(
            f"expected {EXPECTED_BASE_ITEMS} base items, found {len(base_items)}"
        )
    item = _catalog_item(
        source_sha256=source_sha256,
        normalized_sha256=normalized_sha256,
        operations=normalized.operations,
    )
    all_items = base_items + [item]
    catalog["catalog_revision"] = CATALOG_REVISION
    catalog["items"] = all_items
    catalog["source_collections"] = [
        collection
        for collection in catalog["source_collections"]
        if collection["id"] != COLLECTION_ID
    ] + [
        {
            "encoding": "utf-8",
            "id": COLLECTION_ID,
            "manifest_sha256": manifest_sha256,
            "source_url": SOURCE_PAGE_URL,
        }
    ]
    catalog_path.write_text(
        json.dumps(catalog, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )

    report = json.loads(report_path.read_text(encoding="utf-8"))
    report["catalog_revision"] = CATALOG_REVISION
    report["conversion"]["timeless_truths"] = {
        "generator": {"name": GENERATOR_NAME, "version": GENERATOR_VERSION},
        "normalization": {
            "name": TIMELESS_TRUTHS_NORMALIZER_NAME,
            "operations": list(normalized.operations),
            "version": "1",
        },
    }
    report["source_breakdown"]["timeless_truths"] = {
        "catalog_items": 1,
        "exact_public_domain_candidates": 1,
        "source_records": 1,
        "structure_holds": 0,
    }
    report["summary"].update(
        {
            "catalog_items": EXPECTED_BASE_ITEMS + 1,
            "exact_public_domain_candidates": 2232,
            "source_records": 2252,
            "timeless_truths_items": 1,
        }
    )
    report_path.write_text(
        json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    _write_web_catalog(
        all_items,
        web_catalog_path,
        catalog_revision=int(CATALOG_REVISION),
    )
    return {"catalog_items": 1, "source_records": 1, "structure_holds": 0}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--web-catalog", type=Path, default=DEFAULT_WEB_CATALOG)
    args = parser.parse_args()
    try:
        summary = import_score(
            source_path=args.source,
            catalog_path=args.catalog,
            report_path=args.report,
            manifest_path=args.manifest,
            web_catalog_path=args.web_catalog,
        )
    except (
        TimelessTruthsImportError,
        OSError,
        ET.ParseError,
        json.JSONDecodeError,
    ) as exc:
        print(f"Timeless Truths import failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

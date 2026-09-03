#!/usr/bin/env python3
"""Promote the pinned, losslessly normalizable Timeless Truths cohort."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import sys
import unicodedata
import xml.etree.ElementTree as ET

from build_open_hymnal_catalog import _abc_key, _key_name, _write_web_catalog
from inventory_timeless_truths import (
    DATASET_ID,
    EXPECTED_SCORE_COUNT,
    EXPECTED_STRICT_PUBLIC_DOMAIN_COUNT,
    analyze_musicxml,
)
from normalize_satb_musicxml import (
    TIMELESS_TRUTHS_NORMALIZER_NAME,
    normalize_timeless_truths_musicxml,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
CATALOG_ROOT = REPOSITORY_ROOT / "catalog"
DEFAULT_SOURCE = REPOSITORY_ROOT / "data/timeless-truths/raw/Nothing_Between.xml"
DEFAULT_INVENTORY = REPOSITORY_ROOT / "data/timeless-truths/inventory.json"
DEFAULT_CATALOG = CATALOG_ROOT / "catalog.json"
DEFAULT_REPORT = CATALOG_ROOT / "import-report.json"
DEFAULT_MANIFEST = REPOSITORY_ROOT / "data/timeless-truths/manifest.json"
DEFAULT_WEB_CATALOG = REPOSITORY_ROOT / "apps/web/src/lib/catalog.generated.ts"

CATALOG_REVISION = "9"
COLLECTION_ID = DATASET_ID
GENERATOR_NAME = "timeless-truths-sibelius-satb"
GENERATOR_VERSION = "1"
RIGHTS_STATUS = "technical_candidate_not_production_approved"
RIGHTS_DECLARATION = "Public Domain Mark 1.0"
PUBLIC_DOMAIN_MARK_URL = "https://creativecommons.org/publicdomain/mark/1.0/"
SOURCE_INDEX_URL = (
    "https://library.timelesstruths.org/music/_/?section=_&sortby=title"
)
EXPECTED_SOURCE_SHA256 = (
    "785cce66fb51ee98f3b89ab6d04e7053c9cdb05a72cc4a18d3e9d3dbe9885ec7"
)
EXPECTED_NORMALIZED_SHA256 = (
    "9dbd5977d1f4a2110b9af90b466b00746e0d509047a4a1fb2f3c6fe459a8d99a"
)
EXPECTED_BASE_ITEMS = 2225
EXPECTED_PROMOTED_ITEMS = 148
EXPECTED_NET_NEW_TITLES = 126
EXPECTED_DISTINCT_ARRANGEMENTS = 22
LEGACY_ARRANGEMENT_IDS = {"nothing-between": "nothing-between-clark"}
SEARCH_ALIASES = {
    "nothing-between": [
        "Nothing Between My Soul and the Savior",
        "Nothing Between My Soul and the Saviour",
    ]
}


class TimelessTruthsImportError(ValueError):
    """Raised when pinned inventory cannot produce the expected cohort."""


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


def _slug(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", "-", ascii_value.lower()).strip("-")


def _person_name(label: str) -> str:
    value = re.split(
        r",\s*(?:(?:pub\.?|ca\.?|bef\.?)\s*)*\d{4}\b",
        label,
        maxsplit=1,
        flags=re.IGNORECASE,
    )[0]
    value = re.split(r"\s+(?:arr\.|har\.)\s+by\s+", value, maxsplit=1)[0]
    return value.strip(" ,;") or "Anonymous/Unknown"


def _score_facts(data: bytes) -> dict[str, object]:
    root = ET.fromstring(data)
    parts = _direct_children(root, "part")
    voices: set[tuple[int, str]] = set()
    lyric_voices: set[tuple[int, str]] = set()
    verse_ids: set[str] = set()
    chord_notes = 0
    for part_index, part in enumerate(parts):
        for note in (
            element
            for element in part.iter()
            if _local_name(element.tag) == "note"
        ):
            voice = _first_text(note, "voice")
            if voice:
                voices.add((part_index, voice))
            if any(_local_name(child.tag) == "chord" for child in note):
                chord_notes += 1
            lyrics = _direct_children(note, "lyric")
            if lyrics:
                lyric_voices.add((part_index, voice))
            if (part_index, voice) == (0, "1"):
                verse_ids.update(lyric.get("number", "1") for lyric in lyrics)
    return {
        "chord_notes": chord_notes,
        "fifths": _first_text(root, "fifths"),
        "lyric_locations": sorted(lyric_voices),
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
    }


def _validate_facts(facts: dict[str, object], title: str = "Nothing Between") -> None:
    expected = {
        "chord_notes": 0,
        "lyric_locations": [(0, "1")],
        "parts": 2,
        "title": title,
        "voice_locations": [(0, "1"), (0, "2"), (1, "1"), (1, "2")],
    }
    for field, value in expected.items():
        if facts.get(field) != value:
            raise TimelessTruthsImportError(
                f"normalized {field} drifted for {title!r}: "
                f"{facts.get(field)!r} != {value!r}"
            )
    if facts.get("mode") not in {"major", "minor"}:
        raise TimelessTruthsImportError(
            f"normalized mode is unsupported for {title!r}: {facts.get('mode')!r}"
        )
    if not facts.get("verse_ids"):
        raise TimelessTruthsImportError(f"normalized lyrics are missing for {title!r}")
    if "public domain" not in str(facts.get("rights")).casefold():
        raise TimelessTruthsImportError(
            f"source MusicXML does not declare {title!r} public domain"
        )
    if "Transposify Timeless Truths normalizer v1" not in facts.get(
        "software", []
    ):
        raise TimelessTruthsImportError(
            f"normalized score is missing its generator declaration for {title!r}"
        )


def _unique_item_id(record: dict[str, object], *, taken: set[str]) -> str:
    work_id = str(record["work_id"])
    if work_id not in taken:
        return work_id
    suffix = _slug(str(record["arrangement_label"]))
    suffix = re.sub(rf"^{re.escape(work_id)}-?", "", suffix)
    if not suffix or suffix == work_id:
        name = _person_name(str(record["composer_label"]))
        suffix = _slug(name.rsplit(" ", 1)[-1])
    candidates = [
        f"{work_id}-{suffix}" if suffix else "",
        f"{work_id}-timeless-truths",
    ]
    candidates.extend(f"{work_id}-timeless-truths-{index}" for index in range(2, 100))
    return next(candidate for candidate in candidates if candidate and candidate not in taken)


def _catalog_arrangement_id(record: dict[str, object]) -> str:
    source_id = str(record["arrangement_id"])
    return LEGACY_ARRANGEMENT_IDS.get(source_id, source_id)


def _catalog_item(
    *,
    record: dict[str, object],
    item_id: str,
    normalized_sha256: str,
    operations: tuple[str, ...],
    facts: dict[str, object],
) -> dict[str, object]:
    fifths = int(str(facts["fifths"]))
    mode = str(facts["mode"])
    title = str(record["title"])
    composer = _person_name(str(record["composer_label"]))
    text_author = _person_name(str(record["text_author_label"]))
    tune_name = str(record["arrangement_label"]) or composer
    search_terms = sorted(
        {
            value
            for value in [
                str(record["score_reference"]).replace("_", " "),
                tune_name,
                *SEARCH_ALIASES.get(str(record["work_id"]), []),
            ]
            if value.casefold() not in {title.casefold(), composer.casefold()}
        }
    )
    display: dict[str, object] = {
        "composer": composer,
        "ensemble": "SATB choir",
        "lyricist": text_author,
        "meter": str(record["meter"]) or "Irregular",
        "text_author": text_author,
        "tune_name": tune_name,
    }
    if search_terms:
        display["search_terms"] = search_terms
    return {
        "available_lines": ["SATB", "S", "A", "T", "B"],
        "content_type": "hymn",
        "display": display,
        "id": item_id,
        "lyrics": {
            "available": True,
            "scope": "soprano_only",
            "verse_ids": facts["verse_ids"],
        },
        "original_key": {
            "abc": _abc_key(fifths, mode),
            "fifths": fifths,
            "mode": mode,
            "name": _key_name(fifths, mode),
        },
        "rights": {
            "source_attribution": [
                f"Text: {record['text_author_label']}.",
                f"Tune/setting: {record['composer_label']} ({record['arrangement_label']}).",
                "MusicXML published by Timeless Truths.",
            ],
            "source_declaration": RIGHTS_DECLARATION,
            "source_music_reference": record["source_url"],
            "status": RIGHTS_STATUS,
        },
        "score": {
            "canonical_state": "untransposed",
            "generator": {"name": GENERATOR_NAME, "version": GENERATOR_VERSION},
            "media_type": "application/vnd.recordare.musicxml+xml",
            "normalization": {
                "name": TIMELESS_TRUTHS_NORMALIZER_NAME,
                "operations": list(operations),
                "version": "1",
            },
            "path": f"scores/{item_id}.musicxml",
            "sha256": normalized_sha256,
        },
        "source": {
            "arrangement_id": _catalog_arrangement_id(record),
            "arrangement_label": record["arrangement_label"],
            "artifact_sha256": record["source_sha256"],
            "collection_id": COLLECTION_ID,
            "record_ordinal": record["page_ordinal"],
            "record_reference": record["score_reference"],
            "record_url": record["page_url"],
            "work_id": record["work_id"],
        },
        "title": title,
    }


def _hold(record: dict[str, object]) -> dict[str, object]:
    return {
        "arrangement_id": record["arrangement_id"],
        "collection_id": COLLECTION_ID,
        "reason": record.get("hold_reason", record["disposition"]),
        "record_ordinal": record["page_ordinal"],
        "title": record["title"],
    }


def import_score(
    *,
    inventory_path: Path = DEFAULT_INVENTORY,
    catalog_path: Path = DEFAULT_CATALOG,
    report_path: Path = DEFAULT_REPORT,
    manifest_path: Path = DEFAULT_MANIFEST,
    web_catalog_path: Path = DEFAULT_WEB_CATALOG,
) -> dict[str, int]:
    inventory_bytes = inventory_path.read_bytes()
    inventory = json.loads(inventory_bytes)
    records = inventory.get("records", [])
    summary = inventory.get("summary", {})
    if (
        inventory.get("schema_version") != 1
        or inventory.get("dataset_id") != COLLECTION_ID
        or len(records) != EXPECTED_SCORE_COUNT
        or summary.get("strict_public_domain_musicxml")
        != EXPECTED_STRICT_PUBLIC_DOMAIN_COUNT
    ):
        raise TimelessTruthsImportError("inventory identity or pinned counts drifted")

    dispositions = Counter(str(record["disposition"]) for record in records)
    expected_dispositions = {
        "normalization_candidate": 1710,
        "rights_hold": 26,
        "straightforward_candidate": EXPECTED_PROMOTED_ITEMS,
        "structure_hold": 11,
    }
    if dict(sorted(dispositions.items())) != expected_dispositions:
        raise TimelessTruthsImportError(
            f"inventory dispositions drifted: {dict(dispositions)!r}"
        )

    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    if str(catalog.get("catalog_revision")) not in {"8", CATALOG_REVISION}:
        raise TimelessTruthsImportError(
            "base catalog must be revision 8 or idempotent revision 9"
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

    taken_ids = {str(item["id"]) for item in base_items}
    known_title_keys = {
        _slug(str(item["title"]))
        for item in base_items
        if item["content_type"] == "hymn"
    }
    candidate_title_keys = {
        _slug(str(record["title"]))
        for record in records
        if record["disposition"] == "straightforward_candidate"
    }
    known_fingerprints: dict[str, set[str]] = {}
    for item in base_items:
        if item["content_type"] != "hymn":
            continue
        title_key = _slug(str(item["title"]))
        if title_key not in candidate_title_keys:
            continue
        score_path = catalog_path.parent / str(item["score"]["path"])
        fingerprint = str(
            analyze_musicxml(score_path.read_bytes())["music_fingerprint_sha256"]
        )
        known_fingerprints.setdefault(title_key, set()).add(fingerprint)
    imported_items: list[dict[str, object]] = []
    manifest_records: list[dict[str, object]] = []
    net_new_titles = 0
    distinct_arrangements = 0
    for record in records:
        if record["disposition"] != "straightforward_candidate":
            continue
        source_path = inventory_path.parent / str(record["source_file"])
        source_data = source_path.read_bytes()
        source_sha256 = _sha256_bytes(source_data)
        if source_sha256 != record["source_sha256"]:
            raise TimelessTruthsImportError(
                f"source hash drifted for {record['arrangement_id']!r}"
            )
        normalized = normalize_timeless_truths_musicxml(
            source_data,
            work_title=str(record["title"]),
        )
        normalized_sha256 = _sha256_bytes(normalized.data)
        expected_normalized = record["normalization"]
        if (
            normalized_sha256 != expected_normalized["normalized_sha256"]
            or list(normalized.operations) != expected_normalized["operations"]
        ):
            raise TimelessTruthsImportError(
                f"normalization drifted for {record['arrangement_id']!r}"
            )
        facts = _score_facts(normalized.data)
        _validate_facts(facts, str(record["title"]))

        title_key = _slug(str(record["title"]))
        fingerprint = str(
            expected_normalized["structure"]["music_fingerprint_sha256"]
        )
        if fingerprint in known_fingerprints.get(title_key, set()):
            raise TimelessTruthsImportError(
                "exact musical duplicate reached promotion: "
                f"{record['arrangement_id']!r}"
            )
        is_net_new = title_key not in known_title_keys
        promotion_reason = (
            "net_new_title" if is_net_new else "distinct_arrangement"
        )
        known_fingerprints.setdefault(title_key, set()).add(fingerprint)
        known_title_keys.add(title_key)

        item_id = _unique_item_id(record, taken=taken_ids)
        taken_ids.add(item_id)
        destination = catalog_path.parent / f"scores/{item_id}.musicxml"
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(normalized.data)
        imported_items.append(
            _catalog_item(
                record=record,
                item_id=item_id,
                normalized_sha256=normalized_sha256,
                operations=normalized.operations,
                facts=facts,
            )
        )
        net_new_titles += int(is_net_new)
        distinct_arrangements += int(not is_net_new)
        manifest_records.append(
            {
                "arrangement_id": _catalog_arrangement_id(record),
                "inventory_arrangement_id": record["arrangement_id"],
                "catalog_item_id": item_id,
                "music_fingerprint_sha256": fingerprint,
                "normalized_sha256": normalized_sha256,
                "promotion_reason": promotion_reason,
                "raw_sha256": source_sha256,
                "source_musicxml_url": record["source_url"],
                "source_page_url": record["page_url"],
                "title": record["title"],
                "work_id": record["work_id"],
            }
        )

    if (
        len(imported_items) != EXPECTED_PROMOTED_ITEMS
        or net_new_titles != EXPECTED_NET_NEW_TITLES
        or distinct_arrangements != EXPECTED_DISTINCT_ARRANGEMENTS
    ):
        raise TimelessTruthsImportError(
            "promotion boundary drifted: "
            f"items={len(imported_items)}, new={net_new_titles}, "
            f"arrangements={distinct_arrangements}"
        )

    manifest = {
        "audit_date": inventory["audit_date"],
        "collection_id": COLLECTION_ID,
        "inventory_sha256": _sha256_bytes(inventory_bytes),
        "normalization": {
            "name": TIMELESS_TRUTHS_NORMALIZER_NAME,
            "profile": "split_aligned_satb_dyads",
            "version": "1",
        },
        "public_domain_mark_url": PUBLIC_DOMAIN_MARK_URL,
        "records": manifest_records,
        "schema_version": 2,
        "source_index_url": SOURCE_INDEX_URL,
        "summary": {
            "distinct_arrangements": distinct_arrangements,
            "net_new_titles": net_new_titles,
            "normalization_backlog": dispositions["normalization_candidate"],
            "promoted_records": len(imported_items),
            "rights_holds": dispositions["rights_hold"],
            "source_records": len(records),
            "strict_public_domain_musicxml": EXPECTED_STRICT_PUBLIC_DOMAIN_COUNT,
            "structure_holds": dispositions["structure_hold"],
        },
    }
    manifest_bytes = (
        json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    ).encode("utf-8")
    manifest_path.write_bytes(manifest_bytes)

    all_items = base_items + imported_items
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
            "manifest_sha256": _sha256_bytes(manifest_bytes),
            "source_url": SOURCE_INDEX_URL,
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
            "profile": "split_aligned_satb_dyads",
            "version": "1",
        },
    }
    report["source_breakdown"]["timeless_truths"] = {
        "catalog_items": EXPECTED_PROMOTED_ITEMS,
        "distinct_arrangements": EXPECTED_DISTINCT_ARRANGEMENTS,
        "net_new_titles": EXPECTED_NET_NEW_TITLES,
        "normalization_backlog": dispositions["normalization_candidate"],
        "rights_holds": dispositions["rights_hold"],
        "source_records": EXPECTED_SCORE_COUNT,
        "strict_public_domain_musicxml": EXPECTED_STRICT_PUBLIC_DOMAIN_COUNT,
        "structure_holds": dispositions["structure_hold"],
    }
    report["excluded"]["rights_holds"] = [
        hold
        for hold in report["excluded"]["rights_holds"]
        if hold.get("collection_id") != COLLECTION_ID
    ] + [_hold(record) for record in records if record["disposition"] == "rights_hold"]
    report["excluded"]["structure_holds"] = [
        hold
        for hold in report["excluded"]["structure_holds"]
        if hold.get("collection_id") != COLLECTION_ID
    ] + [_hold(record) for record in records if record["disposition"] == "structure_hold"]
    report["excluded"]["normalization_backlog"] = {
        "collection_id": COLLECTION_ID,
        "records": dispositions["normalization_candidate"],
        "reason": "requires a lossless normalization profile beyond aligned SATB dyads",
    }
    report["summary"].update(
        {
            "catalog_items": EXPECTED_BASE_ITEMS + EXPECTED_PROMOTED_ITEMS,
            "exact_public_domain_candidates": 4100,
            "rights_holds": 46,
            "source_records": 4146,
            "structure_holds": 17,
            "timeless_truths_items": EXPECTED_PROMOTED_ITEMS,
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
    return {
        "catalog_items": len(imported_items),
        "distinct_arrangements": distinct_arrangements,
        "net_new_titles": net_new_titles,
        "normalization_backlog": dispositions["normalization_candidate"],
        "rights_holds": dispositions["rights_hold"],
        "source_records": len(records),
        "structure_holds": dispositions["structure_hold"],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--inventory", type=Path, default=DEFAULT_INVENTORY)
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--web-catalog", type=Path, default=DEFAULT_WEB_CATALOG)
    args = parser.parse_args()
    try:
        result = import_score(
            inventory_path=args.inventory,
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
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

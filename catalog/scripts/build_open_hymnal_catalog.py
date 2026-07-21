#!/usr/bin/env python3
"""Promote render-compatible Open Hymnal candidates into the product catalog.

This is the intentionally narrow bridge between the generic ingest spike and
the application catalog. It accepts only records with the audited exact public
domain declaration and the two-staff/four-voice shape supported by the current
SATB renderer.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import re
import unicodedata
import xml.etree.ElementTree as ET


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SOURCE = REPOSITORY_ROOT / "data/open-hymnal/raw/OpenHymnal2014.06.abc"
DEFAULT_CATALOG_ROOT = REPOSITORY_ROOT / "catalog"
DEFAULT_WEB_CATALOG = REPOSITORY_ROOT / "apps/web/src/lib/catalog.generated.ts"
CATALOG_REVISION = "2"
CANONICAL_ENCODING_DATE = "2026-07-21"
RIGHTS_DECLARATION_PREFIX = "copyright: public domain."
RIGHTS_STATUS = "technical_candidate_not_production_approved"
EXPECTED_SOURCE_SHA256 = (
    "f75551ce21cfe9439545f3c0d97b4e737a4689ca4c4594a5a51f76fb164daa46"
)
EXPECTED_NORMALIZED_SHA256 = (
    "9837dd05429a2f442982fc7dc01c94664e214318d1ca04859d8c797b9bf30517"
)
EXPECTED_SOURCE_RECORDS = 293
EXPECTED_PD_CANDIDATES = 275
EXPECTED_CATALOG_ITEMS = 262
ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
ENCODING_DATE_RE = re.compile(
    rb"<encoding-date>[^<]+</encoding-date>"
)
TUNE_RE = re.compile(
    r"(?:Music(?: and Setting)?|Tune):.*?['\"]([^'\"]+)['\"]",
    re.IGNORECASE,
)
OH_FIELD_RE = re.compile(r"^%(OH[A-Z]+)\s+(.*?)\s*$")
X_FIELD_RE = re.compile(r"^X:\s*(.*?)\s*$")

KEY_NAMES = {
    -7: "C-flat",
    -6: "G-flat",
    -5: "D-flat",
    -4: "A-flat",
    -3: "E-flat",
    -2: "B-flat",
    -1: "F",
    0: "C",
    1: "G",
    2: "D",
    3: "A",
    4: "E",
    5: "B",
    6: "F-sharp",
    7: "C-sharp",
}


class CatalogBuildError(ValueError):
    """Raised when pinned ingest artifacts cannot produce the expected catalog."""


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _slug(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii").lower()
    return re.sub(r"[^a-z0-9]+", "-", ascii_value).strip("-")


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _descendant_text(element: ET.Element, name: str) -> str:
    for child in element.iter():
        if _local_name(child.tag) == name:
            return (child.text or "").strip()
    return ""


def _direct_children(element: ET.Element, name: str) -> list[ET.Element]:
    return [child for child in element if _local_name(child.tag) == name]


def _source_metadata(source_text: str) -> dict[int, dict[str, str]]:
    """Associate the Open Hymnal metadata block immediately before each X field."""
    result: dict[int, dict[str, str]] = {}
    pending: dict[str, str] = {}
    ordinal = 0
    for line in source_text.splitlines():
        metadata_match = OH_FIELD_RE.match(line)
        if metadata_match:
            pending[metadata_match.group(1)] = metadata_match.group(2)
            continue
        if X_FIELD_RE.match(line):
            ordinal += 1
            result[ordinal] = dict(pending)
            pending.clear()
    return result


def _display_person(source_value: str) -> str:
    people: list[str] = []
    for raw_person in source_value.split(";"):
        person = re.sub(r"\s*\([^)]*\)\s*$", "", raw_person).strip()
        if not person:
            continue
        if "," in person:
            family, given = (value.strip() for value in person.split(",", 1))
            person = f"{given} {family}".strip()
        people.append(person)
    return ", ".join(people) or "Unknown"


def _tune_name(attributions: list[str]) -> str:
    for attribution in attributions:
        match = TUNE_RE.search(attribution)
        if match:
            return match.group(1).strip()
    raise CatalogBuildError("Could not derive a tune name from source attribution.")


def _normalized_musicxml(path: Path) -> bytes:
    raw = path.read_bytes()
    normalized, replacements = ENCODING_DATE_RE.subn(
        f"<encoding-date>{CANONICAL_ENCODING_DATE}</encoding-date>".encode(),
        raw,
    )
    if replacements != 1:
        raise CatalogBuildError(
            f"Expected one MusicXML encoding-date in {path}, found {replacements}."
        )
    return normalized


def _score_facts(data: bytes) -> dict[str, object]:
    root = ET.fromstring(data)
    if _local_name(root.tag) != "score-partwise":
        raise CatalogBuildError("Converted score is not score-partwise MusicXML.")

    parts = _direct_children(root, "part")
    voice_locations: set[tuple[int, str]] = set()
    lyric_locations: set[tuple[int, str]] = set()
    soprano_verse_ids: set[str] = set()
    for part_index, part in enumerate(parts):
        for note in (child for child in part.iter() if _local_name(child.tag) == "note"):
            voice = _descendant_text(note, "voice")
            if voice:
                voice_locations.add((part_index, voice))
            for lyric in _direct_children(note, "lyric"):
                lyric_locations.add((part_index, voice))
                verse_id = lyric.get("number")
                if verse_id and (part_index, voice) == (0, "1"):
                    soprano_verse_ids.add(verse_id)

    return {
        "title": _descendant_text(root, "work-title"),
        "fifths": int(_descendant_text(root, "fifths")),
        "mode": _descendant_text(root, "mode"),
        "parts": len(parts),
        "voices": len(voice_locations),
        "soprano_lyrics": (0, "1") in lyric_locations,
        "verse_ids": sorted(soprano_verse_ids, key=int),
    }


def _assign_ids(records: list[dict[str, object]]) -> None:
    by_slug: defaultdict[str, list[dict[str, object]]] = defaultdict(list)
    for record in records:
        base = _slug(str(record["title"]))
        if not base:
            raise CatalogBuildError(f"Title cannot form a stable ID: {record['title']!r}")
        by_slug[base].append(record)

    used: set[str] = set()
    for base, group in sorted(by_slug.items()):
        for record in group:
            item_id = base
            if len(group) > 1:
                item_id = f"{base}-{_slug(str(record['tune_name']))}"
            if item_id in used:
                item_id = f"{item_id}-{record['source']['record_ordinal']}"
            if not ID_RE.fullmatch(item_id) or item_id in used:
                raise CatalogBuildError(f"Could not assign a unique stable ID for {base!r}.")
            record["id"] = item_id
            used.add(item_id)


def _write_web_catalog(items: list[dict[str, object]], output_path: Path) -> None:
    lines = [
        "// Generated by catalog/scripts/build_open_hymnal_catalog.py.",
        "// Edit the canonical catalog or generator, not this file.",
        "",
        "export const generatedHymns = [",
    ]
    for item in items:
        display = item["display"]
        key_name = str(item["original_key"]["name"])
        lines.extend(
            [
                "  {",
                f"    id: {json.dumps(item['id'], ensure_ascii=False)},",
                f"    slug: {json.dumps(item['id'], ensure_ascii=False)},",
                f"    title: {json.dumps(item['title'], ensure_ascii=False)},",
                f"    textAuthor: {json.dumps(display['text_author'], ensure_ascii=False)},",
                f"    tuneName: {json.dumps(display['tune_name'], ensure_ascii=False)},",
                f"    meter: {json.dumps(display['meter'], ensure_ascii=False)},",
                f"    originalKey: {json.dumps(_slug(key_name), ensure_ascii=False)},",
                f"    scoreSha256: {json.dumps(item['score']['sha256'])},",
                "  },",
            ]
        )
    lines.extend(["] as const;", ""])
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8", newline="\n")


def build_catalog(
    *,
    inventory_path: Path,
    conversion_path: Path,
    musicxml_dir: Path,
    source_path: Path = DEFAULT_SOURCE,
    catalog_root: Path = DEFAULT_CATALOG_ROOT,
    web_catalog_path: Path = DEFAULT_WEB_CATALOG,
) -> dict[str, object]:
    source_bytes = source_path.read_bytes()
    if _sha256_bytes(source_bytes) != EXPECTED_SOURCE_SHA256:
        raise CatalogBuildError("Open Hymnal source does not match the pinned raw hash.")
    source_text = source_bytes.decode("windows-1252")
    if _sha256_bytes(source_text.encode("utf-8")) != EXPECTED_NORMALIZED_SHA256:
        raise CatalogBuildError("Open Hymnal source does not match the normalized hash.")

    inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
    conversion = json.loads(conversion_path.read_text(encoding="utf-8"))
    tunes = inventory.get("tunes", [])
    converted = {record["ordinal"]: record for record in conversion.get("tunes", [])}
    if len(tunes) != EXPECTED_SOURCE_RECORDS or len(converted) != EXPECTED_SOURCE_RECORDS:
        raise CatalogBuildError("Inventory and conversion must contain all 293 source records.")

    source_metadata = _source_metadata(source_text)
    exact_pd_count = 0
    rights_holds: list[dict[str, object]] = []
    structure_holds: list[dict[str, object]] = []
    records: list[dict[str, object]] = []

    for tune in tunes:
        ordinal = tune["ordinal"]
        declarations = [
            value
            for value in tune["headers"].get("C", [])
            if value.startswith(RIGHTS_DECLARATION_PREFIX)
        ]
        if not declarations:
            rights_holds.append(
                {
                    "ordinal": ordinal,
                    "reference": tune["reference"],
                    "title": tune["primary_title"],
                    "reason": "missing_exact_public_domain_declaration",
                }
            )
            continue
        exact_pd_count += 1

        converted_tune = converted[ordinal]
        if converted_tune["status"] != "succeeded":
            raise CatalogBuildError(f"Conversion failed for source ordinal {ordinal}.")
        input_path = musicxml_dir / Path(converted_tune["musicxml_file"]).name
        xml_data = _normalized_musicxml(input_path)
        facts = _score_facts(xml_data)
        if (
            facts["parts"] != 2
            or facts["voices"] != 4
            or not facts["soprano_lyrics"]
        ):
            structure_holds.append(
                {
                    "ordinal": ordinal,
                    "reference": tune["reference"],
                    "title": tune["primary_title"],
                    "reason": "unsupported_satb_shape",
                    "parts": facts["parts"],
                    "voices": facts["voices"],
                    "soprano_lyrics": facts["soprano_lyrics"],
                }
            )
            continue
        if facts["title"] != tune["primary_title"]:
            raise CatalogBuildError(f"Title mismatch for source ordinal {ordinal}.")
        if facts["mode"] != "major":
            raise CatalogBuildError(
                f"Current product key choices do not support {facts['mode']!r} mode."
            )

        headers = tune["headers"]
        attributions = [
            value
            for value in headers.get("C", [])
            if not value.startswith(RIGHTS_DECLARATION_PREFIX)
        ]
        if not attributions:
            raise CatalogBuildError(f"Missing attribution for source ordinal {ordinal}.")
        metadata = source_metadata.get(ordinal, {})
        tune_name = _tune_name(attributions)
        source_reference = " ".join(headers.get("S", [])).strip()
        if not source_reference:
            source_reference = "No music source reference declared in the source record."
        abc_key = str(tune["key"]).split("%", 1)[0].strip()
        fifths = int(facts["fifths"])
        mode = str(facts["mode"])
        score_sha256 = _sha256_bytes(xml_data)

        records.append(
            {
                "available_lines": ["SATB", "S", "A", "T", "B"],
                "display": {
                    "meter": metadata.get("OHMETRICAL", "Irregular"),
                    "text_author": _display_person(metadata.get("OHAUTHOR", "unknown")),
                    "tune_name": tune_name,
                },
                "lyrics": {
                    "available": True,
                    "scope": "soprano_only",
                    "verse_ids": facts["verse_ids"],
                },
                "original_key": {
                    "abc": abc_key,
                    "fifths": fifths,
                    "mode": mode,
                    "name": f"{KEY_NAMES[fifths]} {mode}",
                },
                "rights": {
                    "source_attribution": attributions,
                    "source_declaration": declarations[0],
                    "source_music_reference": source_reference,
                    "status": RIGHTS_STATUS,
                },
                "score": {
                    "canonical_state": "untransposed",
                    "generator": {"name": "abc2xml", "version": "268"},
                    "media_type": "application/vnd.recordare.musicxml+xml",
                    "path": "",
                    "sha256": score_sha256,
                },
                "source": {
                    "artifact_sha256": tune["sha256"],
                    "collection_id": "open-hymnal-2014-06",
                    "record_ordinal": ordinal,
                    "x_reference": tune["reference"],
                },
                "title": facts["title"],
                "_musicxml": xml_data,
                "_cleanup_required": bool(converted_tune["cleanup_required"]),
                "tune_name": tune_name,
            }
        )

    if exact_pd_count != EXPECTED_PD_CANDIDATES:
        raise CatalogBuildError(
            f"Expected {EXPECTED_PD_CANDIDATES} exact-PD candidates, found {exact_pd_count}."
        )
    if len(records) != EXPECTED_CATALOG_ITEMS:
        raise CatalogBuildError(
            f"Expected {EXPECTED_CATALOG_ITEMS} catalog items, found {len(records)}."
        )

    _assign_ids(records)
    scores_dir = catalog_root / "scores"
    scores_dir.mkdir(parents=True, exist_ok=True)
    cleanup_count = 0
    items: list[dict[str, object]] = []
    for record in sorted(records, key=lambda value: str(value["title"]).casefold()):
        item_id = str(record.pop("id"))
        xml_data = record.pop("_musicxml")
        cleanup_count += int(record.pop("_cleanup_required"))
        record.pop("tune_name")
        record["id"] = item_id
        record["score"]["path"] = f"scores/{item_id}.musicxml"
        (scores_dir / f"{item_id}.musicxml").write_bytes(xml_data)
        items.append(record)

    catalog = {
        "catalog_id": "hymn-transposer-technical-preview",
        "catalog_revision": CATALOG_REVISION,
        "items": items,
        "schema_version": 1,
        "source_collections": [
            {
                "encoding": "windows-1252",
                "id": "open-hymnal-2014-06",
                "normalized_utf8_sha256": EXPECTED_NORMALIZED_SHA256,
                "raw_sha256": EXPECTED_SOURCE_SHA256,
                "source_url": "http://openhymnal.org/OpenHymnal2014.06.abc",
            }
        ],
    }
    catalog_root.mkdir(parents=True, exist_ok=True)
    (catalog_root / "catalog.json").write_text(
        json.dumps(catalog, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )

    report = {
        "catalog_revision": CATALOG_REVISION,
        "conversion": {
            "canonical_encoding_date": CANONICAL_ENCODING_DATE,
            "converter": {
                "declared_version": conversion["converter"]["declared_version"],
                "sha256": conversion["converter"]["sha256"],
            },
            "selected_cleanup_required": cleanup_count,
        },
        "excluded": {
            "rights_holds": rights_holds,
            "structure_holds": structure_holds,
        },
        "schema_version": 1,
        "summary": {
            "catalog_items": len(items),
            "exact_public_domain_candidates": exact_pd_count,
            "rights_holds": len(rights_holds),
            "source_records": len(tunes),
            "structure_holds": len(structure_holds),
        },
    }
    (catalog_root / "import-report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    _write_web_catalog(items, web_catalog_path)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inventory", required=True, type=Path)
    parser.add_argument("--conversion", required=True, type=Path)
    parser.add_argument("--musicxml-dir", required=True, type=Path)
    parser.add_argument("--source", default=DEFAULT_SOURCE, type=Path)
    parser.add_argument("--catalog-root", default=DEFAULT_CATALOG_ROOT, type=Path)
    parser.add_argument("--web-catalog", default=DEFAULT_WEB_CATALOG, type=Path)
    args = parser.parse_args()
    try:
        report = build_catalog(
            inventory_path=args.inventory.resolve(),
            conversion_path=args.conversion.resolve(),
            musicxml_dir=args.musicxml_dir.resolve(),
            source_path=args.source.resolve(),
            catalog_root=args.catalog_root.resolve(),
            web_catalog_path=args.web_catalog.resolve(),
        )
    except (CatalogBuildError, KeyError, OSError, ValueError, ET.ParseError) as exc:
        print(f"catalog build failed: {exc}")
        return 2
    summary = report["summary"]
    print(
        f"Built {summary['catalog_items']} catalog items from "
        f"{summary['source_records']} source records; "
        f"held {summary['rights_holds']} for rights and "
        f"{summary['structure_holds']} for structure."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

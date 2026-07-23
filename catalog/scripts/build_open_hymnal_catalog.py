#!/usr/bin/env python3
"""Promote render-compatible public-domain hymn sources into the product catalog.

This is the intentionally narrow bridge between the generic ingest spike and
the application catalog. It accepts only records that pass their source-specific
public-domain gate and the two-staff/four-voice shape supported by the current
SATB renderer.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import re
import struct
import unicodedata
import xml.etree.ElementTree as ET
from zipfile import BadZipFile, ZipFile

from normalize_satb_musicxml import (
    DROP_EMPTY_PARTS,
    NORMALIZER_NAME,
    NORMALIZER_VERSION,
    SPLIT_COMBINED_CHORD_VOICES,
    normalize_satb_musicxml,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SOURCE = REPOSITORY_ROOT / "data/open-hymnal/raw/OpenHymnal2014.06.abc"
DEFAULT_SPLIT_ZIP = (
    REPOSITORY_ROOT / "data/open-hymnal/raw/OpenHymnal2014.06-abc.zip"
)
DEFAULT_CATALOG_ROOT = REPOSITORY_ROOT / "catalog"
DEFAULT_WEB_CATALOG = REPOSITORY_ROOT / "apps/web/src/lib/catalog.generated.ts"
DEFAULT_HYMNS_TO_GOD_MANIFEST = (
    REPOSITORY_ROOT / "data/hymns-to-god/manifest.json"
)
CATALOG_REVISION = "5"
CANONICAL_ENCODING_DATE = "2026-07-21"
RIGHTS_DECLARATION_PREFIX = "copyright: public domain."
RIGHTS_STATUS = "technical_candidate_not_production_approved"
EXPECTED_SOURCE_SHA256 = (
    "f75551ce21cfe9439545f3c0d97b4e737a4689ca4c4594a5a51f76fb164daa46"
)
EXPECTED_NORMALIZED_SHA256 = (
    "9837dd05429a2f442982fc7dc01c94664e214318d1ca04859d8c797b9bf30517"
)
EXPECTED_SPLIT_ZIP_SHA256 = (
    "407ec5ab7ec6b27f698245c3b4b2c7bea1488fabbb56f7ff190849e11fe472cd"
)
EXPECTED_SPLIT_ZIP_NORMALIZED_SHA256 = (
    "245efeb8e0864229f9f9706f4fdb1e23fb7f4ec7f91977d1280da58c075762a7"
)
EXPECTED_CONVERTER_SHA256 = (
    "76cd2c5c4fc44b28ab2ce923f196d23d09b93fcefa8cfa90a10754d38e15b56e"
)
EXPECTED_SOURCE_RECORDS = 293
EXPECTED_PD_CANDIDATES = 275
EXPECTED_SPLIT_ZIP_RECORDS = 306
EXPECTED_SPLIT_ZIP_PD_CANDIDATES = 285
EXPECTED_COMBINED_ITEMS = 269
EXPECTED_SUPPLEMENT_ITEMS = 8
EXPECTED_HYMNS_TO_GOD_RECORDS = 17
EXPECTED_HYMNS_TO_GOD_PD_RECORDS = 16
EXPECTED_HYMNS_TO_GOD_ITEMS = 13
EXPECTED_HYMNS_TO_GOD_RIGHTS_HOLDS = 1
EXPECTED_HYMNS_TO_GOD_STRUCTURE_HOLDS = 3
EXPECTED_CATALOG_ITEMS = 290
HYMNS_TO_GOD_COLLECTION_ID = "hymns-to-god-public-domain-usa"
HYMNS_TO_GOD_GENERATOR_NAME = "hymns-to-god-mup-satb"
HYMNS_TO_GOD_GENERATOR_VERSION = "1"
STRUCTURE_NORMALIZATIONS = {
    30: SPLIT_COMBINED_CHORD_VOICES,
    134: SPLIT_COMBINED_CHORD_VOICES,
    138: SPLIT_COMBINED_CHORD_VOICES,
    157: DROP_EMPTY_PARTS,
    223: SPLIT_COMBINED_CHORD_VOICES,
    248: SPLIT_COMBINED_CHORD_VOICES,
    283: SPLIT_COMBINED_CHORD_VOICES,
}
SUPPLEMENT_ENTRIES = (
    "A_Child_of_The_King-Binghamton.abc",
    "Good_King_Wenceslas-Tempus_Adest_Floridum.abc",
    "He_Keeps_Me_Singing-He_Keeps_Me_Singing-Melody_of_Love.abc",
    "Jesus_Is_All_The_World_to_Me-Jesus_Is_All_The_World_to_Me.abc",
    "Lord_Of_Our_Life-Iste_Confessor-Rouen.abc",
    "Moment_By_Moment-Whittle.abc",
    "My_Saviors_Love-My_Saviors_Love-I_Stand_Amazed_in_the_Presence.abc",
    "Rescue_the_Perishing-Rescue_the_Perishing.abc",
)
ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
ENCODING_DATE_RE = re.compile(
    rb"<encoding-date>[^<]+</encoding-date>"
)
TUNE_RE = re.compile(
    r"(?:Music(?: and Setting)?|Tune)\s*:?\s*.*?['\"]([^'\"]+)['\"]",
    re.IGNORECASE,
)
OH_FIELD_RE = re.compile(r"^%(OH[A-Z]+)\s+(.*?)\s*$")
X_FIELD_RE = re.compile(r"^X:\s*(.*?)\s*$")

MAJOR_KEY_NAMES = {
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
MINOR_KEY_NAMES = {
    -7: "A-flat",
    -6: "E-flat",
    -5: "B-flat",
    -4: "F",
    -3: "C",
    -2: "G",
    -1: "D",
    0: "A",
    1: "E",
    2: "B",
    3: "F-sharp",
    4: "C-sharp",
    5: "G-sharp",
    6: "D-sharp",
    7: "A-sharp",
}


class CatalogBuildError(ValueError):
    """Raised when pinned ingest artifacts cannot produce the expected catalog."""


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _normalized_zip_sha256(archive: ZipFile) -> str:
    """Hash decoded ABC entries with length framing in archive order."""
    digest = hashlib.sha256()
    for info in archive.infolist():
        if info.is_dir() or not info.filename.lower().endswith(".abc"):
            continue
        name = info.filename.encode("utf-8")
        normalized = archive.read(info).decode("windows-1252").encode("utf-8")
        digest.update(struct.pack(">I", len(name)))
        digest.update(name)
        digest.update(struct.pack(">Q", len(normalized)))
        digest.update(normalized)
    return digest.hexdigest()


def _slug(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii").lower()
    return re.sub(r"[^a-z0-9]+", "-", ascii_value).strip("-")


def _key_name(fifths: int, mode: str) -> str:
    names = MAJOR_KEY_NAMES if mode == "major" else MINOR_KEY_NAMES
    try:
        return f"{names[fifths]} {mode}"
    except KeyError as exc:
        raise CatalogBuildError(
            f"Unsupported key signature {fifths!r} for {mode!r} mode."
        ) from exc


def _abc_key(fifths: int, mode: str) -> str:
    tonic = _key_name(fifths, mode).removesuffix(f" {mode}")
    tonic = tonic.replace("-flat", "b").replace("-sharp", "#")
    return tonic + ("m" if mode == "minor" else "")


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
        source_label = (
            "HymnsToGod"
            if item["source"]["collection_id"] == HYMNS_TO_GOD_COLLECTION_ID
            else "Open Hymnal"
        )
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
                f"    sourceLabel: {json.dumps(source_label)},",
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
    supplement_inventory_path: Path,
    supplement_conversion_path: Path,
    supplement_musicxml_dir: Path,
    hymns_to_god_musicxml_dir: Path,
    hymns_to_god_manifest_path: Path = DEFAULT_HYMNS_TO_GOD_MANIFEST,
    source_path: Path = DEFAULT_SOURCE,
    split_zip_path: Path = DEFAULT_SPLIT_ZIP,
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
    if (
        conversion.get("converter", {}).get("declared_version") != "268"
        or conversion.get("converter", {}).get("sha256")
        != EXPECTED_CONVERTER_SHA256
    ):
        raise CatalogBuildError("Combined conversion did not use pinned abc2xml 268.")
    tunes = inventory.get("tunes", [])
    converted = {record["ordinal"]: record for record in conversion.get("tunes", [])}
    if len(tunes) != EXPECTED_SOURCE_RECORDS or len(converted) != EXPECTED_SOURCE_RECORDS:
        raise CatalogBuildError("Inventory and conversion must contain all 293 source records.")

    if _sha256_bytes(split_zip_path.read_bytes()) != EXPECTED_SPLIT_ZIP_SHA256:
        raise CatalogBuildError("Open Hymnal split ZIP does not match the pinned raw hash.")
    supplement_inventory = json.loads(
        supplement_inventory_path.read_text(encoding="utf-8")
    )
    supplement_conversion = json.loads(
        supplement_conversion_path.read_text(encoding="utf-8")
    )
    if (
        supplement_conversion.get("converter", {}).get("declared_version") != "268"
        or supplement_conversion.get("converter", {}).get("sha256")
        != EXPECTED_CONVERTER_SHA256
    ):
        raise CatalogBuildError("Supplement conversion did not use pinned abc2xml 268.")
    supplement_tunes = supplement_inventory.get("tunes", [])
    supplement_converted = {
        record["ordinal"]: record
        for record in supplement_conversion.get("tunes", [])
    }
    if (
        len(supplement_tunes) != EXPECTED_SUPPLEMENT_ITEMS
        or len(supplement_converted) != EXPECTED_SUPPLEMENT_ITEMS
    ):
        raise CatalogBuildError(
            f"Supplement inventory and conversion must contain "
            f"{EXPECTED_SUPPLEMENT_ITEMS} records."
        )

    source_metadata = _source_metadata(source_text)
    exact_pd_count = 0
    rights_holds: list[dict[str, object]] = []
    structure_holds: list[dict[str, object]] = []
    records: list[dict[str, object]] = []
    normalized_ordinals: set[int] = set()
    normalization_counts: defaultdict[str, int] = defaultdict(int)

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
        normalization_operation = STRUCTURE_NORMALIZATIONS.get(ordinal)
        normalization_operations: tuple[str, ...] = ()
        if normalization_operation is not None:
            normalized = normalize_satb_musicxml(xml_data, normalization_operation)
            xml_data = normalized.data
            normalization_operations = normalized.operations
            normalized_ordinals.add(ordinal)
            for operation in normalization_operations:
                normalization_counts[operation] += 1
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
        if facts["mode"] not in {"major", "minor"}:
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
        score: dict[str, object] = {
            "canonical_state": "untransposed",
            "generator": {"name": "abc2xml", "version": "268"},
            "media_type": "application/vnd.recordare.musicxml+xml",
            "path": "",
            "sha256": score_sha256,
        }
        if normalization_operations:
            score["normalization"] = {
                "name": NORMALIZER_NAME,
                "operations": list(normalization_operations),
                "version": NORMALIZER_VERSION,
            }

        records.append(
            {
                "available_lines": ["SATB", "S", "A", "T", "B"],
                "display": {
                    "meter": metadata.get("OHMETRICAL") or "Irregular",
                    "text_author": _display_person(
                        metadata.get("OHAUTHOR") or "unknown"
                    ),
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
                    "name": _key_name(fifths, mode),
                },
                "rights": {
                    "source_attribution": attributions,
                    "source_declaration": declarations[0],
                    "source_music_reference": source_reference,
                    "status": RIGHTS_STATUS,
                },
                "score": score,
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
    if normalized_ordinals != set(STRUCTURE_NORMALIZATIONS):
        raise CatalogBuildError(
            "The pinned SATB normalization set was not applied exactly once."
        )

    supplement_by_entry = {
        str(tune.get("source_entry")): tune for tune in supplement_tunes
    }
    if set(supplement_by_entry) != set(SUPPLEMENT_ENTRIES):
        raise CatalogBuildError(
            "Supplement inventory does not contain the pinned compatible entry set."
        )
    supplement_cleanup_count = 0
    try:
        with ZipFile(split_zip_path) as archive:
            abc_infos = [
                info
                for info in archive.infolist()
                if not info.is_dir() and info.filename.lower().endswith(".abc")
            ]
            if len(abc_infos) != EXPECTED_SPLIT_ZIP_RECORDS:
                raise CatalogBuildError(
                    f"Expected {EXPECTED_SPLIT_ZIP_RECORDS} ABC entries in the split ZIP, "
                    f"found {len(abc_infos)}."
                )
            normalized_zip_sha256 = _normalized_zip_sha256(archive)
            if normalized_zip_sha256 != EXPECTED_SPLIT_ZIP_NORMALIZED_SHA256:
                raise CatalogBuildError(
                    "Open Hymnal split ZIP does not match the normalized collection hash."
                )
            archive_ordinals = {
                info.filename: ordinal
                for ordinal, info in enumerate(abc_infos, start=1)
            }

            for entry_path in SUPPLEMENT_ENTRIES:
                tune = supplement_by_entry[entry_path]
                ordinal = int(tune["ordinal"])
                archive_ordinal = archive_ordinals[entry_path]
                if tune.get("source_archive_ordinal") != archive_ordinal:
                    raise CatalogBuildError(
                        f"Archive ordinal drift for supplement entry {entry_path!r}."
                    )

                entry_bytes = archive.read(entry_path)
                entry_text = entry_bytes.decode("windows-1252")
                if tune.get("source_entry_raw_sha256") != _sha256_bytes(entry_bytes):
                    raise CatalogBuildError(
                        f"Raw entry hash drift for supplement entry {entry_path!r}."
                    )
                if tune.get("sha256") != _sha256_bytes(entry_text.encode("utf-8")):
                    raise CatalogBuildError(
                        f"Normalized entry hash drift for supplement entry {entry_path!r}."
                    )

                headers = tune["headers"]
                declarations = [
                    value
                    for value in headers.get("C", [])
                    if value.startswith(RIGHTS_DECLARATION_PREFIX)
                ]
                if not declarations:
                    raise CatalogBuildError(
                        f"Missing exact public-domain declaration for {entry_path!r}."
                    )

                converted_tune = supplement_converted[ordinal]
                if (
                    converted_tune["status"] != "succeeded"
                    or converted_tune["input_sha256"] != tune["sha256"]
                ):
                    raise CatalogBuildError(
                        f"Conversion failed or input drifted for {entry_path!r}."
                    )
                input_path = (
                    supplement_musicxml_dir
                    / Path(str(converted_tune["musicxml_file"])).name
                )
                xml_data = _normalized_musicxml(input_path)
                facts = _score_facts(xml_data)
                if (
                    facts["parts"] != 2
                    or facts["voices"] != 4
                    or not facts["soprano_lyrics"]
                ):
                    raise CatalogBuildError(
                        f"Pinned supplement entry no longer has the supported SATB shape: "
                        f"{entry_path!r}."
                    )
                if facts["title"] != tune["primary_title"]:
                    raise CatalogBuildError(
                        f"Title mismatch for supplement entry {entry_path!r}."
                    )
                if facts["mode"] not in {"major", "minor"}:
                    raise CatalogBuildError(
                        f"Current product key choices do not support "
                        f"{facts['mode']!r} mode."
                    )

                attributions = [
                    value
                    for value in headers.get("C", [])
                    if not value.startswith(RIGHTS_DECLARATION_PREFIX)
                ]
                if not attributions:
                    raise CatalogBuildError(
                        f"Missing attribution for supplement entry {entry_path!r}."
                    )
                metadata = _source_metadata(entry_text).get(1, {})
                tune_name = _tune_name(attributions)
                source_reference = " ".join(headers.get("S", [])).strip()
                if not source_reference:
                    source_reference = (
                        "No music source reference declared in the source record."
                    )
                abc_key = str(tune["key"]).split("%", 1)[0].strip()
                fifths = int(facts["fifths"])
                mode = str(facts["mode"])
                score_sha256 = _sha256_bytes(xml_data)

                records.append(
                    {
                        "available_lines": ["SATB", "S", "A", "T", "B"],
                        "display": {
                            "meter": metadata.get("OHMETRICAL") or "Irregular",
                            "text_author": _display_person(
                                metadata.get("OHAUTHOR") or "unknown"
                            ),
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
                            "name": _key_name(fifths, mode),
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
                            "collection_id": "open-hymnal-2014-06-split-zip",
                            "entry_path": entry_path,
                            "record_ordinal": archive_ordinal,
                            "x_reference": tune["reference"],
                        },
                        "title": facts["title"],
                        "_musicxml": xml_data,
                        "_cleanup_required": bool(
                            converted_tune["cleanup_required"]
                        ),
                        "tune_name": tune_name,
                    }
                )
                supplement_cleanup_count += int(
                    bool(converted_tune["cleanup_required"])
                )
    except BadZipFile as exc:
        raise CatalogBuildError(f"Invalid Open Hymnal split ZIP: {exc}") from exc

    hymns_to_god_manifest_bytes = hymns_to_god_manifest_path.read_bytes()
    hymns_to_god_manifest_sha256 = _sha256_bytes(hymns_to_god_manifest_bytes)
    hymns_to_god_manifest = json.loads(
        hymns_to_god_manifest_bytes.decode("utf-8")
    )
    if (
        hymns_to_god_manifest.get("dataset_id") != HYMNS_TO_GOD_COLLECTION_ID
        or hymns_to_god_manifest.get("conversion_profile", {}).get("name")
        != HYMNS_TO_GOD_GENERATOR_NAME
        or hymns_to_god_manifest.get("conversion_profile", {}).get("version")
        != HYMNS_TO_GOD_GENERATOR_VERSION
    ):
        raise CatalogBuildError("HymnsToGod manifest identity or converter drifted.")
    hymns_to_god_records = hymns_to_god_manifest.get("records", [])
    if len(hymns_to_god_records) != EXPECTED_HYMNS_TO_GOD_RECORDS:
        raise CatalogBuildError(
            f"Expected {EXPECTED_HYMNS_TO_GOD_RECORDS} HymnsToGod records, "
            f"found {len(hymns_to_god_records)}."
        )
    hymns_to_god_raw_root = hymns_to_god_manifest_path.parent / "raw"
    hymns_to_god_dispositions: defaultdict[str, int] = defaultdict(int)
    hymns_to_god_item_count = 0
    seen_hymns_to_god_ids: set[str] = set()
    for ordinal, source_record in enumerate(hymns_to_god_records, start=1):
        source_id = str(source_record["id"])
        if source_id in seen_hymns_to_god_ids or not ID_RE.fullmatch(source_id):
            raise CatalogBuildError(
                f"Invalid or duplicate HymnsToGod ID {source_id!r}."
            )
        seen_hymns_to_god_ids.add(source_id)
        disposition = str(source_record["disposition"])
        hymns_to_god_dispositions[disposition] += 1

        page_path = hymns_to_god_raw_root / str(source_record["page_file"])
        page_bytes = page_path.read_bytes()
        if _sha256_bytes(page_bytes) != source_record["page_sha256"]:
            raise CatalogBuildError(
                f"HymnsToGod page hash drift for {source_id!r}."
            )
        page_declaration = str(source_record["page_rights_declaration"])
        page_declaration_value = page_declaration.removeprefix("Copyright: ")
        if page_declaration_value.encode("utf-8") not in page_bytes:
            raise CatalogBuildError(
                f"HymnsToGod page declaration drift for {source_id!r}."
            )

        if disposition == "rights_hold":
            rights_holds.append(
                {
                    "collection_id": HYMNS_TO_GOD_COLLECTION_ID,
                    "record_ordinal": ordinal,
                    "title": source_record["title"],
                    "reason": "individual_page_rights_unknown",
                }
            )
            continue

        source_path = (
            hymns_to_god_raw_root
            / "mup"
            / str(source_record["source_file"])
        )
        source_bytes = source_path.read_bytes()
        if _sha256_bytes(source_bytes) != source_record["source_sha256"]:
            raise CatalogBuildError(
                f"HymnsToGod Mup source hash drift for {source_id!r}."
            )
        source_code_declaration = str(
            source_record["source_code_declaration"]
        )
        donated_source_pattern = re.compile(
            rb"this (?:mup )?(?:source code|code|file) is donated to the "
            rb"public domain\.",
            re.IGNORECASE,
        )
        if (
            source_code_declaration
            != "This MUP code is donated to the public domain."
            or donated_source_pattern.search(source_bytes) is None
        ):
            raise CatalogBuildError(
                f"HymnsToGod Mup code declaration drift for {source_id!r}."
            )

        if disposition == "structure_hold":
            structure_holds.append(
                {
                    "collection_id": HYMNS_TO_GOD_COLLECTION_ID,
                    "record_ordinal": ordinal,
                    "title": source_record["title"],
                    "reason": "unsupported_satb_shape",
                    "detail": source_record["hold_reason"],
                }
            )
            continue
        if disposition != "eligible":
            raise CatalogBuildError(
                f"Unsupported HymnsToGod disposition {disposition!r}."
            )

        input_path = hymns_to_god_musicxml_dir / f"{source_id}.musicxml"
        xml_data = _normalized_musicxml(input_path)
        facts = _score_facts(xml_data)
        if (
            facts["parts"] != 2
            or facts["voices"] != 4
            or not facts["soprano_lyrics"]
        ):
            raise CatalogBuildError(
                f"HymnsToGod item {source_id!r} no longer has the supported "
                "SATB shape."
            )
        if facts["title"] != source_record["title"]:
            raise CatalogBuildError(
                f"Title mismatch for HymnsToGod item {source_id!r}."
            )
        if facts["mode"] not in {"major", "minor"}:
            raise CatalogBuildError(
                f"HymnsToGod item {source_id!r} has unsupported mode "
                f"{facts['mode']!r}."
            )

        fifths = int(facts["fifths"])
        mode = str(facts["mode"])
        score_sha256 = _sha256_bytes(xml_data)
        records.append(
            {
                "available_lines": ["SATB", "S", "A", "T", "B"],
                "display": {
                    "meter": "Irregular",
                    "text_author": source_record["lyricist"],
                    "tune_name": source_record["tune_name"],
                },
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
                        f"Lyrics: {source_record['lyricist']}.",
                        f"Music: {source_record['composer']}.",
                        "Mup transcription published by HymnsToGod.org.",
                    ],
                    "source_declaration": page_declaration,
                    "source_music_reference": str(source_record["source_url"]),
                    "status": RIGHTS_STATUS,
                },
                "score": {
                    "canonical_state": "untransposed",
                    "generator": {
                        "name": HYMNS_TO_GOD_GENERATOR_NAME,
                        "version": HYMNS_TO_GOD_GENERATOR_VERSION,
                    },
                    "media_type": "application/vnd.recordare.musicxml+xml",
                    "path": "",
                    "sha256": score_sha256,
                },
                "source": {
                    "artifact_sha256": source_record["source_sha256"],
                    "collection_id": HYMNS_TO_GOD_COLLECTION_ID,
                    "record_ordinal": ordinal,
                    "record_reference": source_id,
                    "record_url": source_record["page_url"],
                },
                "title": facts["title"],
                "_musicxml": xml_data,
                "_cleanup_required": False,
                "_pinned_id": source_id,
                "tune_name": source_record["tune_name"],
            }
        )
        hymns_to_god_item_count += 1

    if (
        hymns_to_god_item_count != EXPECTED_HYMNS_TO_GOD_ITEMS
        or hymns_to_god_dispositions
        != {
            "eligible": EXPECTED_HYMNS_TO_GOD_ITEMS,
            "rights_hold": EXPECTED_HYMNS_TO_GOD_RIGHTS_HOLDS,
            "structure_hold": EXPECTED_HYMNS_TO_GOD_STRUCTURE_HOLDS,
        }
    ):
        raise CatalogBuildError(
            "HymnsToGod eligible/rights/structure disposition counts drifted."
        )

    if len(records) != EXPECTED_CATALOG_ITEMS:
        raise CatalogBuildError(
            f"Expected {EXPECTED_CATALOG_ITEMS} catalog items, found {len(records)}."
        )

    _assign_ids(records)
    for record in records:
        pinned_id = record.pop("_pinned_id", None)
        if pinned_id is not None and record["id"] != pinned_id:
            raise CatalogBuildError(
                f"HymnsToGod stable ID drift: expected {pinned_id!r}, "
                f"generated {record['id']!r}."
            )
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
            },
            {
                "encoding": "windows-1252",
                "id": "open-hymnal-2014-06-split-zip",
                "normalized_utf8_sha256": EXPECTED_SPLIT_ZIP_NORMALIZED_SHA256,
                "raw_sha256": EXPECTED_SPLIT_ZIP_SHA256,
                "source_url": "http://openhymnal.org/OpenHymnal2014.06-abc.zip",
            },
            {
                "encoding": "utf-8",
                "id": HYMNS_TO_GOD_COLLECTION_ID,
                "manifest_sha256": hymns_to_god_manifest_sha256,
                "source_url": hymns_to_god_manifest["upstream"][
                    "public_domain_index_url"
                ],
            },
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
            "satb_normalizations": {
                "name": NORMALIZER_NAME,
                "operation_counts": dict(sorted(normalization_counts.items())),
                "version": NORMALIZER_VERSION,
            },
            "hymns_to_god": {
                "generator": {
                    "name": HYMNS_TO_GOD_GENERATOR_NAME,
                    "version": HYMNS_TO_GOD_GENERATOR_VERSION,
                },
                "mup_version": hymns_to_god_manifest["conversion_profile"][
                    "mup_version"
                ],
            },
            "selected_cleanup_required": cleanup_count,
            "supplement_cleanup_required": supplement_cleanup_count,
        },
        "excluded": {
            "rights_holds": rights_holds,
            "structure_holds": structure_holds,
        },
        "schema_version": 1,
        "source_breakdown": {
            "combined_abc": {
                "catalog_items": EXPECTED_COMBINED_ITEMS,
                "exact_public_domain_candidates": exact_pd_count,
                "source_records": len(tunes),
            },
            "split_zip": {
                "archive_exact_public_domain_candidates": (
                    EXPECTED_SPLIT_ZIP_PD_CANDIDATES
                ),
                "archive_records": EXPECTED_SPLIT_ZIP_RECORDS,
                "selected_compatible_additions": EXPECTED_SUPPLEMENT_ITEMS,
            },
            "hymns_to_god": {
                "catalog_items": hymns_to_god_item_count,
                "public_domain_page_declarations": (
                    EXPECTED_HYMNS_TO_GOD_PD_RECORDS
                ),
                "rights_holds": EXPECTED_HYMNS_TO_GOD_RIGHTS_HOLDS,
                "source_records": EXPECTED_HYMNS_TO_GOD_RECORDS,
                "structure_holds": EXPECTED_HYMNS_TO_GOD_STRUCTURE_HOLDS,
            },
        },
        "summary": {
            "catalog_items": len(items),
            "exact_public_domain_candidates": (
                exact_pd_count
                + EXPECTED_SUPPLEMENT_ITEMS
                + EXPECTED_HYMNS_TO_GOD_PD_RECORDS
            ),
            "rights_holds": len(rights_holds),
            "source_records": (
                len(tunes)
                + EXPECTED_SUPPLEMENT_ITEMS
                + EXPECTED_HYMNS_TO_GOD_RECORDS
            ),
            "structure_holds": len(structure_holds),
            "supplement_items": EXPECTED_SUPPLEMENT_ITEMS,
            "hymns_to_god_items": hymns_to_god_item_count,
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
    parser.add_argument("--supplement-inventory", required=True, type=Path)
    parser.add_argument("--supplement-conversion", required=True, type=Path)
    parser.add_argument("--supplement-musicxml-dir", required=True, type=Path)
    parser.add_argument("--hymns-to-god-musicxml-dir", required=True, type=Path)
    parser.add_argument(
        "--hymns-to-god-manifest",
        default=DEFAULT_HYMNS_TO_GOD_MANIFEST,
        type=Path,
    )
    parser.add_argument("--source", default=DEFAULT_SOURCE, type=Path)
    parser.add_argument("--split-zip", default=DEFAULT_SPLIT_ZIP, type=Path)
    parser.add_argument("--catalog-root", default=DEFAULT_CATALOG_ROOT, type=Path)
    parser.add_argument("--web-catalog", default=DEFAULT_WEB_CATALOG, type=Path)
    args = parser.parse_args()
    try:
        report = build_catalog(
            inventory_path=args.inventory.resolve(),
            conversion_path=args.conversion.resolve(),
            musicxml_dir=args.musicxml_dir.resolve(),
            supplement_inventory_path=args.supplement_inventory.resolve(),
            supplement_conversion_path=args.supplement_conversion.resolve(),
            supplement_musicxml_dir=args.supplement_musicxml_dir.resolve(),
            hymns_to_god_musicxml_dir=(
                args.hymns_to_god_musicxml_dir.resolve()
            ),
            hymns_to_god_manifest_path=args.hymns_to_god_manifest.resolve(),
            source_path=args.source.resolve(),
            split_zip_path=args.split_zip.resolve(),
            catalog_root=args.catalog_root.resolve(),
            web_catalog_path=args.web_catalog.resolve(),
        )
    except (CatalogBuildError, KeyError, OSError, ValueError, ET.ParseError) as exc:
        print(f"catalog build failed: {exc}")
        return 2
    summary = report["summary"]
    print(
        f"Built {summary['catalog_items']} catalog items from "
        f"{summary['source_records']} evaluated source records; "
        f"held {summary['rights_holds']} for rights and "
        f"{summary['structure_holds']} for structure."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

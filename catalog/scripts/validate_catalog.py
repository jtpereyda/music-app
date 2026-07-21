#!/usr/bin/env python3
from __future__ import annotations

from collections.abc import Mapping
import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Any
import xml.etree.ElementTree as ET


CATALOG_ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = CATALOG_ROOT / "catalog.json"
SCHEMA_PATH = CATALOG_ROOT / "catalog.schema.json"
ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
EXPECTED_LINES = ["SATB", "S", "A", "T", "B"]
RIGHTS_STATUS = "technical_candidate_not_production_approved"


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _direct_children(element: ET.Element, name: str) -> list[ET.Element]:
    return [child for child in element if _local_name(child.tag) == name]


def _first_descendant_text(element: ET.Element, name: str) -> str:
    for child in element.iter():
        if _local_name(child.tag) == name:
            return (child.text or "").strip()
    return ""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _error(errors: list[str], item_id: str, message: str) -> None:
    errors.append(f"{item_id}: {message}")


def _validate_score(
    item: Mapping[str, Any],
    *,
    catalog_root: Path,
    errors: list[str],
) -> None:
    item_id = str(item.get("id", "<missing-id>"))
    score = item.get("score")
    if not isinstance(score, Mapping):
        _error(errors, item_id, "score must be an object")
        return
    relative_path = score.get("path")
    if not isinstance(relative_path, str):
        _error(errors, item_id, "score.path must be a string")
        return
    score_path = (catalog_root / relative_path).resolve()
    try:
        score_path.relative_to(catalog_root.resolve())
    except ValueError:
        _error(errors, item_id, "score.path escapes the catalog directory")
        return
    if not score_path.is_file():
        _error(errors, item_id, f"score file does not exist: {relative_path}")
        return
    actual_sha256 = _sha256(score_path)
    if actual_sha256 != score.get("sha256"):
        _error(
            errors,
            item_id,
            f"score SHA-256 mismatch: expected {score.get('sha256')}, got {actual_sha256}",
        )
    try:
        root = ET.parse(score_path).getroot()
    except ET.ParseError as exc:
        _error(errors, item_id, f"invalid MusicXML: {exc}")
        return
    if _local_name(root.tag) != "score-partwise":
        _error(errors, item_id, f"expected score-partwise, found {_local_name(root.tag)}")
        return
    work_title = _first_descendant_text(root, "work-title")
    if work_title != item.get("title"):
        _error(errors, item_id, f"work-title {work_title!r} does not match catalog title")

    key = item.get("original_key", {})
    fifths = _first_descendant_text(root, "fifths")
    mode = _first_descendant_text(root, "mode")
    if fifths != str(key.get("fifths")) or mode != key.get("mode"):
        _error(
            errors,
            item_id,
            f"MusicXML key {fifths}:{mode} does not match catalog original_key",
        )

    parts = _direct_children(root, "part")
    voice_locations: set[tuple[int, str]] = set()
    lyric_locations: set[tuple[int, str]] = set()
    soprano_verse_ids: set[str] = set()
    for part_index, part in enumerate(parts):
        for note in (child for child in part.iter() if _local_name(child.tag) == "note"):
            voice = _first_descendant_text(note, "voice")
            if voice:
                voice_locations.add((part_index, voice))
            lyrics = _direct_children(note, "lyric")
            if lyrics:
                lyric_locations.add((part_index, voice))
            for lyric in lyrics:
                verse_id = lyric.get("number")
                if verse_id and (part_index, voice) == (0, "1"):
                    soprano_verse_ids.add(verse_id)
    if len(parts) != 2 or len(voice_locations) != 4:
        _error(
            errors,
            item_id,
            f"expected two parts/four voices, found {len(parts)} parts/{len(voice_locations)} voices",
        )
    if (0, "1") not in lyric_locations:
        _error(
            errors,
            item_id,
            f"expected lyrics on first-part voice 1, found {sorted(lyric_locations)}",
        )
    declared_verses = set(item.get("lyrics", {}).get("verse_ids", []))
    if soprano_verse_ids != declared_verses:
        _error(
            errors,
            item_id,
            f"soprano verse IDs {sorted(soprano_verse_ids)} "
            f"do not match {sorted(declared_verses)}",
        )
    encoders = [
        (element.text or "").strip()
        for element in root.iter()
        if _local_name(element.tag) == "encoder"
    ]
    if "abc2xml version 268" not in encoders:
        _error(errors, item_id, "score does not declare abc2xml version 268")


def validate_catalog_data(data: Any, *, catalog_root: Path = CATALOG_ROOT) -> list[str]:
    errors: list[str] = []
    if not isinstance(data, Mapping):
        return ["catalog: root must be an object"]
    if data.get("schema_version") != 1:
        errors.append("catalog: schema_version must be 1")
    if data.get("catalog_id") != "hymn-transposer-technical-preview":
        errors.append("catalog: unexpected catalog_id")

    collections = data.get("source_collections")
    if not isinstance(collections, list) or not collections:
        errors.append("catalog: source_collections must be a non-empty array")
        collections = []
    collection_ids: set[str] = set()
    for collection in collections:
        if not isinstance(collection, Mapping):
            errors.append("catalog: source collection must be an object")
            continue
        collection_id = collection.get("id")
        if not isinstance(collection_id, str) or not ID_RE.fullmatch(collection_id):
            errors.append(f"catalog: invalid source collection ID {collection_id!r}")
        else:
            collection_ids.add(collection_id)
        for field in ("raw_sha256", "normalized_utf8_sha256"):
            value = collection.get(field)
            if not isinstance(value, str) or not SHA256_RE.fullmatch(value):
                errors.append(f"catalog: invalid {field} for {collection_id!r}")

    items = data.get("items")
    if not isinstance(items, list) or not items:
        errors.append("catalog: items must be a non-empty array")
        return errors
    seen_ids: set[str] = set()
    seen_paths: set[str] = set()
    source_records: set[tuple[str, int, str]] = set()
    for item in items:
        if not isinstance(item, Mapping):
            errors.append("catalog: item must be an object")
            continue
        item_id = item.get("id")
        display_id = str(item_id or "<missing-id>")
        if not isinstance(item_id, str) or not ID_RE.fullmatch(item_id):
            _error(errors, display_id, "invalid stable ID")
        elif item_id in seen_ids:
            _error(errors, display_id, "duplicate stable ID")
        else:
            seen_ids.add(item_id)
        if not isinstance(item.get("title"), str) or not item["title"].strip():
            _error(errors, display_id, "title must be a non-empty string")
        if item.get("available_lines") != EXPECTED_LINES:
            _error(errors, display_id, f"available_lines must be {EXPECTED_LINES}")

        display = item.get("display")
        if not isinstance(display, Mapping):
            _error(errors, display_id, "display must be an object")
        else:
            for field in ("meter", "text_author", "tune_name"):
                value = display.get(field)
                if not isinstance(value, str) or not value.strip():
                    _error(errors, display_id, f"display.{field} must be non-empty")

        lyrics = item.get("lyrics")
        if not isinstance(lyrics, Mapping):
            _error(errors, display_id, "lyrics must be an object")
        elif lyrics.get("available") is not True or lyrics.get("scope") != "soprano_only":
            _error(errors, display_id, "lyrics must be available with soprano_only scope")

        rights = item.get("rights")
        if not isinstance(rights, Mapping):
            _error(errors, display_id, "rights must be an object")
        else:
            if rights.get("status") != RIGHTS_STATUS:
                _error(errors, display_id, f"rights.status must be {RIGHTS_STATUS}")
            declaration = rights.get("source_declaration")
            if not isinstance(declaration, str) or not declaration.startswith(
                "copyright: public domain."
            ):
                _error(errors, display_id, "missing exact public-domain source declaration")

        source = item.get("source")
        if not isinstance(source, Mapping):
            _error(errors, display_id, "source must be an object")
        else:
            collection_id = source.get("collection_id")
            if collection_id not in collection_ids:
                _error(errors, display_id, f"unknown collection_id {collection_id!r}")
            artifact_sha256 = source.get("artifact_sha256")
            if not isinstance(artifact_sha256, str) or not SHA256_RE.fullmatch(
                artifact_sha256
            ):
                _error(errors, display_id, "invalid source artifact SHA-256")
            ordinal = source.get("record_ordinal")
            x_reference = source.get("x_reference")
            if not isinstance(ordinal, int) or ordinal < 1:
                _error(errors, display_id, "record_ordinal must be a positive integer")
            if not isinstance(x_reference, str) or not x_reference:
                _error(errors, display_id, "x_reference must be a non-empty string")
            if isinstance(ordinal, int) and isinstance(x_reference, str):
                source_record = (str(collection_id), ordinal, x_reference)
                if source_record in source_records:
                    _error(errors, display_id, "duplicate source record")
                source_records.add(source_record)

        score = item.get("score")
        if isinstance(score, Mapping):
            score_path = score.get("path")
            if not isinstance(score_path, str):
                _error(errors, display_id, "score.path must be a string")
            elif score_path in seen_paths:
                _error(errors, display_id, "duplicate score.path")
            else:
                seen_paths.add(score_path)
            score_sha256 = score.get("sha256")
            if not isinstance(score_sha256, str) or not SHA256_RE.fullmatch(score_sha256):
                _error(errors, display_id, "invalid score SHA-256")
            if score.get("canonical_state") != "untransposed":
                _error(errors, display_id, "score must be canonical and untransposed")
        _validate_score(item, catalog_root=catalog_root, errors=errors)
    return errors


def main() -> int:
    try:
        catalog_data = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
        schema_data = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"catalog validation failed: {exc}", file=sys.stderr)
        return 2
    if schema_data.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
        print("catalog validation failed: schema is not draft 2020-12", file=sys.stderr)
        return 2
    errors = validate_catalog_data(catalog_data)
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        print(f"Catalog invalid: {len(errors)} error(s).", file=sys.stderr)
        return 1
    print(f"Catalog valid: {len(catalog_data['items'])} canonical technical candidates.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

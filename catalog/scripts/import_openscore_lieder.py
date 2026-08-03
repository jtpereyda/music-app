#!/usr/bin/env python3
"""Import the pinned OpenScore Lieder MusicXML corpus into the catalog.

The upstream repository contains both version-control sources and direct MXL
exports.  This importer admits only rows present in ``data/scores.tsv`` so
that every promoted score has stable, structured metadata.  Canonical catalog
scores are byte-for-byte copies of the pinned MXL artifacts.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import shutil
import sys
from typing import Any
import unicodedata
import xml.etree.ElementTree as ET
from zipfile import BadZipFile, ZipFile


CATALOG_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = CATALOG_ROOT.parent
DEFAULT_CATALOG = CATALOG_ROOT / "catalog.json"
DEFAULT_REPORT = CATALOG_ROOT / "import-report.json"
DEFAULT_MANIFEST = REPOSITORY_ROOT / "data" / "openscore-lieder" / "manifest.json"
DEFAULT_WEB_CATALOG = (
    REPOSITORY_ROOT / "apps" / "web" / "src" / "lib" / "catalog.generated.ts"
)

COLLECTION_ID = "openscore-lieder-cc0"
CATALOG_REVISION = "7"
PINNED_COMMIT = "6b2dc542ce2e8aa4b78c8ee62103b210efc07015"
PINNED_ARCHIVE_SHA256 = (
    "e925dd89f9dc2ac16f2aff49470d2c1f2dec9977bb4059172cbcbc7a4b98958c"
)
PINNED_SOURCE_URL = (
    "https://github.com/OpenScore/Lieder/archive/"
    f"{PINNED_COMMIT}.zip"
)
EXPECTED_METADATA_RECORDS = 1356
EXPECTED_MXL_FILES = 1462
RIGHTS_DECLARATION = "Creative Commons Zero (CC0) 1.0 Universal"
RIGHTS_STATUS = "technical_candidate_not_production_approved"

MAJOR_NAMES = {
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
MINOR_NAMES = {
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
MAJOR_ABC = {
    -7: "Cb",
    -6: "Gb",
    -5: "Db",
    -4: "Ab",
    -3: "Eb",
    -2: "Bb",
    -1: "F",
    0: "C",
    1: "G",
    2: "D",
    3: "A",
    4: "E",
    5: "B",
    6: "F#",
    7: "C#",
}
MINOR_ABC = {
    -7: "Abm",
    -6: "Ebm",
    -5: "Bbm",
    -4: "Fm",
    -3: "Cm",
    -2: "Gm",
    -1: "Dm",
    0: "Am",
    1: "Em",
    2: "Bm",
    3: "F#m",
    4: "C#m",
    5: "G#m",
    6: "D#m",
    7: "A#m",
}
MAJOR_TONIC_PC = {
    -7: 11,
    -6: 6,
    -5: 1,
    -4: 8,
    -3: 3,
    -2: 10,
    -1: 5,
    0: 0,
    1: 7,
    2: 2,
    3: 9,
    4: 4,
    5: 11,
    6: 6,
    7: 1,
}
MAJOR_PROFILE = (6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88)
MINOR_PROFILE = (6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17)
STEP_PC = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}


class LiederImportError(ValueError):
    """Raised when the pinned corpus no longer matches the ingest contract."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _children(element: ET.Element, name: str) -> list[ET.Element]:
    return [child for child in element if _local_name(child.tag) == name]


def _descendant_text(element: ET.Element, name: str) -> str:
    for child in element.iter():
        if _local_name(child.tag) == name:
            return (child.text or "").strip()
    return ""


def _read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as source:
        return list(csv.DictReader(source, delimiter="\t"))


def _score_xml(mxl_path: Path) -> bytes:
    try:
        with ZipFile(mxl_path) as archive:
            names = set(archive.namelist())
            root_name = "score.xml"
            if root_name not in names:
                try:
                    container = ET.fromstring(archive.read("META-INF/container.xml"))
                except (KeyError, ET.ParseError) as exc:
                    raise LiederImportError("MXL container is missing its score root") from exc
                root_name = next(
                    (
                        element.get("full-path", "")
                        for element in container.iter()
                        if _local_name(element.tag) == "rootfile"
                        and element.get("full-path")
                    ),
                    "",
                )
            if not root_name or root_name not in names:
                raise LiederImportError("MXL container names an absent score root")
            return archive.read(root_name)
    except (BadZipFile, KeyError) as exc:
        raise LiederImportError("invalid compressed MusicXML archive") from exc


def _creator(root: ET.Element, creator_type: str) -> str:
    for element in root.iter():
        if (
            _local_name(element.tag) == "creator"
            and element.get("type") == creator_type
            and (element.text or "").strip()
        ):
            return (element.text or "").strip()
    return ""


def _part_names(root: ET.Element) -> list[str]:
    names: list[str] = []
    for element in root.iter():
        if _local_name(element.tag) != "score-part":
            continue
        name = _descendant_text(element, "part-name")
        if name:
            normalized = " ".join(name.split())
            if normalized not in names:
                names.append(normalized)
    return names


def _pitch_weights(root: ET.Element) -> list[float]:
    weights = [0.0] * 12
    for note in root.iter():
        if _local_name(note.tag) != "note":
            continue
        pitch = next(
            (child for child in note if _local_name(child.tag) == "pitch"),
            None,
        )
        if pitch is None:
            continue
        step = _descendant_text(pitch, "step")
        if step not in STEP_PC:
            continue
        alter_text = _descendant_text(pitch, "alter")
        try:
            alter = int(float(alter_text)) if alter_text else 0
        except ValueError:
            alter = 0
        duration_text = _descendant_text(note, "duration")
        try:
            duration = max(float(duration_text), 0.25) if duration_text else 1.0
        except ValueError:
            duration = 1.0
        weights[(STEP_PC[step] + alter) % 12] += min(duration, 64.0)
    return weights


def _correlation(weights: list[float], profile: tuple[float, ...], tonic: int) -> float:
    if not any(weights):
        return float("-inf")
    expected = [profile[(pitch_class - tonic) % 12] for pitch_class in range(12)]
    mean_weights = sum(weights) / 12
    mean_expected = sum(expected) / 12
    numerator = sum(
        (actual - mean_weights) * (candidate - mean_expected)
        for actual, candidate in zip(weights, expected, strict=True)
    )
    denominator = math.sqrt(
        sum((actual - mean_weights) ** 2 for actual in weights)
        * sum((candidate - mean_expected) ** 2 for candidate in expected)
    )
    return numerator / denominator if denominator else float("-inf")


def _mode(root: ET.Element, fifths: int) -> tuple[str, dict[str, float | str]]:
    first_key = next(
        (element for element in root.iter() if _local_name(element.tag) == "key"),
        None,
    )
    declared = _descendant_text(first_key, "mode").lower() if first_key is not None else ""
    if declared in {"major", "minor"}:
        return declared, {"method": "musicxml", "major_correlation": 0.0, "minor_correlation": 0.0}

    weights = _pitch_weights(root)
    major_tonic = MAJOR_TONIC_PC[fifths]
    minor_tonic = (major_tonic + 9) % 12
    major_score = _correlation(weights, MAJOR_PROFILE, major_tonic)
    minor_score = _correlation(weights, MINOR_PROFILE, minor_tonic)
    inferred = "minor" if minor_score > major_score else "major"
    return inferred, {
        "method": "relative-key-profile-v1",
        "major_correlation": round(major_score, 6),
        "minor_correlation": round(minor_score, 6),
    }


def _score_facts(xml_data: bytes) -> dict[str, Any]:
    try:
        root = ET.fromstring(xml_data)
    except ET.ParseError as exc:
        raise LiederImportError(f"invalid MusicXML: {exc}") from exc
    if _local_name(root.tag) != "score-partwise":
        raise LiederImportError(f"unsupported MusicXML root {_local_name(root.tag)!r}")
    first_key = next(
        (element for element in root.iter() if _local_name(element.tag) == "key"),
        None,
    )
    if first_key is None:
        raise LiederImportError("score has no key signature")
    fifths_text = _descendant_text(first_key, "fifths")
    try:
        fifths = int(fifths_text)
    except ValueError as exc:
        raise LiederImportError(f"invalid key fifths {fifths_text!r}") from exc
    if fifths not in MAJOR_NAMES:
        raise LiederImportError(f"unsupported key signature with {fifths} fifths")

    mode, mode_analysis = _mode(root, fifths)
    pitched_notes = sum(
        1
        for note in root.iter()
        if _local_name(note.tag) == "note"
        and any(_local_name(child.tag) == "pitch" for child in note)
    )
    if pitched_notes == 0:
        raise LiederImportError("score has no pitched notes")
    verse_ids = {
        element.get("number") or "1"
        for element in root.iter()
        if _local_name(element.tag) == "lyric"
    }
    lyricist = _creator(root, "lyricist")
    composer = _creator(root, "composer")
    software = [
        (element.text or "").strip()
        for element in root.iter()
        if _local_name(element.tag) == "software" and (element.text or "").strip()
    ]
    part_names = _part_names(root)
    return {
        "composer": composer,
        "ensemble": " + ".join(part_names) if part_names else "Full score",
        "fifths": fifths,
        "lyricist": lyricist,
        "mode": mode,
        "mode_analysis": mode_analysis,
        "part_count": sum(1 for child in root if _local_name(child.tag) == "part"),
        "pitched_notes": pitched_notes,
        "software": software,
        "verse_ids": sorted(verse_ids, key=lambda value: (not value.isdigit(), value)),
        "work_title": _descendant_text(root, "work-title"),
        "movement_title": _descendant_text(root, "movement-title"),
    }


def _original_key(fifths: int, mode: str) -> dict[str, Any]:
    names = MINOR_NAMES if mode == "minor" else MAJOR_NAMES
    abc_names = MINOR_ABC if mode == "minor" else MAJOR_ABC
    return {
        "abc": abc_names[fifths],
        "fifths": fifths,
        "mode": mode,
        "name": f"{names[fifths]} {mode}",
    }


def _display_collection(set_name: str) -> str:
    return "" if set_name.startswith("Other songs by ") else set_name


def _normalize_path(path: Path) -> Path:
    """Match macOS filesystem normalization without changing source identity."""
    return Path(*[unicodedata.normalize("NFD", part) for part in path.parts])


def _source_file(
    source_root: Path,
    source_path: str,
    score_id: str,
    *,
    files_by_id: dict[str, Path],
) -> Path:
    relative = Path("scores") / source_path / f"lc{score_id}.mxl"
    direct = source_root / relative
    if direct.is_file():
        return direct
    normalized = source_root / _normalize_path(relative)
    if normalized.is_file():
        return normalized
    indexed = files_by_id.get(score_id)
    if indexed is not None:
        return indexed
    raise LiederImportError(f"missing indexed MXL artifact {relative.as_posix()!r}")


def _base_report_numbers(report: dict[str, Any]) -> tuple[int, int, int]:
    summary = report["summary"]
    prior = report.get("source_breakdown", {}).get("openscore_lieder", {})
    return (
        int(summary["exact_public_domain_candidates"])
        - int(prior.get("exact_public_domain_candidates", 0)),
        int(summary["source_records"]) - int(prior.get("source_records", 0)),
        int(summary["structure_holds"])
        - int(prior.get("structure_holds", 0)),
    )


def import_lieder(
    *,
    source_root: Path,
    catalog_path: Path = DEFAULT_CATALOG,
    report_path: Path = DEFAULT_REPORT,
    manifest_path: Path = DEFAULT_MANIFEST,
    web_catalog_path: Path = DEFAULT_WEB_CATALOG,
) -> dict[str, Any]:
    source_root = source_root.resolve()
    required = [
        source_root / "LICENSE.txt",
        source_root / "data" / "scores.tsv",
        source_root / "data" / "sets.tsv",
        source_root / "data" / "composers.tsv",
    ]
    if any(not path.is_file() for path in required):
        raise LiederImportError("source root is not the pinned OpenScore Lieder tree")
    if PINNED_COMMIT not in source_root.name:
        raise LiederImportError(
            f"source directory must identify pinned commit {PINNED_COMMIT}"
        )

    scores = _read_tsv(source_root / "data" / "scores.tsv")
    sets = {row["id"]: row for row in _read_tsv(source_root / "data" / "sets.tsv")}
    composers = {
        row["id"]: row for row in _read_tsv(source_root / "data" / "composers.tsv")
    }
    if len(scores) != EXPECTED_METADATA_RECORDS:
        raise LiederImportError(
            f"expected {EXPECTED_METADATA_RECORDS} metadata rows, found {len(scores)}"
        )
    mxl_files = list((source_root / "scores").rglob("*.mxl"))
    mxl_count = len(mxl_files)
    if mxl_count != EXPECTED_MXL_FILES:
        raise LiederImportError(
            f"expected {EXPECTED_MXL_FILES} MXL files, found {mxl_count}"
        )
    files_by_id: dict[str, Path] = {}
    for path in mxl_files:
        score_id = path.stem.removeprefix("lc")
        if score_id in files_by_id:
            raise LiederImportError(f"duplicate MXL score ID {score_id}")
        files_by_id[score_id] = path

    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    report = json.loads(report_path.read_text(encoding="utf-8"))
    if str(catalog.get("catalog_revision")) not in {"6", CATALOG_REVISION}:
        raise LiederImportError("base catalog must be revision 6 or idempotent revision 7")
    old_lieder_items = [
        item
        for item in catalog["items"]
        if item["source"]["collection_id"] == COLLECTION_ID
    ]
    base_items = [
        item
        for item in catalog["items"]
        if item["source"]["collection_id"] != COLLECTION_ID
    ]
    for item in base_items:
        item.setdefault("content_type", "hymn")

    holds: list[dict[str, Any]] = []
    records: list[dict[str, Any]] = []
    items: list[dict[str, Any]] = []
    destination_root = catalog_path.parent / "scores"
    destination_root.mkdir(parents=True, exist_ok=True)

    for ordinal, row in enumerate(scores, start=1):
        score_id = row["id"]
        try:
            source_file = _source_file(
                source_root,
                row["path"],
                score_id,
                files_by_id=files_by_id,
            )
            source_entry = source_file.relative_to(source_root).as_posix()
            artifact_sha256 = _sha256(source_file)
            facts = _score_facts(_score_xml(source_file))
            set_record = sets[row["set_id"]]
            composer_record = composers[set_record["composer_id"]]
        except (KeyError, LiederImportError, OSError) as exc:
            holds.append(
                {
                    "collection_id": COLLECTION_ID,
                    "reason": str(exc),
                    "record_ordinal": ordinal,
                    "record_reference": score_id,
                    "title": row.get("name", ""),
                }
            )
            continue

        composer = composer_record["name"].strip() or facts["composer"] or "Unknown"
        lyricist = facts["lyricist"] or "Unknown"
        collection = _display_collection(set_record["name"].strip())
        item_id = f"lieder-{score_id}"
        destination = destination_root / f"{item_id}.mxl"
        shutil.copyfile(source_file, destination)
        if _sha256(destination) != artifact_sha256:
            raise LiederImportError(f"copied score hash drifted for {score_id}")
        original_key = _original_key(facts["fifths"], facts["mode"])
        verse_ids = facts["verse_ids"]
        work_id = item_id
        record = {
            "artifact_sha256": artifact_sha256,
            "composer": composer,
            "entry_path": source_entry,
            "ensemble": facts["ensemble"],
            "id": score_id,
            "key": original_key,
            "lyricist": lyricist,
            "mode_analysis": facts["mode_analysis"],
            "record_ordinal": ordinal,
            "record_url": row["link"],
            "set": collection,
            "software": facts["software"],
            "title": row["name"],
        }
        records.append(record)
        items.append(
            {
                "available_lines": ["SCORE"],
                "content_type": "art_song",
                "display": {
                    "collection": collection or "Standalone song",
                    "composer": composer,
                    "ensemble": facts["ensemble"],
                    "lyricist": lyricist,
                    "meter": "Art song",
                    "text_author": lyricist,
                    "tune_name": composer,
                },
                "id": item_id,
                "lyrics": {
                    "available": bool(verse_ids),
                    "scope": "vocal_parts" if verse_ids else "none",
                    "verse_ids": verse_ids,
                },
                "original_key": original_key,
                "rights": {
                    "source_attribution": [
                        f"Music: {composer}.",
                        f"Text: {lyricist}.",
                        "OpenScore Lieder transcription and MusicXML export.",
                    ],
                    "source_declaration": RIGHTS_DECLARATION,
                    "source_music_reference": row["link"],
                    "status": RIGHTS_STATUS,
                },
                "score": {
                    "canonical_state": "untransposed",
                    "generator": {
                        "name": "openscore-lieder-mxl",
                        "version": "1",
                    },
                    "media_type": "application/vnd.recordare.musicxml",
                    "path": f"scores/{item_id}.mxl",
                    "sha256": artifact_sha256,
                },
                "source": {
                    "arrangement_id": item_id,
                    "artifact_sha256": artifact_sha256,
                    "collection_id": COLLECTION_ID,
                    "entry_path": source_entry,
                    "record_ordinal": ordinal,
                    "record_reference": score_id,
                    "record_url": row["link"],
                    "work_id": work_id,
                },
                "title": row["name"],
            }
        )

    manifest = {
        "archive_sha256": PINNED_ARCHIVE_SHA256,
        "collection_id": COLLECTION_ID,
        "license": RIGHTS_DECLARATION,
        "metadata_files": {
            path.name: _sha256(path)
            for path in required[1:]
        },
        "pinned_commit": PINNED_COMMIT,
        "records": records,
        "schema_version": 1,
        "source_url": PINNED_SOURCE_URL,
        "summary": {
            "indexed_records": len(scores),
            "promoted_records": len(items),
            "structure_holds": len(holds),
            "unindexed_mxl_files": mxl_count - len(scores),
        },
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_bytes = (
        json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    ).encode("utf-8")
    manifest_path.write_bytes(manifest_bytes)
    manifest_sha256 = _sha256_bytes(manifest_bytes)

    all_items = base_items + items
    catalog["catalog_id"] = "transposify-technical-preview"
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
            "source_url": PINNED_SOURCE_URL,
        }
    ]
    catalog_path.write_text(
        json.dumps(catalog, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )

    expected_paths = {item["score"]["path"] for item in items}
    for old_item in old_lieder_items:
        old_path = old_item["score"]["path"]
        if old_path not in expected_paths:
            stale = catalog_path.parent / old_path
            if stale.is_file() and stale.parent == destination_root.resolve():
                stale.unlink()

    base_exact_pd, base_source_records, base_structure_holds = _base_report_numbers(report)
    existing_holds = [
        hold
        for hold in report["excluded"]["structure_holds"]
        if hold.get("collection_id") != COLLECTION_ID
    ]
    report["catalog_revision"] = CATALOG_REVISION
    report["conversion"]["openscore_lieder"] = {
        "canonical_format": "compressed MusicXML",
        "generator": {"name": "openscore-lieder-mxl", "version": "1"},
        "mode_inference": "relative-key-profile-v1",
        "pinned_commit": PINNED_COMMIT,
    }
    report["excluded"]["structure_holds"] = existing_holds + holds
    report["source_breakdown"]["openscore_lieder"] = {
        "catalog_items": len(items),
        "exact_public_domain_candidates": len(scores),
        "indexed_records": len(scores),
        "source_records": len(scores),
        "structure_holds": len(holds),
        "unindexed_mxl_files": mxl_count - len(scores),
    }
    report["summary"].update(
        {
            "catalog_items": len(all_items),
            "exact_public_domain_candidates": base_exact_pd + len(scores),
            "openscore_lieder_items": len(items),
            "source_records": base_source_records + len(scores),
            "structure_holds": base_structure_holds + len(holds),
        }
    )
    report_path.write_text(
        json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )

    sys.path.insert(0, str(CATALOG_ROOT / "scripts"))
    from build_open_hymnal_catalog import _write_web_catalog

    _write_web_catalog(
        all_items,
        web_catalog_path,
        catalog_revision=int(CATALOG_REVISION),
    )
    return report["source_breakdown"]["openscore_lieder"]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--source-root",
        required=True,
        type=Path,
        help="Extracted OpenScore Lieder tree at the pinned commit.",
    )
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--web-catalog", type=Path, default=DEFAULT_WEB_CATALOG)
    args = parser.parse_args()
    try:
        summary = import_lieder(
            source_root=args.source_root,
            catalog_path=args.catalog,
            report_path=args.report,
            manifest_path=args.manifest,
            web_catalog_path=args.web_catalog,
        )
    except (LiederImportError, OSError, json.JSONDecodeError) as exc:
        print(f"OpenScore Lieder import failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

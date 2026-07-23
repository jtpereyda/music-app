#!/usr/bin/env python3
"""Prepare the eight compatible split-ZIP additions for catalog promotion.

The Open Hymnal combined ABC and split ZIP disagree. This script deliberately
extracts only the eight exact-public-domain ZIP entries that are absent from
the combined file and already match the product's two-part/four-voice SATB
shape. It writes an inventory, converted MusicXML, and a conversion report for
the catalog builder without modifying the pinned source archive.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from zipfile import BadZipFile, ZipFile


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
INGEST_ROOT = REPOSITORY_ROOT / "spikes" / "ingest"
sys.path.insert(0, str(INGEST_ROOT))

from hymn_ingest.abc_inventory import (  # noqa: E402
    ABCInventoryError,
    build_inventory,
    write_json,
)
from hymn_ingest.conversion import (  # noqa: E402
    ConversionConfigurationError,
    convert_inventory,
)


DEFAULT_ARCHIVE = (
    REPOSITORY_ROOT / "data" / "open-hymnal" / "raw" / "OpenHymnal2014.06-abc.zip"
)
EXPECTED_ARCHIVE_SHA256 = (
    "407ec5ab7ec6b27f698245c3b4b2c7bea1488fabbb56f7ff190849e11fe472cd"
)
EXPECTED_ARCHIVE_ABC_FILES = 306
EXPECTED_CONVERTER_SHA256 = (
    "76cd2c5c4fc44b28ab2ce923f196d23d09b93fcefa8cfa90a10754d38e15b56e"
)
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


class SupplementPreparationError(ValueError):
    """Raised when a pinned supplement input or result drifts."""


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def prepare_supplement(
    *,
    archive_path: Path,
    converter_path: Path,
    output_root: Path,
    converter_python: Path | None = None,
) -> dict[str, object]:
    if _sha256_file(archive_path) != EXPECTED_ARCHIVE_SHA256:
        raise SupplementPreparationError(
            "Open Hymnal split ZIP does not match the pinned archive hash."
        )
    if _sha256_file(converter_path) != EXPECTED_CONVERTER_SHA256:
        raise SupplementPreparationError(
            "abc2xml converter does not match the pinned release-268 script hash."
        )

    source_root = output_root / "source"
    split_root = output_root / "abc"
    inventory_root = output_root / "entry-inventories"
    source_root.mkdir(parents=True, exist_ok=True)

    try:
        with ZipFile(archive_path) as archive:
            abc_infos = [
                info
                for info in archive.infolist()
                if not info.is_dir() and info.filename.lower().endswith(".abc")
            ]
            if len(abc_infos) != EXPECTED_ARCHIVE_ABC_FILES:
                raise SupplementPreparationError(
                    f"Expected {EXPECTED_ARCHIVE_ABC_FILES} ABC entries, "
                    f"found {len(abc_infos)}."
                )
            archive_ordinals = {
                info.filename: ordinal
                for ordinal, info in enumerate(abc_infos, start=1)
            }
            missing = set(SUPPLEMENT_ENTRIES) - archive_ordinals.keys()
            if missing:
                raise SupplementPreparationError(
                    f"Pinned supplement entries are missing: {sorted(missing)}"
                )

            tunes: list[dict[str, object]] = []
            for selection_ordinal, entry_path in enumerate(SUPPLEMENT_ENTRIES, start=1):
                entry_bytes = archive.read(entry_path)
                source_path = source_root / entry_path
                source_path.parent.mkdir(parents=True, exist_ok=True)
                source_path.write_bytes(entry_bytes)

                entry_split_root = split_root / f"{selection_ordinal:02d}"
                entry_report_path = (
                    inventory_root / f"{selection_ordinal:02d}-inventory.json"
                )
                entry_inventory = build_inventory(
                    input_path=source_path,
                    split_dir=entry_split_root,
                    report_path=entry_report_path,
                    source_encoding="windows-1252",
                    expected_raw_bytes=len(entry_bytes),
                    expected_raw_sha256=_sha256_bytes(entry_bytes),
                    expected_tune_count=1,
                )
                tune = dict(entry_inventory["tunes"][0])
                tune["file"] = (
                    f"{selection_ordinal:02d}/{Path(str(tune['file'])).name}"
                )
                tune["ordinal"] = selection_ordinal
                tune["source_archive_ordinal"] = archive_ordinals[entry_path]
                tune["source_entry"] = entry_path
                tune["source_entry_raw_sha256"] = _sha256_bytes(entry_bytes)
                tunes.append(tune)
    except BadZipFile as exc:
        raise SupplementPreparationError(f"Invalid Open Hymnal split ZIP: {exc}") from exc

    inventory_path = output_root / "inventory.json"
    inventory = {
        "generator": {
            "name": "prepare_open_hymnal_supplement",
            "version": "1",
        },
        "schema_version": 2,
        "source": {
            "encoding": "windows-1252",
            "path": str(archive_path),
            "raw": {
                "bytes": archive_path.stat().st_size,
                "sha256": EXPECTED_ARCHIVE_SHA256,
            },
        },
        "split_directory": "abc",
        "summary": {
            "archive_abc_files": EXPECTED_ARCHIVE_ABC_FILES,
            "tune_count": len(tunes),
        },
        "tunes": tunes,
    }
    write_json(inventory_path, inventory)

    conversion = convert_inventory(
        inventory_path=inventory_path,
        converter_path=converter_path,
        converter_version="268",
        converter_python=converter_python,
        output_dir=output_root / "musicxml",
        report_path=output_root / "conversion.json",
    )
    summary = conversion["summary"]
    if summary["succeeded"] != len(SUPPLEMENT_ENTRIES):
        raise SupplementPreparationError(
            f"Converted {summary['succeeded']}/{len(SUPPLEMENT_ENTRIES)} supplement entries."
        )
    return conversion


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, default=DEFAULT_ARCHIVE)
    parser.add_argument("--converter", type=Path, required=True)
    parser.add_argument("--converter-python", type=Path, default=Path(sys.executable))
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    try:
        report = prepare_supplement(
            archive_path=args.archive.resolve(),
            converter_path=args.converter.resolve(),
            converter_python=args.converter_python.resolve(),
            output_root=args.output_root.resolve(),
        )
    except (
        ABCInventoryError,
        BadZipFile,
        ConversionConfigurationError,
        SupplementPreparationError,
        json.JSONDecodeError,
        OSError,
    ) as exc:
        print(f"supplement preparation failed: {exc}", file=sys.stderr)
        return 2

    summary = report["summary"]
    print(
        f"Prepared {summary['succeeded']} Open Hymnal supplement scores; "
        f"{summary['clean']} clean and "
        f"{summary['cleanup_required']} requiring catalog cleanup review."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

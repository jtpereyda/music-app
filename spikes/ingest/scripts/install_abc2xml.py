#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import zipfile


SCRIPT_ROOT = Path(__file__).resolve().parents[1]
LOCK_PATH = SCRIPT_ROOT / "converter.lock.json"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract the pinned abc2xml.py release into a local tools directory."
    )
    parser.add_argument("--archive", required=True, type=Path)
    parser.add_argument("--destination", required=True, type=Path)
    parser.add_argument(
        "--expected-sha256",
        help="Optional reviewed archive digest; overrides archive_sha256 in the lock file.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    lock = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
    archive_bytes = args.archive.read_bytes()
    archive_sha256 = sha256(archive_bytes)
    expected = args.expected_sha256 or lock.get("archive_sha256")
    if expected and archive_sha256.lower() != str(expected).lower():
        print(
            f"archive checksum mismatch: expected {expected}, got {archive_sha256}",
            file=sys.stderr,
        )
        return 2

    with zipfile.ZipFile(args.archive) as archive:
        candidates = [
            name
            for name in archive.namelist()
            if Path(name).name == lock["entrypoint"] and not name.endswith("/")
        ]
        if len(candidates) != 1:
            print(
                f"expected exactly one {lock['entrypoint']} in archive; found {candidates}",
                file=sys.stderr,
            )
            return 2
        script_bytes = archive.read(candidates[0])
    expected_script = lock.get("entrypoint_sha256")
    script_sha256 = sha256(script_bytes)
    if expected_script and script_sha256.lower() != str(expected_script).lower():
        print(
            f"converter checksum mismatch: expected {expected_script}, got {script_sha256}",
            file=sys.stderr,
        )
        return 2

    args.destination.mkdir(parents=True, exist_ok=True)
    script_path = args.destination / lock["entrypoint"]
    script_path.write_bytes(script_bytes)
    metadata = {
        "archive_filename": args.archive.name,
        "archive_sha256": archive_sha256,
        "converter": lock["name"],
        "download_url": lock["download_url"],
        "entrypoint": lock["entrypoint"],
        "entrypoint_sha256": script_sha256,
        "version": lock["version"],
    }
    metadata_path = args.destination / "INSTALL-METADATA.json"
    metadata_path.write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"Installed {lock['name']} {lock['version']} at {script_path}")
    print(f"Archive SHA-256: {archive_sha256}")
    print(f"Script SHA-256:  {metadata['entrypoint_sha256']}")
    if not expected:
        print(
            "WARNING: upstream archive had no locked checksum; review and retain the digests above.",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

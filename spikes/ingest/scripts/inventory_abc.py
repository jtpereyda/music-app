#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


SCRIPT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_ROOT))

from hymn_ingest.abc_inventory import ABCInventoryError, build_inventory  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Inventory and split a multi-tune Open Hymnal ABC file."
    )
    parser.add_argument("--input", required=True, type=Path, help="Multi-tune UTF-8 ABC file.")
    parser.add_argument(
        "--split-dir", required=True, type=Path, help="Directory for per-tune ABC files."
    )
    parser.add_argument("--report", required=True, type=Path, help="Inventory JSON report.")
    parser.add_argument(
        "--source-encoding",
        help="Declared source character encoding (default: UTF-8, or the source lock value).",
    )
    parser.add_argument(
        "--source-lock",
        type=Path,
        help="Optional JSON lock containing expected source hashes, size, encoding, and tune count.",
    )
    parser.add_argument(
        "--fail-on-warning",
        action="store_true",
        help="Exit nonzero when the inventory contains warnings.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        source_lock = (
            json.loads(args.source_lock.read_text(encoding="utf-8"))
            if args.source_lock
            else {}
        )
        locked_encoding = source_lock.get("encoding")
        if args.source_encoding and locked_encoding and args.source_encoding != locked_encoding:
            raise ABCInventoryError(
                f"--source-encoding {args.source_encoding!r} conflicts with "
                f"source lock encoding {locked_encoding!r}."
            )
        source_encoding = args.source_encoding or locked_encoding or "utf-8"
        raw_lock = source_lock.get("raw", {})
        normalized_lock = source_lock.get("normalized_utf8", {})
        report = build_inventory(
            input_path=args.input.resolve(),
            split_dir=args.split_dir.resolve(),
            report_path=args.report.resolve(),
            source_encoding=source_encoding,
            expected_raw_bytes=raw_lock.get("bytes"),
            expected_raw_sha256=raw_lock.get("sha256"),
            expected_normalized_utf8_bytes=normalized_lock.get("bytes"),
            expected_normalized_utf8_sha256=normalized_lock.get("sha256"),
            expected_tune_count=source_lock.get("expected_tune_count"),
        )
    except (ABCInventoryError, json.JSONDecodeError, OSError) as exc:
        print(f"inventory failed: {exc}", file=sys.stderr)
        return 2

    summary = report["summary"]
    print(
        f"Inventoried {summary['tune_count']} tune(s); "
        f"{summary['warning_count']} warning(s)."
    )
    if args.fail_on_warning and summary["warning_count"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

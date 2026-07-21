#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import sys


SCRIPT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_ROOT))

from hymn_ingest.conversion import (  # noqa: E402
    ConversionConfigurationError,
    convert_inventory,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert every tune in an inventory report to validated MusicXML."
    )
    parser.add_argument("--inventory", required=True, type=Path)
    parser.add_argument("--converter", required=True, type=Path)
    parser.add_argument("--converter-version", default="268")
    parser.add_argument("--converter-python", type=Path, default=Path(sys.executable))
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--timeout-seconds", type=float, default=60.0)
    parser.add_argument(
        "--fail-on-error",
        action="store_true",
        help="Exit nonzero when any tune is failed or invalid.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        report = convert_inventory(
            inventory_path=args.inventory.resolve(),
            converter_path=args.converter.resolve(),
            converter_version=args.converter_version,
            output_dir=args.output_dir.resolve(),
            report_path=args.report.resolve(),
            converter_python=args.converter_python.resolve(),
            timeout_seconds=args.timeout_seconds,
        )
    except (ConversionConfigurationError, OSError, ValueError) as exc:
        print(f"conversion failed: {exc}", file=sys.stderr)
        return 2

    summary = report["summary"]
    print(
        f"Converted {summary['succeeded']}/{summary['total']} tune(s); "
        f"{summary['clean']} clean, {summary['invalid']} invalid, "
        f"{summary['failed']} failed."
    )
    if args.fail_on_error and (summary["invalid"] or summary["failed"]):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


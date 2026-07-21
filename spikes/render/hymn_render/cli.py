from __future__ import annotations

import argparse
import json
from pathlib import Path

from hymn_render.core import (
    CLEF_FACTORIES,
    LINE_NAMES,
    OCTAVE_PLACEMENTS,
    PAGE_SIZES,
    run_pipeline,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Select/transpose/re-clef MusicXML and render SVG/PDF."
    )
    parser.add_argument("input", type=Path, help="Source MusicXML path")
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--line", choices=LINE_NAMES, default="satb")
    parser.add_argument(
        "--target-key",
        help="Target tonic (such as D or B-) or explicit key (such as D minor)",
    )
    parser.add_argument(
        "--clef",
        choices=("original", *CLEF_FACTORIES.keys()),
        default="original",
    )
    parser.add_argument(
        "--octave",
        choices=OCTAVE_PLACEMENTS,
        default="original",
        help="Preserve, automatically place, or shift an individual line by one octave",
    )
    parser.add_argument("--page-size", choices=PAGE_SIZES.keys(), default="letter")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest = run_pipeline(
        args.input,
        args.output_dir,
        line_name=args.line,
        target_key_name=args.target_key,
        clef_name=args.clef,
        octave_placement=args.octave,
        page_size=args.page_size,
    )
    print(json.dumps(manifest["transform"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

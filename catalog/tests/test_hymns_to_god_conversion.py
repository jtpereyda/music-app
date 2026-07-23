from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import unittest


CATALOG_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = CATALOG_ROOT.parent
SCRIPT_ROOT = CATALOG_ROOT / "scripts"
sys.path.insert(0, str(SCRIPT_ROOT))

from convert_hymns_to_god_mup import (  # noqa: E402
    MupConversionError,
    parse_expanded_mup,
    score_to_music21,
)


SYNTHETIC_SOURCE = r'''
score
    time=4/4
    key=1&

title bold (19) "" "Synthetic Hymn" ""

music

1: 2s; 4ce; df;
2: 2s; 4c-g; d-a;
lyrics between 1&2: 2s; 4; 4; "Pick up";
bar

1 1: 4ce; df; eg; fa;
1 2: 4s; e; s; f;
2: 4c-g; d-a; e-b; f-c+;
lyrics between 1&2: "One two three four";
endbar
'''


class HymnsToGodConversionTests(unittest.TestCase):
    def test_parser_preserves_spaces_overlays_and_lyrics(self) -> None:
        parsed = parse_expanded_mup(SYNTHETIC_SOURCE)
        self.assertEqual(parsed.title, "Synthetic Hymn")
        self.assertEqual(parsed.time_signature, "4/4")
        self.assertEqual(parsed.fifths, -1)
        self.assertEqual(len(parsed.measures), 2)
        self.assertEqual(parsed.measures[0].assignments[(1, 1)][0].kind, "space")
        self.assertEqual(
            parsed.measures[0].assignments[(1, 1)][0].duration,
            2,
        )

        score = score_to_music21(parsed)
        self.assertEqual(len(score.parts), 2)
        self.assertEqual(len(score.voicesToParts().parts), 4)
        first_soprano = list(score.parts[0].measure(1).voices[0].notes)
        self.assertEqual([value.offset for value in first_soprano], [2.0, 3.0])
        self.assertEqual(
            [lyric.text for value in first_soprano for lyric in value.lyrics],
            ["Pick", "up"],
        )

        second_alto = list(score.parts[0].measure(2).voices[1].notes)
        self.assertEqual(
            [value.pitch.nameWithOctave for value in second_alto],
            ["C4", "E4", "E4", "F4"],
        )

    def test_non_satb_secondary_chord_fails_closed(self) -> None:
        source = SYNTHETIC_SOURCE.replace(
            "1 2: 4s; e; s; f;",
            "1 2: 4s; eg; s; f;",
        )
        parsed = parse_expanded_mup(source)
        with self.assertRaisesRegex(
            MupConversionError,
            "Secondary staff 1 voice is not monophonic",
        ):
            score_to_music21(parsed)

    def test_manifest_hashes_and_dispositions_are_pinned(self) -> None:
        manifest_path = (
            REPOSITORY_ROOT / "data/hymns-to-god/manifest.json"
        )
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        raw_root = manifest_path.parent / "raw"
        counts: dict[str, int] = {}
        for record in manifest["records"]:
            disposition = record["disposition"]
            counts[disposition] = counts.get(disposition, 0) + 1
            page_path = raw_root / record["page_file"]
            self.assertEqual(
                hashlib.sha256(page_path.read_bytes()).hexdigest(),
                record["page_sha256"],
            )
            if disposition == "rights_hold":
                continue
            source_path = raw_root / "mup" / record["source_file"]
            self.assertEqual(
                hashlib.sha256(source_path.read_bytes()).hexdigest(),
                record["source_sha256"],
            )
        self.assertEqual(
            counts,
            {"eligible": 13, "rights_hold": 1, "structure_hold": 3},
        )

    def test_catalog_contains_only_eligible_hymns_to_god_records(self) -> None:
        catalog = json.loads(
            (CATALOG_ROOT / "catalog.json").read_text(encoding="utf-8")
        )
        items = [
            item
            for item in catalog["items"]
            if item["source"]["collection_id"]
            == "hymns-to-god-public-domain-usa"
        ]
        self.assertEqual(len(items), 13)
        self.assertTrue(
            all(
                item["score"]["generator"]
                == {"name": "hymns-to-god-mup-satb", "version": "1"}
                for item in items
            )
        )


if __name__ == "__main__":
    unittest.main()

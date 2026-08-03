from __future__ import annotations

import hashlib
import json
from fractions import Fraction
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch


CATALOG_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = CATALOG_ROOT.parent
SCRIPT_ROOT = CATALOG_ROOT / "scripts"
sys.path.insert(0, str(SCRIPT_ROOT))

from convert_hymns_to_god_mup import (  # noqa: E402
    MupConversionError,
    _lyric_tokens,
    _normalized_title_variants,
    convert_inventory,
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

TUPLET_SOURCE = r'''
score
    time=3/4
    key=c

title bold (19) "" "Tuplet Hymn" ""

music

1: 2s; {8ce; df; eg;} above 3;
2: 2s; {8cg; da; eb;} above 3;
lyrics between 1&2: 2s; {8; 8; 8;} above 3; "One two three";
endbar
'''

DYNAMIC_SOURCE = r'''
score
    time=3/4
    key=c

title bold (19) "" "Dynamic Hymn" ""

music

1: 4ce; df; eg;
2: 4cg; da; eb;
lyrics between 1&2: "One two three";
repeatstart

score time=4/4
music
1: [pad 5; with .]... 4c+bm; d+ ebm; e+; f+;
2: 4c; d; e; f;
lyrics between 1&2: 4; 4; 4; 4; [c] "Four five six <>";
repeatend
'''

BASS_ENTRANCE_SOURCE = r'''
score
    time=4/4
    key=c

title bold (19) "" "Bass Entrance" ""

music

1: 2.s; 4r;
2 1: 2.s; 4r;
2 2: 2.s; 8c; d;
lyrics between 1&2: 2.s; 8; 8; "We rise";
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

    def test_divisi_chords_are_preserved_in_semantic_parts(self) -> None:
        source = SYNTHETIC_SOURCE.replace(
            "1 2: 4s; e; s; f;",
            "1 2: 4s; eg; s; f;",
        ).replace("1: 2s; 4ce; df;", "1: 2s; 4cde; df;")
        parsed = parse_expanded_mup(source)
        score = score_to_music21(parsed)

        primary_divisi = list(score.parts[0].measure(1).voices[1].notes)[0]
        self.assertEqual(
            [value.nameWithOctave for value in primary_divisi.pitches],
            ["C4", "D4"],
        )
        secondary_divisi = list(score.parts[0].measure(2).voices[1].notes)[1]
        self.assertEqual(
            [value.nameWithOctave for value in secondary_divisi.pitches],
            ["E4", "G4"],
        )

    def test_silent_staff_and_engraving_only_lyric_markup_are_supported(self) -> None:
        source = r'''
score
    time=4/4
    key=c

title bold (19) " " "Solo Entrance" ""

music
1: 2s; 4c; d;
lyrics 1: 2s; 4; 4; "Solo line";
endbar
'''
        parsed = parse_expanded_mup(source)
        self.assertEqual(parsed.title, "Solo Entrance")
        score = score_to_music21(parsed)
        self.assertEqual(len(score.voicesToParts().parts), 4)
        self.assertFalse(list(score.parts[1].recurse().notes))
        self.assertEqual(
            [
                lyric.text
                for value in score.parts[0].recurse().notes
                for lyric in value.lyrics
            ],
            ["Solo", "line"],
        )
        self.assertEqual(
            [token.text for token in _lyric_tokens("comes_{3}")],
            ["comes"],
        )

    def test_directional_ties_and_repeated_space_markers_are_preserved(self) -> None:
        source = r'''
score
    time=4/4
    key=c

title bold (19) "" "Directional Ties" ""

music
1: 2s; 4d+~upfn~down; 4ss;
2: 2s; 4ce; 4s;
lyrics between 1&2: 2s; 4; 4s; "Tied";
endbar
'''
        parsed = parse_expanded_mup(source)
        tied_group = parsed.measures[0].assignments[(1, 1)][1]
        self.assertEqual(
            [value.step for value in tied_group.pitches],
            ["d", "f"],
        )
        self.assertTrue(all(value.tie_to_next for value in tied_group.pitches))
        self.assertEqual(
            parsed.measures[0].assignments[(1, 1)][2].kind,
            "space",
        )

    def test_implicit_lyrics_prefer_the_nearest_semantic_voice(self) -> None:
        source = r'''
score
    time=4/4
    key=c

title bold (19) "" "Nearest Lyric Voice" ""

music
1 1: 2s; 4c; 4s;
1 2: 2s; 4e; 4g;
2: 2s; 4ce; 4df;
lyrics between 1&2: 2s; 4; 4; "With His";
endbar
'''
        score = score_to_music21(parse_expanded_mup(source))
        soprano_lyrics = [
            lyric.text
            for value in score.parts[0].measure(1).voices[0].notes
            for lyric in value.lyrics
        ]
        alto_lyrics = [
            lyric.text
            for value in score.parts[0].measure(1).voices[1].notes
            for lyric in value.lyrics
        ]
        self.assertEqual(soprano_lyrics, ["With"])
        self.assertEqual(alto_lyrics, ["His"])

    def test_parser_preserves_tuplet_note_and_lyric_timing(self) -> None:
        parsed = parse_expanded_mup(TUPLET_SOURCE)
        groups = parsed.measures[0].assignments[(1, 1)]
        self.assertEqual(
            [group.duration for group in groups],
            [2, Fraction(1, 3), Fraction(1, 3), Fraction(1, 3)],
        )
        score = score_to_music21(parsed)
        tuplet_notes = list(score.parts[0].measure(1).voices[0].notes)
        self.assertEqual(
            [value.offset for value in tuplet_notes],
            [2.0, Fraction(7, 3), Fraction(8, 3)],
        )
        self.assertEqual(
            [lyric.text for value in tuplet_notes for lyric in value.lyrics],
            ["One", "two", "three"],
        )

    def test_minor_mode_is_preserved_without_changing_the_music(self) -> None:
        parsed = parse_expanded_mup(
            SYNTHETIC_SOURCE.replace("key=1&", "key=3& minor")
        )
        self.assertEqual(parsed.fifths, -3)
        self.assertEqual(parsed.mode, "minor")
        score = score_to_music21(parsed)
        first_key = score.parts[0].measure(1).getElementsByClass("Key")[0]
        self.assertEqual(first_key.mode, "minor")
        self.assertEqual(first_key.tonic.name, "C")

    def test_dynamic_meter_repeats_beams_and_blank_lyrics_are_preserved(self) -> None:
        parsed = parse_expanded_mup(DYNAMIC_SOURCE)
        self.assertEqual(
            [measure.time_signature for measure in parsed.measures],
            ["3/4", "4/4"],
        )
        score = score_to_music21(parsed)
        self.assertEqual(
            score.parts[0].measure(2).timeSignature.ratioString,
            "4/4",
        )
        self.assertEqual(score.parts[0].measure(2).leftBarline.direction, "start")
        self.assertEqual(score.parts[0].measure(2).rightBarline.direction, "end")
        lyrics = [
            lyric.text
            for value in score.parts[0].measure(2).voices[0].notes
            for lyric in value.lyrics
        ]
        self.assertEqual(lyrics, ["Four", "five", "six"])

    def test_implicit_lyric_layer_moves_to_unique_bass_entrance(self) -> None:
        score = score_to_music21(parse_expanded_mup(BASS_ENTRANCE_SOURCE))
        bass_notes = list(score.parts[1].measure(1).voices[1].notes)
        self.assertEqual(
            [lyric.text for value in bass_notes for lyric in value.lyrics],
            ["We", "rise"],
        )

    def test_trailing_article_title_is_the_same_work(self) -> None:
        self.assertTrue(
            _normalized_title_variants("The Blood Of My Redeemer")
            & _normalized_title_variants("Blood Of My Redeemer, The")
        )

    def test_bulk_conversion_preserves_arrangements_and_reports_holds(self) -> None:
        page = b"Copyright: Public Domain - USA"
        good_source = b"// This Mup code is donated to the public domain.\n"
        held_source = b"// This Mup code is donated to the public domain.\nheld\n"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            raw = root / "raw"
            (raw / "pages").mkdir(parents=True)
            (raw / "mup").mkdir()
            records = []
            for arrangement_id, source in (
                ("abide-with-me-monk", good_source),
                ("abide-with-me-troyte", held_source),
            ):
                page_file = f"pages/{arrangement_id}.html"
                source_file = f"mup/{arrangement_id}.mup"
                (raw / page_file).write_bytes(page)
                (raw / source_file).write_bytes(source)
                records.append(
                    {
                        "arrangement_id": arrangement_id,
                        "work_id": "abide-with-me",
                        "title": "Abide With Me",
                        "arrangement_label": arrangement_id.rsplit("-", 1)[-1],
                        "disposition": "pending_conversion",
                        "page_file": page_file,
                        "page_sha256": hashlib.sha256(page).hexdigest(),
                        "page_rights_declaration": "Copyright: Public Domain - USA",
                        "source_file": source_file,
                        "source_sha256": hashlib.sha256(source).hexdigest(),
                    }
                )
            inventory_path = root / "inventory.json"
            inventory_path.write_text(
                json.dumps(
                    {
                        "schema_version": 2,
                        "dataset_id": "hymns-to-god-public-domain-usa",
                        "records": records,
                    }
                ),
                encoding="utf-8",
            )
            output_dir = root / "musicxml"

            def fake_convert(**kwargs):
                source_path = kwargs["source_path"]
                if source_path.name == "abide-with-me-troyte.mup":
                    raise MupConversionError("unsupported synthetic setting")
                kwargs["output_path"].parent.mkdir(parents=True, exist_ok=True)
                kwargs["output_path"].write_text("<score-partwise/>", encoding="utf-8")
                return parse_expanded_mup(SYNTHETIC_SOURCE)

            with patch(
                "convert_hymns_to_god_mup.convert_source",
                side_effect=fake_convert,
            ), patch(
                "convert_hymns_to_god_mup._mup_version",
                return_value="7.2",
            ):
                report = convert_inventory(
                    inventory_path=inventory_path,
                    source_root=raw,
                    output_dir=output_dir,
                    mup_executable=root / "mup",
                    conversion_report=root / "conversion.json",
                )

            self.assertEqual(
                report["summary"],
                {"conversion_hold": 1, "eligible": 1},
            )
            self.assertEqual(
                {record["arrangement_id"] for record in report["records"]},
                {"abide-with-me-monk", "abide-with-me-troyte"},
            )
            self.assertTrue(
                (output_dir / "abide-with-me-monk.musicxml").is_file()
            )
            eligible = next(
                record
                for record in report["records"]
                if record["disposition"] == "eligible"
            )
            self.assertFalse(eligible["source_title_matches_page"])

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
            source_path = raw_root / record["source_file"]
            self.assertEqual(
                hashlib.sha256(source_path.read_bytes()).hexdigest(),
                record["source_sha256"],
            )
        self.assertEqual(
            counts,
            {"pending_conversion": 592, "rights_hold": 2},
        )

        conversion = json.loads(
            (manifest_path.parent / "conversion.json").read_text(encoding="utf-8")
        )
        self.assertEqual(
            conversion["summary"], {"eligible": 592, "rights_hold": 2}
        )
        self.assertEqual(
            conversion["inventory_sha256"],
            hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
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
        self.assertEqual(len(items), 592)
        self.assertTrue(
            all(
                item["score"]["generator"]
                == {"name": "hymns-to-god-mup-satb", "version": "2"}
                for item in items
            )
        )


if __name__ == "__main__":
    unittest.main()

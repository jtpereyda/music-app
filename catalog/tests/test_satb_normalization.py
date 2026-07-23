from __future__ import annotations

from pathlib import Path
import sys
import unittest
import xml.etree.ElementTree as ET


CATALOG_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CATALOG_ROOT / "scripts"))

from normalize_satb_musicxml import (  # noqa: E402
    DROP_EMPTY_PARTS,
    SPLIT_COMBINED_CHORD_VOICES,
    normalize_satb_musicxml,
)


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _text(element: ET.Element, name: str) -> str:
    return next(
        (child.text or "")
        for child in element.iter()
        if _local_name(child.tag) == name
    )


COMBINED_XML = b"""\
<score-partwise version="3.1">
  <part-list><score-part id="P1"><part-name /></score-part></part-list>
  <part id="P1">
    <measure number="1">
      <attributes><divisions>1</divisions></attributes>
      <note>
        <pitch><step>C</step><octave>4</octave></pitch>
        <duration>1</duration><voice>1</voice><type>quarter</type>
        <lyric number="1"><text>Test</text></lyric>
      </note>
      <note>
        <chord />
        <pitch><step>E</step><octave>4</octave></pitch>
        <duration>1</duration><voice>1</voice><type>quarter</type>
      </note>
      <note>
        <pitch><step>G</step><octave>4</octave></pitch>
        <duration>1</duration><voice>1</voice><type>quarter</type>
      </note>
      <backup><duration>2</duration></backup>
      <note>
        <rest /><duration>1</duration><voice>2</voice><type>quarter</type>
      </note>
      <note>
        <pitch><step>G</step><octave>4</octave></pitch>
        <duration>1</duration><voice>2</voice><type>quarter</type>
      </note>
    </measure>
  </part>
</score-partwise>
"""


class SatbNormalizationTests(unittest.TestCase):
    def test_split_combined_chords_preserves_two_aligned_lines(self) -> None:
        result = normalize_satb_musicxml(
            COMBINED_XML,
            SPLIT_COMBINED_CHORD_VOICES,
        )
        root = ET.fromstring(result.data)
        measure = next(
            element for element in root.iter() if _local_name(element.tag) == "measure"
        )
        notes = [
            element for element in measure if _local_name(element.tag) == "note"
        ]

        self.assertEqual(
            [(_text(note, "voice"), _text(note, "step")) for note in notes],
            [("1", "E"), ("1", "G"), ("2", "C"), ("2", "G")],
        )
        self.assertFalse(
            any(
                _local_name(child.tag) == "chord"
                for note in notes
                for child in note
            )
        )
        lyric_voices = [
            _text(note, "voice")
            for note in notes
            if any(_local_name(child.tag) == "lyric" for child in note)
        ]
        self.assertEqual(lyric_voices, ["1"])
        backup = next(
            element
            for element in measure
            if _local_name(element.tag) == "backup"
        )
        self.assertEqual(_text(backup, "duration"), "2")

    def test_drop_empty_part_removes_matching_part_list_entry(self) -> None:
        source = b"""\
<score-partwise version="3.1">
  <part-list>
    <score-part id="P1"><part-name /></score-part>
    <score-part id="P2"><part-name /></score-part>
    <score-part id="P3"><part-name /></score-part>
  </part-list>
  <part id="P1"><measure number="1"><note><rest /><duration>1</duration><voice>1</voice></note></measure></part>
  <part id="P2"><measure number="1"><note><rest /><duration>1</duration><voice>1</voice></note></measure></part>
  <part id="P3"><measure number="1"><attributes><divisions>1</divisions></attributes></measure></part>
</score-partwise>
"""
        result = normalize_satb_musicxml(source, DROP_EMPTY_PARTS)
        root = ET.fromstring(result.data)
        part_ids = [
            element.get("id")
            for element in root
            if _local_name(element.tag) == "part"
        ]
        score_part_ids = [
            element.get("id")
            for element in root.iter()
            if _local_name(element.tag) == "score-part"
        ]
        self.assertEqual(part_ids, ["P1", "P2"])
        self.assertEqual(score_part_ids, ["P1", "P2"])


if __name__ == "__main__":
    unittest.main()

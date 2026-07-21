from __future__ import annotations

import unittest

from hymn_ingest.musicxml_validation import validate_musicxml


VALID_XML = b"""<?xml version="1.0"?>
<score-partwise xmlns="http://www.musicxml.org/ns/musicxml" version="4.0">
  <part-list><score-part id="P1"><part-name>Voice</part-name></score-part></part-list>
  <part id="P1">
    <measure number="1">
      <attributes>
        <divisions>1</divisions>
        <key><fifths>-1</fifths><mode>major</mode></key>
        <time><beats>3</beats><beat-type>4</beat-type></time>
        <staves>2</staves>
      </attributes>
      <note>
        <pitch><step>F</step><octave>4</octave></pitch>
        <duration>1</duration><voice>1</voice>
        <lyric number="1"><text>Test</text></lyric>
      </note>
      <note><rest/><duration>2</duration><voice>2</voice></note>
    </measure>
  </part>
</score-partwise>
"""


class MusicXMLValidationTests(unittest.TestCase):
    def test_namespaced_musicxml_semantics_are_counted(self) -> None:
        result = validate_musicxml(VALID_XML)
        self.assertTrue(result.valid)
        self.assertEqual(result.stats["parts"], 1)
        self.assertEqual(result.stats["staves"], 2)
        self.assertEqual(result.stats["voices"], 2)
        self.assertEqual(result.stats["pitched_notes"], 1)
        self.assertEqual(result.stats["rests"], 1)
        self.assertEqual(result.stats["lyric_verse_ids"], ["1"])
        self.assertEqual(result.stats["key_signatures"], ["-1:major"])
        self.assertEqual(result.stats["time_signatures"], ["3/4"])

    def test_invalid_xml_is_reported(self) -> None:
        result = validate_musicxml(b"<score-partwise>")
        self.assertFalse(result.valid)
        self.assertEqual(result.errors[0]["code"], "xml_parse_error")

    def test_non_grace_note_requires_duration(self) -> None:
        data = VALID_XML.replace(b"<duration>1</duration>", b"", 1)
        result = validate_musicxml(data)
        self.assertFalse(result.valid)
        self.assertIn("missing_note_duration", {error["code"] for error in result.errors})


if __name__ == "__main__":
    unittest.main()


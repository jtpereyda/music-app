from __future__ import annotations

from pathlib import Path
import sys
import unittest


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPOSITORY_ROOT / "catalog/scripts"))

from inventory_timeless_truths import (  # noqa: E402
    _arrangement_id,
    _rights_kind,
    analyze_musicxml,
    parse_index,
    parse_work_page,
)


INDEX_HTML = b"""
<html><body>
<a href="../../../music/A_Charge_to_Keep_I_Have/score/">score</a>
<a href="../../../music/A_Charge_to_Keep_I_Have/">A Charge</a>
<a href="../../../music/Nothing_Between/score/">score</a>
<a href="../../../music/Nothing_Between/">Nothing Between</a>
</body></html>
"""

WORK_HTML = b"""
<html><body>
<h1 class="first">A Charge to Keep I Have</h1>
<p data-editable="tt3_music|url=A_Charge_to_Keep_I_Have|author">
Charles Wesley, 1762</p>
<p data-editable="tt3_music|url=A_Charge_to_Keep_I_Have|copyright">
copyright status is <a>Public Domain</a></p>
<p data-editable="tt3_music|url=A_Charge_to_Keep_I_Have|subject">
Subjects: Consecration, Work</p>
<fieldset>
<p class="scoretitle">Boylston [<a href="../../library/music/A/A_Charge_to_Keep_I_Have/A_Charge_to_Keep_I_Have.xml">.xml</a>]</p>
<p data-editable="tt3_scores|title=Boylston|author">Lowell Mason, 1832</p>
<p data-editable="tt3_scores|title=Boylston|copyright">copyright status is <a>Public Domain</a></p>
<p data-editable="tt3_scores|title=Boylston|keytone">Key: C</p>
<p data-editable="tt3_scores|title=Boylston|meter">Meter: S.M.</p>
</fieldset>
<fieldset>
<p class="scoretitle">Ferguson [<a href="../../library/music/A/A_Charge_to_Keep_I_Have/A_Charge_to_Keep_I_Have_2.xml">.xml</a>]</p>
<p data-editable="tt3_scores|title=Ferguson|author">John Ferguson, 1810</p>
<p data-editable="tt3_scores|title=Ferguson|copyright">copyright status is <a>Uncertain</a></p>
<p data-editable="tt3_scores|title=Ferguson|keytone">Key: E-flat</p>
<p data-editable="tt3_scores|title=Ferguson|meter">Meter: S.M.</p>
</fieldset>
</body></html>
"""

SEMANTIC_SATB_XML = b"""<?xml version="1.0" encoding="UTF-8"?>
<score-partwise version="3.0">
  <work><work-title>A Charge to Keep I Have</work-title></work>
  <identification><encoding><software>Sibelius 7.5</software></encoding></identification>
  <part-list>
    <score-part id="P1"><part-name>Soprano and Alto</part-name></score-part>
    <score-part id="P2"><part-name>Tenor and Bass</part-name></score-part>
  </part-list>
  <part id="P1"><measure number="1">
    <attributes><divisions>1</divisions><key><fifths>0</fifths><mode>major</mode></key></attributes>
    <note><pitch><step>C</step><octave>4</octave></pitch><duration>1</duration><voice>1</voice><lyric number="part1verse1"><text>A</text></lyric></note>
    <backup><duration>1</duration></backup>
    <note><pitch><step>A</step><octave>3</octave></pitch><duration>1</duration><voice>2</voice></note>
  </measure></part>
  <part id="P2"><measure number="1">
    <note><pitch><step>F</step><octave>3</octave></pitch><duration>1</duration><voice>1</voice></note>
    <backup><duration>1</duration></backup>
    <note><pitch><step>C</step><octave>3</octave></pitch><duration>1</duration><voice>2</voice></note>
  </measure></part>
</score-partwise>
"""


class TimelessTruthsInventoryTests(unittest.TestCase):
    def test_index_preserves_source_order_and_work_identity(self) -> None:
        records = parse_index(INDEX_HTML)

        self.assertEqual([record.ordinal for record in records], [1, 2])
        self.assertEqual(
            [record.slug for record in records],
            ["A_Charge_to_Keep_I_Have", "Nothing_Between"],
        )
        self.assertEqual(
            records[0].page_url,
            "https://library.timelesstruths.org/music/A_Charge_to_Keep_I_Have/",
        )

    def test_page_parser_preserves_multiple_score_settings(self) -> None:
        page = parse_work_page(
            WORK_HTML,
            page_url=(
                "https://library.timelesstruths.org/music/"
                "A_Charge_to_Keep_I_Have/"
            ),
        )

        self.assertEqual(page["title"], "A Charge to Keep I Have")
        self.assertEqual(page["rights_kind"], "public_domain")
        self.assertEqual(len(page["scores"]), 2)
        self.assertEqual(page["scores"][0]["title"], "Boylston")
        self.assertEqual(page["scores"][0]["rights_kind"], "public_domain")
        self.assertEqual(page["scores"][1]["title"], "Ferguson")
        self.assertEqual(page["scores"][1]["rights_kind"], "uncertain")
        self.assertTrue(page["scores"][1]["xml_url"].endswith("_2.xml"))

    def test_arrangement_identity_distinguishes_source_settings(self) -> None:
        first_url = (
            "https://library.timelesstruths.org/library/music/A/"
            "A_Charge_to_Keep_I_Have/A_Charge_to_Keep_I_Have.xml"
        )
        second_url = first_url.replace(".xml", "_2.xml")

        self.assertEqual(
            _arrangement_id("a-charge-to-keep-i-have", first_url),
            "a-charge-to-keep-i-have",
        )
        self.assertEqual(
            _arrangement_id("a-charge-to-keep-i-have", second_url),
            "a-charge-to-keep-i-have-2",
        )

    def test_musicxml_analysis_identifies_semantic_satb(self) -> None:
        facts = analyze_musicxml(SEMANTIC_SATB_XML)

        self.assertEqual(facts["profile"], "semantic_satb_two_staff")
        self.assertEqual(facts["part_voice_ids"], [["1", "2"], ["1", "2"]])
        self.assertEqual(facts["lyric_locations"], [[0, "1"]])
        self.assertEqual(facts["fifths"], "0")
        self.assertEqual(facts["mode"], "major")
        self.assertRegex(facts["music_fingerprint_sha256"], r"^[0-9a-f]{64}$")

    def test_rights_gate_fails_closed(self) -> None:
        self.assertEqual(_rights_kind("copyright status is Public Domain"), "public_domain")
        self.assertEqual(_rights_kind("copyright is CC License"), "cc_license")
        self.assertEqual(_rights_kind("copyright status is Uncertain"), "uncertain")
        self.assertEqual(_rights_kind(""), "missing")


if __name__ == "__main__":
    unittest.main()

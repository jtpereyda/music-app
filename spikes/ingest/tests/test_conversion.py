from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest

from hymn_ingest.abc_inventory import build_inventory
from hymn_ingest.conversion import classify_converter_stderr, convert_inventory


FIXTURES = Path(__file__).parent / "fixtures"


class ConversionTests(unittest.TestCase):
    def test_inventory_converts_to_validated_musicxml_and_report(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "hymnal.abc"
            source.write_bytes((FIXTURES / "open_hymnal_sample.abc").read_bytes())
            inventory_path = root / "build" / "inventory.json"
            build_inventory(
                input_path=source,
                split_dir=root / "build" / "abc",
                report_path=inventory_path,
            )

            report = convert_inventory(
                inventory_path=inventory_path,
                converter_path=FIXTURES / "fake_abc2xml.py",
                converter_version="fixture",
                output_dir=root / "build" / "musicxml",
                report_path=root / "build" / "conversion.json",
                converter_python=Path(sys.executable),
            )

            self.assertEqual(report["summary"]["total"], 2)
            self.assertEqual(report["summary"]["succeeded"], 2)
            self.assertEqual(report["summary"]["clean"], 2)
            self.assertEqual(report["summary"]["cleanup_marker_occurrences"], {})
            self.assertEqual(report["summary"]["success_rate"], 1.0)
            for tune in report["tunes"]:
                self.assertEqual(tune["status"], "succeeded")
                self.assertEqual(tune["stats"]["notes"], 2)
                self.assertTrue(tune["musicxml_sha256"])
            routine = report["tunes"][1]
            self.assertTrue(routine["clean"])
            self.assertTrue(routine["converter_diagnostics"])
            self.assertEqual(
                {diagnostic["severity"] for diagnostic in routine["converter_diagnostics"]},
                {"info"},
            )

    def test_converter_failure_does_not_stop_remaining_report(self) -> None:
        text = "X:999\nT:Failure\nM:4/4\nL:1/4\nK:C\nC4|\nX:1\nT:Success\nK:C\nC4|\n"
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "mixed.abc"
            source.write_text(text, encoding="utf-8")
            inventory_path = root / "inventory.json"
            build_inventory(
                input_path=source,
                split_dir=root / "abc",
                report_path=inventory_path,
            )
            report = convert_inventory(
                inventory_path=inventory_path,
                converter_path=FIXTURES / "fake_abc2xml.py",
                converter_version="fixture",
                output_dir=root / "musicxml",
                report_path=root / "conversion.json",
                converter_python=Path(sys.executable),
            )

        self.assertEqual(report["summary"]["failed"], 1)
        self.assertEqual(report["summary"]["succeeded"], 1)
        self.assertEqual(report["tunes"][0]["status"], "failed")
        self.assertFalse(report["tunes"][0]["cleanup_required"])
        self.assertEqual(report["tunes"][1]["status"], "succeeded")

    def test_converter_diagnostics_distinguish_info_from_cleanup(self) -> None:
        diagnostics = classify_converter_stderr(
            b"""-- decoded from utf-8
-- skipped I-field: newpage
-- unhandled note decorations: ['sintro']
-- unhandled note decorations: ['invertedfermata']
-- dropped voice mapping for V:3
-- empty voice V:4
-- done in 0.03 secs
"""
        )
        by_code = {diagnostic["code"]: diagnostic for diagnostic in diagnostics}
        self.assertEqual(by_code["converter_info"]["severity"], "info")
        self.assertEqual(
            by_code["unhandled_note_decoration"]["severity"],
            "cleanup",
        )
        self.assertEqual(by_code["dropped_mapping"]["severity"], "cleanup")
        self.assertEqual(by_code["empty_voice"]["severity"], "cleanup")
        decoration_items = {
            item
            for diagnostic in diagnostics
            if diagnostic["code"] == "unhandled_note_decoration"
            for item in diagnostic["items"]
        }
        self.assertEqual(decoration_items, {"sintro", "invertedfermata"})


if __name__ == "__main__":
    unittest.main()

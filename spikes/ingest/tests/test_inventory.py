from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from hymn_ingest.abc_inventory import ABCInventoryError, build_inventory, split_tunes


FIXTURES = Path(__file__).parent / "fixtures"


class InventoryTests(unittest.TestCase):
    def test_split_preserves_preamble_and_header_metadata(self) -> None:
        source = (FIXTURES / "open_hymnal_sample.abc").read_text(encoding="utf-8")
        preamble, tunes = split_tunes(source)

        self.assertEqual(len(tunes), 2)
        self.assertTrue(preamble.startswith("%abc-2.2"))
        self.assertTrue(tunes[0].text.startswith("%abc-2.2"))
        self.assertTrue(tunes[1].text.startswith("%abc-2.2"))
        self.assertEqual(tunes[0].reference, "1")
        self.assertEqual(tunes[0].titles, ["Alpha Hymn", "Alpha Alternate"])
        self.assertEqual(tunes[1].headers["K"], ["G"])

    def test_inventory_is_structured_and_files_match_hashes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            input_path = root / "hymnal.abc"
            input_path.write_bytes((FIXTURES / "open_hymnal_sample.abc").read_bytes())
            report_path = root / "build" / "inventory.json"
            split_dir = root / "build" / "abc"

            report = build_inventory(
                input_path=input_path,
                split_dir=split_dir,
                report_path=report_path,
            )

            self.assertEqual(report["summary"]["tune_count"], 2)
            self.assertEqual(report["summary"]["warning_count"], 0)
            self.assertEqual(report["tunes"][0]["primary_title"], "Alpha Hymn")
            self.assertEqual(report["tunes"][1]["source_line_start"], 17)
            self.assertTrue((split_dir / report["tunes"][0]["file"]).is_file())
            self.assertEqual(report["source"]["encoding"], "utf-8")
            self.assertEqual(
                report["source"]["raw"]["sha256"],
                report["source"]["normalized_utf8"]["sha256"],
            )
            self.assertEqual(json.loads(report_path.read_text()), report)

    def test_windows_1252_source_reports_raw_and_normalized_hashes(self) -> None:
        raw = b"X:1\nT:En dash \x96 hymn\nK:C\nC|\n"
        normalized = raw.decode("windows-1252").encode("utf-8")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            input_path = root / "windows.abc"
            input_path.write_bytes(raw)
            report = build_inventory(
                input_path=input_path,
                split_dir=root / "split",
                report_path=root / "inventory.json",
                source_encoding="windows-1252",
                expected_raw_bytes=len(raw),
                expected_raw_sha256=hashlib.sha256(raw).hexdigest(),
                expected_normalized_utf8_bytes=len(normalized),
                expected_normalized_utf8_sha256=hashlib.sha256(normalized).hexdigest(),
                expected_tune_count=1,
            )

            split_text = (root / "split" / report["tunes"][0]["file"]).read_text(
                encoding="utf-8"
            )

        self.assertIn("En dash \u2013 hymn", split_text)
        self.assertEqual(report["source"]["encoding"], "windows-1252")
        self.assertEqual(
            report["source"]["raw"]["sha256"],
            hashlib.sha256(raw).hexdigest(),
        )
        self.assertEqual(
            report["source"]["normalized_utf8"]["sha256"],
            hashlib.sha256(normalized).hexdigest(),
        )

    def test_source_lock_mismatch_is_rejected_before_writing_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            input_path = root / "source.abc"
            input_path.write_text("X:1\nT:Test\nK:C\nC|\n", encoding="utf-8")
            with self.assertRaisesRegex(ABCInventoryError, "raw SHA-256"):
                build_inventory(
                    input_path=input_path,
                    split_dir=root / "split",
                    report_path=root / "inventory.json",
                    expected_raw_sha256="0" * 64,
                )
            self.assertFalse((root / "split").exists())
            self.assertFalse((root / "inventory.json").exists())

    def test_duplicate_references_and_missing_metadata_are_warnings(self) -> None:
        text = "X:7\nT:One\nK:C\nC|\nX:7\nK:G\nG|\n"
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            input_path = root / "duplicate.abc"
            input_path.write_text(text, encoding="utf-8")
            report = build_inventory(
                input_path=input_path,
                split_dir=root / "split",
                report_path=root / "inventory.json",
            )

        first_codes = {warning["code"] for warning in report["tunes"][0]["warnings"]}
        second_codes = {warning["code"] for warning in report["tunes"][1]["warnings"]}
        self.assertIn("duplicate_reference", first_codes)
        self.assertIn("duplicate_reference", second_codes)
        self.assertIn("missing_title", second_codes)

    def test_missing_reference_boundary_is_rejected(self) -> None:
        with self.assertRaises(ABCInventoryError):
            split_tunes("T:Not a complete ABC tune\nK:C\nC|\n")


if __name__ == "__main__":
    unittest.main()

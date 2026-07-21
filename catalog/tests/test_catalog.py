from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
import unittest


CATALOG_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CATALOG_ROOT / "scripts"))

from validate_catalog import RIGHTS_STATUS, validate_catalog_data  # noqa: E402


LANDMARK_IDS = {
    "amazing-grace",
    "beneath-the-cross-of-jesus",
    "blessed-assurance",
    "come-thou-fount-of-every-blessing",
    "it-is-well-with-my-soul",
    "o-for-a-thousand-tongues",
}


class CatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog = json.loads((CATALOG_ROOT / "catalog.json").read_text(encoding="utf-8"))
        cls.schema = json.loads(
            (CATALOG_ROOT / "catalog.schema.json").read_text(encoding="utf-8")
        )

    def test_catalog_and_musicxml_artifacts_validate(self) -> None:
        self.assertEqual(validate_catalog_data(self.catalog), [])

    def test_expanded_catalog_and_safety_status(self) -> None:
        ids = {item["id"] for item in self.catalog["items"]}
        self.assertTrue(LANDMARK_IDS <= ids)
        self.assertEqual(len(self.catalog["items"]), 262)
        for item in self.catalog["items"]:
            self.assertEqual(item["rights"]["status"], RIGHTS_STATUS)
            self.assertEqual(item["lyrics"]["scope"], "soprano_only")
            self.assertEqual(item["available_lines"], ["SATB", "S", "A", "T", "B"])
            self.assertTrue(item["display"]["text_author"])
            self.assertTrue(item["display"]["tune_name"])

    def test_import_report_accounts_for_every_source_record(self) -> None:
        report = json.loads(
            (CATALOG_ROOT / "import-report.json").read_text(encoding="utf-8")
        )
        self.assertEqual(
            report["summary"],
            {
                "catalog_items": 262,
                "exact_public_domain_candidates": 275,
                "rights_holds": 18,
                "source_records": 293,
                "structure_holds": 13,
            },
        )

    def test_schema_pins_non_production_rights_status(self) -> None:
        status = self.schema["$defs"]["rights"]["properties"]["status"]["const"]
        self.assertEqual(status, RIGHTS_STATUS)

    def test_validator_detects_score_hash_mutation(self) -> None:
        mutated = copy.deepcopy(self.catalog)
        mutated["items"][0]["score"]["sha256"] = "0" * 64
        errors = validate_catalog_data(mutated)
        self.assertTrue(any("score SHA-256 mismatch" in error for error in errors))


if __name__ == "__main__":
    unittest.main()

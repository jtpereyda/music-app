from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
import unittest


CATALOG_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CATALOG_ROOT / "scripts"))

from validate_catalog import RIGHTS_STATUS, validate_catalog_data  # noqa: E402
from build_open_hymnal_catalog import _abc_key, _assign_ids, _key_name  # noqa: E402


LANDMARK_IDS = {
    "a-child-of-the-king",
    "amazing-grace",
    "away-in-a-manger",
    "beneath-the-cross-of-jesus",
    "blessed-assurance",
    "come-thou-fount-of-every-blessing",
    "did-you-think-to-pray",
    "he-keeps-me-singing",
    "great-is-thy-faithfulness",
    "it-is-well-with-my-soul",
    "jesus-loves-me",
    "now-thank-we-all-our-god",
    "o-for-a-thousand-tongues",
    "praise-my-soul-the-king-of-heaven",
    "rescue-the-perishing",
    "the-law-of-god-is-good-and-wise",
    "you-parents-hear-what-jesus-taught",
}
NORMALIZED_IDS = {
    "away-in-a-manger",
    "did-you-think-to-pray",
    "jesus-loves-me",
    "now-thank-we-all-our-god",
    "praise-my-soul-the-king-of-heaven",
    "the-law-of-god-is-good-and-wise",
    "you-parents-hear-what-jesus-taught",
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
        self.assertEqual(self.catalog["catalog_revision"], "6")
        self.assertEqual(len(self.catalog["items"]), 869)
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
                "catalog_items": 869,
                "exact_public_domain_candidates": 875,
                "hymns_to_god_items": 592,
                "rights_holds": 20,
                "source_holds": 0,
                "source_records": 895,
                "structure_holds": 6,
                "supplement_items": 8,
            },
        )
        self.assertEqual(
            report["source_breakdown"]["combined_abc"]["catalog_items"], 269
        )
        self.assertEqual(
            report["source_breakdown"]["split_zip"][
                "selected_compatible_additions"
            ],
            8,
        )
        self.assertEqual(
            report["source_breakdown"]["hymns_to_god"],
            {
                "catalog_items": 592,
                "index_pages": 593,
                "public_domain_arrangements": 592,
                "public_domain_pages": 591,
                "rights_holds": 2,
                "source_holds": 0,
                "source_records": 594,
                "structure_holds": 0,
            },
        )

    def test_hymns_to_god_work_and_arrangement_identity_is_preserved(self) -> None:
        hymns_to_god = [
            item
            for item in self.catalog["items"]
            if item["source"]["collection_id"]
            == "hymns-to-god-public-domain-usa"
        ]
        self.assertEqual(len(hymns_to_god), 592)
        for item in hymns_to_god:
            source = item["source"]
            self.assertTrue(source["work_id"])
            self.assertTrue(source["arrangement_id"])
            self.assertEqual(
                source["record_reference"], source["arrangement_id"]
            )

        sweet_by_and_by = [
            item
            for item in hymns_to_god
            if item["source"]["work_id"] == "sweet-by-and-by"
        ]
        self.assertEqual(
            {
                item["source"]["arrangement_id"]
                for item in sweet_by_and_by
            },
            {"sweet-by-and-by-arr-1", "sweet-by-and-by-arr-2"},
        )

    def test_split_zip_additions_preserve_entry_identity(self) -> None:
        supplement = [
            item
            for item in self.catalog["items"]
            if item["source"]["collection_id"]
            == "open-hymnal-2014-06-split-zip"
        ]
        self.assertEqual(len(supplement), 8)
        self.assertTrue(
            all(item["source"]["entry_path"].endswith(".abc") for item in supplement)
        )

    def test_structural_normalizations_are_explicit_and_pinned(self) -> None:
        normalized = {
            item["id"]: item["score"]["normalization"]
            for item in self.catalog["items"]
            if "normalization" in item["score"]
        }
        self.assertEqual(set(normalized), NORMALIZED_IDS)
        for metadata in normalized.values():
            self.assertEqual(metadata["name"], "open-hymnal-satb-normalizer")
            self.assertEqual(metadata["version"], "1")
        self.assertEqual(
            normalized["now-thank-we-all-our-god"]["operations"],
            ["split_combined_chord_voices", "align_measure_numbers"],
        )
        for item_id, metadata in normalized.items():
            if item_id != "now-thank-we-all-our-god":
                self.assertEqual(len(metadata["operations"]), 1)

    def test_schema_pins_non_production_rights_status(self) -> None:
        status = self.schema["$defs"]["rights"]["properties"]["status"]["const"]
        self.assertEqual(status, RIGHTS_STATUS)

    def test_key_names_distinguish_major_and_minor_signatures(self) -> None:
        self.assertEqual(_key_name(-3, "major"), "E-flat major")
        self.assertEqual(_key_name(-3, "minor"), "C minor")
        self.assertEqual(_key_name(3, "minor"), "F-sharp minor")
        self.assertEqual(_abc_key(-3, "minor"), "Cm")

    def test_arrangement_ids_do_not_rename_existing_open_hymnal_routes(self) -> None:
        records = [
            {
                "title": "Amazing Grace",
                "tune_name": "New Britain",
                "source": {
                    "collection_id": "open-hymnal-2014-06",
                    "record_ordinal": 1,
                },
            },
            {
                "title": "Amazing Grace",
                "tune_name": "Alternate Setting",
                "_arrangement_id": "amazing-grace",
                "source": {
                    "collection_id": "hymns-to-god-public-domain-usa",
                    "record_ordinal": 2,
                },
            },
        ]
        _assign_ids(records)
        self.assertEqual(records[0]["id"], "amazing-grace")
        self.assertEqual(records[1]["id"], "amazing-grace-hymns-to-god")

    def test_original_hymns_to_god_routes_remain_stable(self) -> None:
        records = [
            {
                "title": "Near The Cross",
                "tune_name": "Doane",
                "_arrangement_id": "near-the-cross-doane",
                "source": {
                    "collection_id": "hymns-to-god-public-domain-usa",
                    "record_ordinal": 1,
                },
            },
            {
                "title": "Rejoice, The Lord Is King",
                "tune_name": "Darwall",
                "_arrangement_id": "rejoice-the-lord-is-king-darwall",
                "source": {
                    "collection_id": "hymns-to-god-public-domain-usa",
                    "record_ordinal": 2,
                },
            },
        ]
        _assign_ids(records)
        self.assertEqual(
            [record["id"] for record in records],
            ["near-the-cross", "rejoice-the-lord-is-king"],
        )

    def test_validator_detects_score_hash_mutation(self) -> None:
        mutated = copy.deepcopy(self.catalog)
        mutated["items"][0]["score"]["sha256"] = "0" * 64
        errors = validate_catalog_data(mutated)
        self.assertTrue(any("score SHA-256 mismatch" in error for error in errors))

    def test_validator_detects_mode_incorrect_key_name(self) -> None:
        mutated = copy.deepcopy(self.catalog)
        mutated["items"][0]["original_key"]["name"] = "C minor"
        errors = validate_catalog_data(mutated)
        self.assertTrue(
            any("original_key.name must be" in error for error in errors)
        )


if __name__ == "__main__":
    unittest.main()

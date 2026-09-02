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
    "nothing-between",
    "o-for-a-thousand-tongues",
    "praise-my-soul-the-king-of-heaven",
    "rescue-the-perishing",
    "the-law-of-god-is-good-and-wise",
    "you-parents-hear-what-jesus-taught",
}
OPEN_HYMNAL_NORMALIZED_IDS = {
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
        self.assertEqual(self.catalog["catalog_id"], "transposify-technical-preview")
        self.assertEqual(self.catalog["catalog_revision"], "9")
        self.assertEqual(len(self.catalog["items"]), 2373)
        hymns = [
            item for item in self.catalog["items"] if item["content_type"] == "hymn"
        ]
        art_songs = [
            item
            for item in self.catalog["items"]
            if item["content_type"] == "art_song"
        ]
        self.assertEqual(len(hymns), 1017)
        self.assertEqual(len(art_songs), 1356)
        for item in hymns:
            self.assertEqual(item["rights"]["status"], RIGHTS_STATUS)
            self.assertEqual(item["lyrics"]["scope"], "soprano_only")
            self.assertEqual(item["available_lines"], ["SATB", "S", "A", "T", "B"])
            self.assertTrue(item["display"]["text_author"])
            self.assertTrue(item["display"]["tune_name"])
        for item in art_songs:
            self.assertEqual(item["rights"]["status"], RIGHTS_STATUS)
            self.assertEqual(
                item["rights"]["source_declaration"],
                "Creative Commons Zero (CC0) 1.0 Universal",
            )
            self.assertIn(item["lyrics"]["scope"], {"vocal_parts", "none"})
            self.assertEqual(item["available_lines"], ["SCORE"])
            self.assertTrue(item["display"]["composer"])

    def test_import_report_accounts_for_every_source_record(self) -> None:
        report = json.loads(
            (CATALOG_ROOT / "import-report.json").read_text(encoding="utf-8")
        )
        self.assertEqual(
            report["summary"],
            {
                "catalog_items": 2373,
                "exact_public_domain_candidates": 4100,
                "hymns_to_god_items": 592,
                "openscore_lieder_items": 1356,
                "rights_holds": 46,
                "source_holds": 0,
                "source_records": 4146,
                "structure_holds": 17,
                "supplement_items": 8,
                "timeless_truths_items": 148,
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
        self.assertEqual(
            report["source_breakdown"]["openscore_lieder"],
            {
                "catalog_items": 1356,
                "exact_public_domain_candidates": 1356,
                "indexed_records": 1356,
                "source_records": 1356,
                "structure_holds": 0,
                "unindexed_mxl_files": 106,
            },
        )
        self.assertEqual(
            report["source_breakdown"]["timeless_truths"],
            {
                "catalog_items": 148,
                "distinct_arrangements": 21,
                "net_new_titles": 127,
                "normalization_backlog": 1710,
                "rights_holds": 26,
                "source_records": 1895,
                "strict_public_domain_musicxml": 1869,
                "structure_holds": 11,
            },
        )

    def test_openscore_lieder_pin_and_landmark_keys(self) -> None:
        manifest = json.loads(
            (CATALOG_ROOT.parent / "data" / "openscore-lieder" / "manifest.json")
            .read_text(encoding="utf-8")
        )
        self.assertEqual(
            manifest["pinned_commit"],
            "6b2dc542ce2e8aa4b78c8ee62103b210efc07015",
        )
        self.assertEqual(
            manifest["archive_sha256"],
            "e925dd89f9dc2ac16f2aff49470d2c1f2dec9977bb4059172cbcbc7a4b98958c",
        )
        self.assertEqual(manifest["summary"]["indexed_records"], 1356)
        self.assertEqual(manifest["summary"]["promoted_records"], 1356)
        self.assertEqual(manifest["summary"]["unindexed_mxl_files"], 106)

        by_id = {item["id"]: item for item in self.catalog["items"]}
        expected = {
            "lieder-5701612": ("Wiegenlied", "E-flat major"),
            "lieder-6810863": ("Après un rêve", "C minor"),
            "lieder-7111114": ("Gretchen am Spinnrade, D.118", "D minor"),
            "lieder-5016466": ("Der Lindenbaum", "E major"),
        }
        for item_id, (title, key_name) in expected.items():
            item = by_id[item_id]
            self.assertEqual(item["title"], title)
            self.assertEqual(item["original_key"]["name"], key_name)
            self.assertEqual(item["source"]["work_id"], item_id)
            self.assertEqual(item["source"]["arrangement_id"], item_id)
            self.assertTrue(item["source"]["entry_path"].endswith(f"lc{item_id.removeprefix('lieder-')}.mxl"))

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
        open_hymnal = {
            item_id: metadata
            for item_id, metadata in normalized.items()
            if metadata["name"] == "open-hymnal-satb-normalizer"
        }
        timeless_truths = {
            item_id: metadata
            for item_id, metadata in normalized.items()
            if metadata["name"] == "timeless-truths-satb-normalizer"
        }
        self.assertEqual(set(open_hymnal), OPEN_HYMNAL_NORMALIZED_IDS)
        self.assertEqual(len(timeless_truths), 148)
        for metadata in open_hymnal.values():
            self.assertEqual(metadata["name"], "open-hymnal-satb-normalizer")
            self.assertEqual(metadata["version"], "1")
        self.assertEqual(
            normalized["now-thank-we-all-our-god"]["operations"],
            ["split_combined_chord_voices", "align_measure_numbers"],
        )
        for item_id, metadata in open_hymnal.items():
            if item_id != "now-thank-we-all-our-god":
                self.assertEqual(len(metadata["operations"]), 1)
        self.assertEqual(
            normalized["nothing-between"],
            {
                "name": "timeless-truths-satb-normalizer",
                "operations": [
                    "normalize_sibelius_lyric_rows",
                    "split_sibelius_satb_dyads",
                    "strip_source_page_credits",
                ],
                "version": "1",
            },
        )

    def test_nothing_between_preserves_source_and_search_identity(self) -> None:
        item = next(
            item for item in self.catalog["items"] if item["id"] == "nothing-between"
        )
        self.assertEqual(item["source"]["collection_id"], "timeless-truths-public-domain")
        self.assertEqual(item["source"]["arrangement_id"], "nothing-between-clark")
        self.assertEqual(item["original_key"]["name"], "G major")
        self.assertEqual(
            item["display"]["search_terms"],
            [
                "Nothing Between My Soul and the Savior",
                "Nothing Between My Soul and the Saviour",
            ],
        )

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

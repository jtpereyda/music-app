from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path
import sys
import unittest
import xml.etree.ElementTree as ET


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
CATALOG_ROOT = REPOSITORY_ROOT / "catalog"
sys.path.insert(0, str(CATALOG_ROOT / "scripts"))

from import_timeless_truths import (  # noqa: E402
    EXPECTED_NORMALIZED_SHA256,
    EXPECTED_SOURCE_SHA256,
    _score_facts,
)
from normalize_satb_musicxml import (  # noqa: E402
    NORMALIZE_SIBELIUS_LYRIC_ROWS,
    SPLIT_SIBELIUS_SATB_DYADS,
    STRIP_SOURCE_PAGE_CREDITS,
    normalize_timeless_truths_musicxml,
)


SOURCE = REPOSITORY_ROOT / "data/timeless-truths/raw/Nothing_Between.xml"


class TimelessTruthsImportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source_data = SOURCE.read_bytes()
        cls.result = normalize_timeless_truths_musicxml(cls.source_data)

    def test_source_and_normalized_hashes_are_pinned(self) -> None:
        self.assertEqual(
            hashlib.sha256(self.source_data).hexdigest(),
            EXPECTED_SOURCE_SHA256,
        )
        self.assertEqual(
            hashlib.sha256(self.result.data).hexdigest(),
            EXPECTED_NORMALIZED_SHA256,
        )

    def test_normalization_produces_four_extractable_voices(self) -> None:
        facts = _score_facts(self.result.data)
        self.assertEqual(
            facts["voice_locations"],
            [(0, "1"), (0, "2"), (1, "1"), (1, "2")],
        )
        self.assertEqual(facts["lyric_locations"], [(0, "1")])
        self.assertEqual(facts["verse_ids"], ["1", "2", "3", "4"])
        root = ET.fromstring(self.result.data)
        self.assertFalse(any(element.tag.endswith("chord") for element in root.iter()))

    def test_normalization_operations_are_explicit(self) -> None:
        self.assertEqual(
            self.result.operations,
            (
                NORMALIZE_SIBELIUS_LYRIC_ROWS,
                SPLIT_SIBELIUS_SATB_DYADS,
                STRIP_SOURCE_PAGE_CREDITS,
            ),
        )

    def test_bulk_inventory_and_manifest_account_for_the_source(self) -> None:
        source_root = REPOSITORY_ROOT / "data/timeless-truths"
        inventory = json.loads((source_root / "inventory.json").read_text())
        manifest = json.loads((source_root / "manifest.json").read_text())

        self.assertEqual(len(inventory["records"]), 1895)
        self.assertEqual(
            inventory["summary"],
            {
                "normalization_candidate": 1710,
                "rights_hold": 26,
                "score_settings": 1895,
                "straightforward_candidate": 148,
                "strict_public_domain_musicxml": 1869,
                "structure_hold": 11,
            },
        )
        self.assertEqual(manifest["summary"]["promoted_records"], 148)
        self.assertEqual(manifest["summary"]["net_new_titles"], 126)
        self.assertEqual(manifest["summary"]["distinct_arrangements"], 22)
        self.assertEqual(len(manifest["records"]), 148)
        self.assertEqual(
            Counter(record["promotion_reason"] for record in manifest["records"]),
            {"distinct_arrangement": 22, "net_new_title": 126},
        )
        self.assertTrue(
            all(
                len(record["music_fingerprint_sha256"]) == 64
                for record in manifest["records"]
            )
        )
        self.assertEqual(
            len(list((source_root / "raw/xml").glob("*.xml"))),
            148,
        )


if __name__ == "__main__":
    unittest.main()

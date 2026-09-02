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
    SPLIT_SIBELIUS_MIXED_VOICES,
    SPLIT_SIBELIUS_MIXED_VOICES_WITH_CONTEXT,
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

    def test_mixed_voice_profile_produces_semantic_satb(self) -> None:
        source = (
            REPOSITORY_ROOT
            / "data/timeless-truths/raw/xml/abide-with-me.xml"
        ).read_bytes()
        result = normalize_timeless_truths_musicxml(
            source,
            work_title="Abide with Me",
        )
        facts = _score_facts(result.data)

        self.assertEqual(
            result.profile,
            "split_primary_dyads_with_secondary_voice",
        )
        self.assertIn(SPLIT_SIBELIUS_MIXED_VOICES, result.operations)
        self.assertEqual(result.duplicated_unison_events, 0)
        self.assertEqual(facts["chord_notes"], 0)
        self.assertEqual(
            facts["voice_locations"],
            [(0, "1"), (0, "2"), (1, "1"), (1, "2")],
        )

    def test_shared_printed_unisons_are_explicitly_counted(self) -> None:
        source = (
            REPOSITORY_ROOT
            / "data/timeless-truths/raw/xml/drifting-away-from-jesus.xml"
        ).read_bytes()
        result = normalize_timeless_truths_musicxml(
            source,
            work_title="Drifting Away from Jesus",
        )
        source_root = ET.fromstring(source)
        normalized_root = ET.fromstring(result.data)
        source_pitches = sum(
            element.tag.endswith("pitch") for element in source_root.iter()
        )
        normalized_pitches = sum(
            element.tag.endswith("pitch") for element in normalized_root.iter()
        )

        self.assertEqual(result.duplicated_unison_events, 60)
        self.assertEqual(normalized_pitches, source_pitches + 60)

    def test_interleaved_notation_is_preserved_at_its_voice_cursor(self) -> None:
        source = (
            REPOSITORY_ROOT
            / "data/timeless-truths/raw/xml/abiding-and-confiding.xml"
        ).read_bytes()
        result = normalize_timeless_truths_musicxml(
            source,
            work_title="Abiding and Confiding",
        )
        source_root = ET.fromstring(source)
        normalized_root = ET.fromstring(result.data)

        self.assertEqual(
            result.profile,
            "split_mixed_voices_with_interleaved_notation",
        )
        self.assertIn(
            SPLIT_SIBELIUS_MIXED_VOICES_WITH_CONTEXT,
            result.operations,
        )
        self.assertEqual(result.preserved_context_events, 1)
        for name in ("barline", "direction"):
            self.assertEqual(
                sum(element.tag.endswith(name) for element in source_root.iter()),
                sum(element.tag.endswith(name) for element in normalized_root.iter()),
            )

    def test_bulk_inventory_and_manifest_account_for_the_source(self) -> None:
        source_root = REPOSITORY_ROOT / "data/timeless-truths"
        inventory = json.loads((source_root / "inventory.json").read_text())
        manifest = json.loads((source_root / "manifest.json").read_text())

        self.assertEqual(inventory["schema_version"], 2)
        self.assertEqual(manifest["schema_version"], 3)
        self.assertEqual(len(inventory["records"]), 1895)
        self.assertEqual(
            inventory["summary"],
            {
                "normalization_candidate": 691,
                "rights_hold": 26,
                "score_settings": 1895,
                "straightforward_candidate": 1168,
                "strict_public_domain_musicxml": 1869,
                "structure_hold": 10,
            },
        )
        self.assertEqual(manifest["summary"]["promoted_records"], 1168)
        self.assertEqual(manifest["summary"]["net_new_titles"], 1016)
        self.assertEqual(manifest["summary"]["distinct_arrangements"], 152)
        self.assertEqual(manifest["summary"]["shared_unison_events"], 661)
        self.assertEqual(manifest["summary"]["preserved_context_events"], 1493)
        self.assertEqual(
            manifest["summary"]["normalization_profile_counts"],
            {
                "split_aligned_satb_dyads": 148,
                "split_mixed_voices_with_interleaved_notation": 685,
                "split_primary_dyads_with_secondary_voice": 335,
            },
        )
        self.assertEqual(len(manifest["records"]), 1168)
        self.assertEqual(
            Counter(record["promotion_reason"] for record in manifest["records"]),
            {"distinct_arrangement": 152, "net_new_title": 1016},
        )
        self.assertTrue(
            all(
                len(record["music_fingerprint_sha256"]) == 64
                for record in manifest["records"]
            )
        )
        self.assertEqual(
            len(list((source_root / "raw/xml").glob("*.xml"))),
            1168,
        )


if __name__ == "__main__":
    unittest.main()

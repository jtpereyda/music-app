from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest


CATALOG_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CATALOG_ROOT / "scripts"))

from inventory_hymns_to_god import (  # noqa: E402
    choose_source_variant,
    inventory_collection,
    load_cdx_snapshots,
    parse_index,
    parse_page,
    split_source_arrangements,
    _verified_retrieval,
)


class HymnsToGodInventoryTests(unittest.TestCase):
    def test_index_preserves_multiple_arrangements(self) -> None:
        index = b"""
        <dl><dt><a href="./A-Hymns/Abide-With-Me-Monk.html">Abide With Me</a>
        - (Lyte / Monk)</dt></dl>
        <dl><dt><a href="./A-Hymns/Abide-With-Me-Troyte.html">Abide With Me</a>
        - Chant (Lyte / Troyte)</dt></dl>
        """

        records = parse_index(index)

        self.assertEqual(len(records), 2)
        self.assertEqual({record.work_id for record in records}, {"abide-with-me"})
        self.assertEqual(
            {record.arrangement_id for record in records},
            {"abide-with-me-monk", "abide-with-me-troyte"},
        )
        self.assertEqual(records[0].arrangement_label, "(Lyte / Monk)")
        self.assertEqual(
            records[1].arrangement_label, "Chant (Lyte / Troyte)"
        )

    def test_one_page_can_expand_to_multiple_musical_arrangements(self) -> None:
        entry = parse_index(
            b'<dl><dt><a href="./S-Hymns/Sweet-By-And-By.html">Sweet By And By</a></dt></dl>'
        )[0]
        groups = split_source_arrangements(
            entry,
            [
                {
                    "label": "Hymn Page",
                    "url": "https://example.test/Sweet-By-And-By-Arr-1/score.mup",
                },
                {
                    "label": "Projection",
                    "url": "https://example.test/Sweet-By-And-By-Arr-1/projection.mup",
                },
                {
                    "label": "Hymn Page",
                    "url": "https://example.test/Sweet-By-And-By-Arr-2/score.mup",
                },
            ],
        )
        self.assertEqual(
            [(arrangement_id, label) for arrangement_id, label, _ in groups],
            [
                ("sweet-by-and-by-arr-1", "Arrangement 1"),
                ("sweet-by-and-by-arr-2", "Arrangement 2"),
            ],
        )

    def test_page_extracts_rights_people_and_mup_variants(self) -> None:
        page = b"""
        <title>Praise God, Ye Servants Of The Lord</title>
        <table>
          <tr><th>Lyrics:</th><td><a href="people/crosby.html">Fanny Crosby</a></td></tr>
          <tr><th>Music:</th><td><a href="people/lowry.html">Robert Lowry</a></td></tr>
          <tr><th>MUP File:</th><td>
            <a href="score-6x9.mup">6x9</a>
            <a href="score-letter.mup">Letter</a>
            <a href="score-projection.mup">Projection</a>
          </td></tr>
          <tr><th>Copyright:</th><td><a>Public Domain - USA</a></td></tr>
        </table>
        """

        parsed = parse_page(page, "https://example.test/hymn/page.html")

        self.assertEqual(parsed["page_title"], "Praise God, Ye Servants Of The Lord")
        self.assertEqual(parsed["lyricist"], "Fanny Crosby")
        self.assertEqual(parsed["composer"], "Robert Lowry")
        self.assertEqual(
            parsed["page_rights_declaration"],
            "Copyright: Public Domain - USA",
        )
        variants = parsed["source_variants"]
        self.assertEqual(len(variants), 3)
        self.assertEqual(choose_source_variant(variants)["label"], "Letter")

    def test_non_mup_links_are_not_source_variants(self) -> None:
        page = b"""
        <table><tr><th>MUP File:</th><td>
          <a href="score.pdf">PDF</a><a href="score.mup">Hymn Page</a>
        </td></tr></table>
        """

        parsed = parse_page(page, "https://example.test/hymn/page.html")

        self.assertEqual(
            parsed["source_variants"],
            [{"label": "Hymn Page", "url": "https://example.test/hymn/score.mup"}],
        )

    def test_mislabelled_metadata_row_still_exposes_mup_source(self) -> None:
        page = b"""
        <table><tr><th>Hymn Page:</th><td>
          <a href="score.mup">Hymn Page</a>
        </td></tr></table>
        """
        parsed = parse_page(page, "https://example.test/hymn/page.html")
        self.assertEqual(
            parsed["source_variants"],
            [{"label": "Hymn Page", "url": "https://example.test/hymn/score.mup"}],
        )

    def test_page_tolerates_implicitly_closed_table_cells(self) -> None:
        page = b"""
        <table><tr><th>MUP File:</th>
          <td><a href="score.mup">Hymn Page</a>
          <td></td><td></td>
        </tr><tr><th>Copyright:</th>
          <td><a>Public Domain - USA</a><td></td>
        </tr></table>
        """
        parsed = parse_page(page, "https://example.test/hymn/page.html")
        self.assertEqual(
            parsed["source_variants"],
            [{"label": "Hymn Page", "url": "https://example.test/hymn/score.mup"}],
        )
        self.assertEqual(
            parsed["page_rights_declaration"],
            "Copyright: Public Domain - USA",
        )

    def test_inventory_is_arrangement_aware_and_resumes_cached_downloads(self) -> None:
        index = b"""
        <dl><dt><a href="./A-Hymns/Abide-With-Me-Monk.html">Abide With Me</a>
        - (Lyte / Monk)</dt></dl>
        <dl><dt><a href="./A-Hymns/Abide-With-Me-Troyte.html">Abide With Me</a>
        - Chant (Lyte / Troyte)</dt></dl>
        """
        page_template = """
        <table>
          <tr><th>Lyrics:</th><td>Henry Lyte</td></tr>
          <tr><th>Music:</th><td>{composer}</td></tr>
          <tr><th>MUP File:</th><td><a href="{source}">Letter</a></td></tr>
          <tr><th>Copyright:</th><td>Public Domain - USA</td></tr>
        </table>
        """
        responses = {
            "https://example.test/Hymns-PD/A-Hymns/Abide-With-Me-Monk.html": page_template.format(
                composer="William Monk", source="monk.mup"
            ).encode(),
            "https://example.test/Hymns-PD/A-Hymns/Abide-With-Me-Troyte.html": page_template.format(
                composer="Arthur Troyte", source="troyte.mup"
            ).encode(),
            "https://example.test/Hymns-PD/A-Hymns/monk.mup": b"// This Mup source code is donated to the public domain.\n",
            "https://example.test/Hymns-PD/A-Hymns/troyte.mup": b"// This Mup source code is donated to the public domain.\n",
        }
        calls: list[str] = []

        def fetch(url: str) -> bytes:
            calls.append(url)
            return responses[url]

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            index_file = root / "source-index.html"
            index_file.write_bytes(index)
            output_root = root / "inventory"
            first = inventory_collection(
                output_root=output_root,
                index_url="https://example.test/Hymns-PD/ZZ-CompletePDHymnList.html",
                index_file=index_file,
                audit_date="2026-08-03",
                fetcher=fetch,
            )
            self.assertEqual(first["summary"], {"pending_conversion": 2})
            self.assertEqual(len(calls), 4)
            self.assertEqual(
                {record["work_id"] for record in first["records"]},
                {"abide-with-me"},
            )
            self.assertEqual(
                len({record["arrangement_id"] for record in first["records"]}),
                2,
            )

            calls.clear()
            second = inventory_collection(
                output_root=output_root,
                index_url="https://example.test/Hymns-PD/ZZ-CompletePDHymnList.html",
                index_file=index_file,
                audit_date="2026-08-03",
                fetcher=fetch,
            )
            self.assertEqual(second["summary"], {"pending_conversion": 2})
            self.assertEqual(calls, [])

    def test_public_domain_index_is_sufficient_when_page_rights_are_blank(self) -> None:
        index = b"""
        <dl><dt><a href="./A-Hymns/Example.html">Example</a></dt></dl>
        """
        page = b"""
        <title>Example</title><table>
          <tr><th>MUP File:</th><td><a href="example.mup">Letter</a></td></tr>
        </table>
        """
        responses = {
            "https://example.test/Hymns-PD/A-Hymns/Example.html": page,
            "https://example.test/Hymns-PD/A-Hymns/example.mup": b"score\n",
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            index_file = root / "index.html"
            index_file.write_bytes(index)
            inventory = inventory_collection(
                output_root=root / "output",
                index_url="https://example.test/Hymns-PD/index.html",
                index_file=index_file,
                fetcher=responses.__getitem__,
            )
        record = inventory["records"][0]
        self.assertEqual(record["disposition"], "pending_conversion")
        self.assertEqual(record["rights_basis"], "complete_public_domain_index")
        self.assertFalse(record["source_code_donation_found"])

    def test_cdx_loader_selects_latest_snapshot_by_url_path(self) -> None:
        rows = [
            ["timestamp", "original", "digest"],
            [
                "20240101000000",
                "http://hymnstogod.org/Hymns-PD/A-Hymns/Example.html",
                "OLD",
            ],
            [
                "20250101000000",
                "https://www.hymnstogod.org/Hymns-PD/A-Hymns/Example.html",
                "NEW",
            ],
        ]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "cdx.json"
            path.write_text(json.dumps(rows), encoding="utf-8")
            snapshots = load_cdx_snapshots([path])

        snapshot = snapshots[("/hymns-pd/a-hymns/example.html", "")]
        self.assertEqual(snapshot.timestamp, "20250101000000")
        self.assertEqual(snapshot.digest, "NEW")
        self.assertIn("20250101000000id_", snapshot.replay_url)

    def test_cached_archive_content_must_match_snapshot_digest(self) -> None:
        data = b"verified archive payload"
        digest = base64.b32encode(hashlib.sha1(data).digest()).decode().rstrip("=")
        retrieval = _verified_retrieval(
            data,
            canonical_url="https://example.test/hymn.mup",
            retrieval={
                "method": "internet_archive_snapshot",
                "archive_digest": digest,
                "url": "https://web.archive.org/example",
            },
            was_cached=True,
        )
        self.assertTrue(retrieval["content_digest_verified"])
        self.assertEqual(retrieval["sha1_base32"], digest)

        drifted = _verified_retrieval(
            b"different payload",
            canonical_url="https://example.test/hymn.mup",
            retrieval={
                "method": "internet_archive_snapshot",
                "archive_digest": digest,
                "url": "https://web.archive.org/example",
            },
            was_cached=True,
        )
        self.assertEqual(drifted["method"], "cached_official_url_content")
        self.assertFalse(drifted["content_digest_verified"])


if __name__ == "__main__":
    unittest.main()

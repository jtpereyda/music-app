from __future__ import annotations

from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
import xml.etree.ElementTree as ET


CATALOG_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CATALOG_ROOT / "scripts"))

from import_openscore_lieder import (  # noqa: E402
    _mode,
    _original_key,
    _source_file,
)


class OpenScoreLiederImportTests(unittest.TestCase):
    def test_source_file_reconciles_upstream_path_drift_by_stable_id(self) -> None:
        source_root = Path(self.enterContext(TemporaryDirectory()))
        actual = source_root / "scores" / "Renamed_Composer" / "lc12345.mxl"
        actual.parent.mkdir(parents=True)
        actual.write_bytes(b"score")

        resolved = _source_file(
            source_root,
            "Old_Composer/Old_Title",
            "12345",
            files_by_id={"12345": actual},
        )

        self.assertEqual(resolved, actual)

    def test_explicit_musicxml_minor_mode_wins(self) -> None:
        root = ET.fromstring(
            "<score-partwise><part><measure><attributes><key>"
            "<fifths>-3</fifths><mode>minor</mode>"
            "</key></attributes></measure></part></score-partwise>"
        )

        mode, analysis = _mode(root, -3)

        self.assertEqual(mode, "minor")
        self.assertEqual(analysis["method"], "musicxml")
        self.assertEqual(_original_key(-3, mode)["name"], "C minor")


if __name__ == "__main__":
    unittest.main()

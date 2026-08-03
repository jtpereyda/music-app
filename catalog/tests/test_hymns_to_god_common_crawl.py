from __future__ import annotations

import base64
import gzip
import hashlib
from pathlib import Path
import sys
import unittest


CATALOG_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CATALOG_ROOT / "scripts"))

from fetch_hymns_to_god_common_crawl import (  # noqa: E402
    CommonCrawlError,
    extract_warc_response,
)


class HymnsToGodCommonCrawlTests(unittest.TestCase):
    def test_verified_warc_response_body_is_extracted(self) -> None:
        body = b"<html>Public Domain - USA</html>"
        digest = base64.b32encode(hashlib.sha1(body).digest()).decode().rstrip("=")
        record = (
            b"WARC/1.0\r\nContent-Type: application/http\r\n\r\n"
            b"HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n"
            + body
        )
        self.assertEqual(extract_warc_response(gzip.compress(record), digest), body)

    def test_payload_digest_drift_fails_closed(self) -> None:
        record = (
            b"WARC/1.0\r\n\r\nHTTP/1.1 200 OK\r\n\r\nbody"
        )
        with self.assertRaisesRegex(CommonCrawlError, "digest mismatch"):
            extract_warc_response(gzip.compress(record), "NOTTHEHASH")


if __name__ == "__main__":
    unittest.main()

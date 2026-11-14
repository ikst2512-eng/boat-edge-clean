"""Synthetic, no-network tests: K receipt is not official result reconciliation."""
import datetime as dt
import io
import tempfile
import unittest
from pathlib import Path

from scripts.research_official_k_receipt import archive_url, collect, get_archive

DAY = dt.date(2026, 8, 1)
FAKE = b"\x30\x00-lh5-" + b"\x00" * 70  # signature only; NOT a decodable LZH


class Response(io.BytesIO):
    def __init__(self, url, data=FAKE, status=200, destination=None):
        super().__init__(data)
        self.url = destination or url
        self.status = status

    def geturl(self):
        return self.url

    def getcode(self):
        return self.status


def opener_ok(request, timeout):
    assert timeout > 0
    return Response(request.full_url)


class OfficialKReceiptTests(unittest.TestCase):
    def test_official_url_and_frozen_period(self):
        self.assertEqual(
            archive_url(DAY),
            "https://www1.mbrace.or.jp/od2/K/202608/k260801.lzh")
        self.assertEqual(
            archive_url(dt.date(2026, 10, 31)),
            "https://www1.mbrace.or.jp/od2/K/202610/k261031.lzh")
        with self.assertRaisesRegex(ValueError, "date_outside"):
            archive_url(dt.date(2026, 11, 1))

    def test_receipt_never_implies_official_reconciliation(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            result = collect(DAY, DAY, root, opener=opener_ok)
            self.assertEqual(len(result["receipts"]), 1)
            self.assertFalse(result["eligible_for_prediction"])
            self.assertEqual(result["official_primary_rows_decoded"], 0)
            self.assertEqual(result["official_primary_rows_reconciled"], 0)
            self.assertTrue((root / "k260801.lzh").exists())
            self.assertEqual(
                get_archive(DAY, root, opener=opener_ok)["bytes"], len(FAKE))

    def test_rejects_html_and_short_payload(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            with self.assertRaisesRegex(ValueError, "invalid_lzh"):
                get_archive(
                    DAY, root,
                    opener=lambda req, timeout: Response(req.full_url, b"<html>"))
            self.assertFalse((root / "k260801.lzh").exists())

    def test_rejects_redirect_and_http_error(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            with self.assertRaisesRegex(ValueError, "unexpected_redirect"):
                get_archive(
                    DAY, root,
                    opener=lambda req, timeout: Response(
                        req.full_url, destination="https://example.com/"))
            with self.assertRaisesRegex(ValueError, "http_status"):
                get_archive(
                    DAY, root,
                    opener=lambda req, timeout: Response(req.full_url, status=404))

    def test_no_overwrite_of_conflicting_existing_archive(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "k260801.lzh").write_bytes(b"other")
            with self.assertRaisesRegex(ValueError, "conflicting_existing_archive"):
                get_archive(DAY, root, opener=opener_ok)
            self.assertEqual((root / "k260801.lzh").read_bytes(), b"other")

    def test_reversed_period_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaisesRegex(ValueError, "invalid_date_order"):
                collect(dt.date(2026, 8, 2), DAY, Path(td), opener=opener_ok)


if __name__ == "__main__":
    unittest.main()

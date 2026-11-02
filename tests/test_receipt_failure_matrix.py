"""Independent failure-injection checks for immutable receipt publication."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.publish_official_receipt import publish_receipt
from scripts.capture_official_beforeinfo_json import capture as capture_before
from scripts.capture_official_odds_receipt import capture as capture_odds


class FailureMatrixTests(unittest.TestCase):
    def test_rename_failure_does_not_publish_and_retry_succeeds(self):
        with tempfile.TemporaryDirectory() as root:
            dest = Path(root) / "observations" / "test"
            with patch("scripts.publish_official_receipt.os.rename", side_effect=OSError("storage unavailable")):
                with self.assertRaises(OSError):
                    publish_receipt(dest, "original.html", b"original", {"status": "observed"})
            self.assertFalse(dest.exists())
            self.assertFalse(list(dest.parent.glob(".receipt-*")))
            publish_receipt(dest, "original.html", b"verified", {"status": "observed"})
            self.assertEqual((dest / "original.html").read_bytes(), b"verified")
            with self.assertRaises(FileExistsError):
                publish_receipt(dest, "original.html", b"duplicate", {})

    def test_timeout_does_not_publish_either_source(self):
        with tempfile.TemporaryDirectory() as root:
            race = "202611021512"
            def timeout(_):
                raise TimeoutError("simulated network timeout")
            before = capture_before(race, root, "beforetimeout", fetch=timeout)
            odds = capture_odds(race, "2026-11-02T20:36:00+09:00", root, "oddstimeout", fetch=timeout)
            self.assertEqual(before["status"], "official_json_probe_failed")
            self.assertEqual(odds["status"], "official_odds_probe_failed")
            for receipt in (before, odds):
                self.assertFalse(receipt["forecast_usable"])
                self.assertFalse(receipt["t12_eligible"])
            self.assertFalse(list(Path(root).rglob("manifest.json")))
            self.assertFalse(list(Path(root).rglob("original.html")))
            self.assertFalse(list(Path(root).rglob("beforeinfo.json")))

    def test_incomplete_manifest_not_counted_as_archival_evidence(self):
        with tempfile.TemporaryDirectory() as root:
            dest = Path(root) / "incomplete"
            dest.mkdir()
            (dest / "original.html").write_bytes(b"source")
            from scripts.audit_joint_official_receipts import audit_pair
            with self.assertRaises((OSError, ValueError, KeyError)):
                audit_pair(dest, dest)


if __name__ == "__main__":
    unittest.main()

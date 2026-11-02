import json
import tempfile
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path
from scripts.capture_official_racelist_receipt import capture
from scripts.audit_official_racelist_receipt import audit_racelist

RACE = "202611031201"
JST = timezone(timedelta(hours=9))


class AuditRacelistReceiptTests(unittest.TestCase):
    def make(self, root):
        times = iter((datetime(2026,11,3,10,0,tzinfo=JST), datetime(2026,11,3,10,0,1,tzinfo=JST)))
        result = capture(RACE, root, "proof", fetch=lambda _: b"<!doctype html><html><body>fixture</body></html>", clock=lambda: next(times))
        self.assertEqual(result["status"], "official_racelist_html_observed_research_only")
        return Path(root) / "observations" / "proof" / "20261103" / RACE

    def test_valid_original_is_not_six_racer_or_entry_proof(self):
        with tempfile.TemporaryDirectory() as root:
            directory = self.make(root)
            report = audit_racelist(directory, RACE, "2026-11-03T10:05:00+09:00")
            self.assertTrue(report["original_hash_verified"])
            self.assertTrue(report["received_by_t12"])
            self.assertFalse(report["six_racers_verified"])
            self.assertFalse(report["entry_verified"])
            self.assertFalse(report["full_t12_source_certified"])

    def test_late_receipt_is_not_t12(self):
        with tempfile.TemporaryDirectory() as root:
            directory = self.make(root)
            report = audit_racelist(directory, RACE, "2026-11-03T09:59:00+09:00")
            self.assertFalse(report["received_by_t12"])

    def test_tampered_original_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            directory = self.make(root)
            (directory / "racelist.html").write_bytes(b"<html>tampered</html>")
            with self.assertRaisesRegex(ValueError, "source bytes mismatch"):
                audit_racelist(directory, RACE, "2026-11-03T10:05:00+09:00")

    def test_wrong_origin_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            directory = self.make(root)
            path = directory / "manifest.json"
            manifest = json.loads(path.read_text())
            manifest["official_url"] = "https://example.com"
            path.write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError, "source identity mismatch"):
                audit_racelist(directory, RACE, "2026-11-03T10:05:00+09:00")

    def test_reversed_or_non_jst_time_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            directory = self.make(root)
            path = directory / "manifest.json"
            manifest = json.loads(path.read_text())
            manifest["received_at_jst"] = "2026-11-03T00:00:00+00:00"
            path.write_text(json.dumps(manifest))
            with self.assertRaises(ValueError):
                audit_racelist(directory, RACE, "2026-11-03T10:05:00+09:00")

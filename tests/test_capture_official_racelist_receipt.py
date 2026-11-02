import hashlib
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from scripts.capture_official_racelist_receipt import capture

RACE = "202611031201"
JST = timezone(timedelta(hours=9))


class RacelistReceiptTests(unittest.TestCase):
    def clock(self):
        values = iter((datetime(2026, 11, 3, 10, 0, tzinfo=JST),
                       datetime(2026, 11, 3, 10, 0, 1, tzinfo=JST)))
        return lambda: next(values)

    def test_original_html_immutable_and_not_certified(self):
        raw = b"<!doctype html><html><body>unparsed</body></html>"
        with tempfile.TemporaryDirectory() as root:
            result = capture(RACE, root, "proof01", fetch=lambda url: raw, clock=self.clock())
            self.assertEqual(result["status"], "official_racelist_html_observed_research_only")
            self.assertEqual(result["sha256"], hashlib.sha256(raw).hexdigest())
            self.assertFalse(result["entry_verified"])
            self.assertFalse(result["racecard_content_verified"])
            self.assertFalse(result["t12_eligible"])
            folder = Path(root) / "observations" / "proof01" / "20261103" / RACE
            self.assertEqual((folder / "racelist.html").read_bytes(), raw)
            manifest = json.loads((folder / "manifest.json").read_text())
            self.assertEqual(manifest["sha256"], result["sha256"])
            with self.assertRaises(FileExistsError):
                capture(RACE, root, "proof01", fetch=lambda url: raw, clock=self.clock())

    def test_json_disguised_as_html_is_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            result = capture(RACE, root, "bad01", fetch=lambda url: b'{"error":true}', clock=self.clock())
            self.assertEqual(result["status"], "official_racelist_probe_failed")
            self.assertFalse(result["forecast_usable"])
            self.assertFalse((Path(root) / "observations" / "bad01").exists())

    def test_invalid_race_identity_rejected(self):
        with self.assertRaises(ValueError):
            capture("202611039901", "/tmp", "invalid", fetch=lambda url: b"<html></html>")

import tempfile
import json
from pathlib import Path
from datetime import datetime, timedelta
from official_prerace_capture import capture_beforeinfo, JST
import unittest
from unittest.mock import patch
from run_official_prerace_probe import run


class ProbeRunnerTests(unittest.TestCase):
    def test_invalid_deadline_rejected_without_network(self):
        with patch("run_official_prerace_probe.capture_beforeinfo") as capture:
            with tempfile.TemporaryDirectory() as directory:
                for bad in ("not-a-date", "2026-10-27T15:00:00", "2026-10-27T06:00:00+00:00", "2026-10-27T15:00:00+08:00"):
                    with self.assertRaises(ValueError):
                        run("20261027-12-01", bad, directory)
            capture.assert_not_called()

    def test_real_archive_roundtrip_with_mocked_transport(self):
        """Exercise real hashing, archival, readback and diagnosis without network."""
        now = datetime(2026, 10, 27, 14, 50, tzinfo=JST)
        deadline = now + timedelta(minutes=10)
        class Response:
            status = 200
            headers = {"Content-Type": "text/html"}
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def read(self, size):
                return "<html><body><h3>展示タイム</h3></body></html>".encode("utf-8")
        def capture(key, cutoff):
            return capture_beforeinfo(key, cutoff, now=now, completed_at=now,
                                      opener=lambda *args, **kwargs: Response())
        with patch("run_official_prerace_probe.capture_beforeinfo", side_effect=capture):
            with tempfile.TemporaryDirectory() as directory:
                result = run("20261027-12-01", deadline.isoformat(), directory)
                evidence = list(Path(directory).iterdir())
                self.assertEqual({p.suffix for p in evidence}, {".html", ".json", ".complete"})
                self.assertEqual(len(evidence), 4)
                manifest = Path(directory) / ("20261027-12-01-" + result["receipt_sha256"] + ".manifest.json")
                self.assertEqual(json.loads(manifest.read_text()), result)
                self.assertEqual(result["deadline"], deadline.isoformat())
                self.assertEqual(result["fetched_at"], now.isoformat())
                self.assertEqual(result["diagnostic"]["status"], "inspection_only")
                self.assertTrue(result["diagnostic"]["sections_present"]["exhibition_time"])
                self.assertFalse(result["diagnostic"]["verified_preview"])

    def test_rejects_unexpected_promoted_diagnostic(self):
        with patch("run_official_prerace_probe.capture_beforeinfo", return_value=({"sha256": "a" * 64}, b"html")), \
             patch("run_official_prerace_probe.save_raw_receipt", return_value=[]), \
             patch("run_official_prerace_probe.read_raw_receipt"), \
             patch("run_official_prerace_probe.inspect_saved_beforeinfo", return_value={
                 "race_key": "20261027-12-01", "status": "inspection_only",
                 "verified_preview": True, "actual_entry_verified": False,
                 "racers": [], "start_exhibition": []}):
            with tempfile.TemporaryDirectory() as directory:
                with self.assertRaises(ValueError):
                    run("20261027-12-01", "2026-10-27T15:00:00+09:00", directory)
                self.assertEqual(list(Path(directory).iterdir()), [])

    def test_evidence_is_not_reported_as_verified(self):
        with patch("run_official_prerace_probe.capture_beforeinfo", return_value=({"sha256": "a" * 64, "source": "https://www.boatrace.jp/owpc/pc/race/beforeinfo?hd=20261027&jcd=12&rno=1", "fetched_at": "2026-10-27T14:55:00+09:00"}, b"html")), \
             patch("run_official_prerace_probe.save_raw_receipt", return_value=["/tmp/probe.html", "/tmp/probe.json"]), \
             patch("run_official_prerace_probe.read_raw_receipt"), \
             patch("run_official_prerace_probe.inspect_saved_beforeinfo", return_value={"verified_preview": False, "actual_entry_verified": False, "race_key": "20261027-12-01", "racers": [], "start_exhibition": [], "status": "inspection_only"}):
            with tempfile.TemporaryDirectory() as directory:
                result = run("20261027-12-01", "2026-10-27T15:00:00+09:00", directory)
                manifest = Path(directory) / ("20261027-12-01-" + "a" * 64 + ".manifest.json")
                self.assertTrue(manifest.exists())
                self.assertEqual(json.loads(manifest.read_text()), result)
        self.assertEqual(result["status"], "unverified_raw_only")
        self.assertFalse(result["diagnostic"]["verified_preview"])


if __name__ == "__main__":
    unittest.main()

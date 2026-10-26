import tempfile
import unittest
from unittest.mock import patch
from run_official_prerace_probe import run


class ProbeRunnerTests(unittest.TestCase):
    def test_invalid_deadline_rejected_without_network(self):
        with patch("run_official_prerace_probe.capture_beforeinfo") as capture:
            with tempfile.TemporaryDirectory() as directory:
                for bad in ("not-a-date", "2026-10-27T15:00:00"):
                    with self.assertRaises(ValueError):
                        run("20261027-12-01", bad, directory)
            capture.assert_not_called()

    def test_evidence_is_not_reported_as_verified(self):
        with patch("run_official_prerace_probe.capture_beforeinfo", return_value=({"sha256": "a" * 64}, b"html")), \
             patch("run_official_prerace_probe.save_raw_receipt", return_value=["/tmp/probe.html", "/tmp/probe.json"]), \
             patch("run_official_prerace_probe.read_raw_receipt"), \
             patch("run_official_prerace_probe.inspect_saved_beforeinfo", return_value={"verified_preview": False, "status": "inspection_only"}):
            result = run("20261027-12-01", "2026-10-27T15:00:00+09:00", "/tmp")
        self.assertEqual(result["status"], "unverified_raw_only")
        self.assertFalse(result["diagnostic"]["verified_preview"])


if __name__ == "__main__":
    unittest.main()

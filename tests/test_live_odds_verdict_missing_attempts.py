"""Regression tests for fail-closed unattended odds verdict on broken artifacts."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from check_live_odds_probe_verdict import verdict


class TestMalformedOddsEvidence(unittest.TestCase):
    def setUp(self):
        self.base = {"source_status": "ok", "checked_at_jst": "2026-11-04T16:25:00+09:00"}

    def test_missing_attempts_fails_closed(self):
        self.assertEqual(verdict({**self.base, "samples": [{"race_code": "202611042212"}]}),
                         "no_valid_200")

    def test_null_attempts_fails_closed(self):
        self.assertEqual(verdict({**self.base, "samples": [{"race_code": "202611042212", "attempts": None}]}),
                         "no_valid_200")

    def test_empty_attempts_fails_closed(self):
        self.assertEqual(verdict({**self.base, "samples": [{"race_code": "202611042212", "attempts": []}]}),
                         "no_valid_200")

    def test_complete_timestamped_200_still_valid(self):
        self.assertEqual(verdict({
            **self.base,
            "samples": [{"race_code": "202611042212", "attempts": [{
                "state": "valid_200", "http": 200, "latency_ms": 20,
                "started_at_utc": "2026-11-04T07:25:01Z",
                "finished_at_utc": "2026-11-04T07:25:02Z",
            }]}],
        }), "valid_200_observed")


if __name__ == "__main__":
    unittest.main()

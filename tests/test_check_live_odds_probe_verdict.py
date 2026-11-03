"""Operational verdict must never equate a green job with a valid odds sample."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from check_live_odds_probe_verdict import verdict


class OddsOperationalVerdictTests(unittest.TestCase):
    @staticmethod
    def sample(state, http):
        return {"race_code": "202611030111",
                "attempts": [{"http": http, "state": state, "latency_ms": 44}]}

    def test_healthy_saved_response(self):
        self.assertEqual(verdict({"source_status": "ok",
                                  "samples": [self.sample("valid_200", 200)]}),
                         "valid_200_observed")

    def test_initial_timeout_then_valid_200_is_operational_success(self):
        sample = {"race_code": "202611030111", "attempts": [
            {"http": None, "state": "transport_error:TimeoutError",
             "latency_ms": 25000},
            {"http": 200, "state": "valid_200", "latency_ms": 300}]}
        self.assertEqual(verdict({"source_status": "ok", "samples": [sample]}),
                         "valid_200_observed")
        sample["attempts"].insert(0, {"http": 202, "state": "pending_202",
                                      "latency_ms": 100})
        self.assertEqual(verdict({"source_status": "ok", "samples": [sample]}),
                         "no_valid_200")

    def test_no_sample_and_unavailable_source_are_not_green(self):
        self.assertEqual(verdict({"source_status": "ok", "samples": []}),
                         "no_eligible_races")
        self.assertEqual(verdict({"source_status": "unavailable:URLError",
                                  "samples": [self.sample("valid_200", 200)]}),
                         "source_unavailable")
        self.assertEqual(verdict({"source_status": "fallback_ineligible",
                                  "samples": []}), "source_unavailable")

    def test_pending_or_invalid_response_are_not_green(self):
        for state, http in (("pending_202", 202), ("invalid_200", 200),
                            ("valid_200", 202)):
            self.assertEqual(verdict({"source_status": "ok",
                                      "samples": [self.sample(state, http)]}),
                             "no_valid_200")

    def test_valid_response_among_multiple_samples(self):
        self.assertEqual(verdict({"source_status": "ok", "samples": [
            self.sample("pending_202", 202), self.sample("valid_200", 200)]}),
                         "valid_200_observed")


if __name__ == "__main__":
    unittest.main()

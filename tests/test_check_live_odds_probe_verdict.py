"""Operational verdict requires actual timed HTTP 200, unlike historical legacy reports."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from check_live_odds_probe_verdict import verdict

CHECKED = "2026-11-03T12:00:00+09:00"


def attempt(state, http, start="2026-11-03T03:00:01+00:00",
            end="2026-11-03T03:00:02+00:00", latency=44):
    return {"http": http, "state": state, "latency_ms": latency,
            "started_at_utc": start, "finished_at_utc": end}


def record(samples, status="ok", checked=CHECKED):
    return {"source_status": status, "checked_at_jst": checked, "samples": samples}


class OddsOperationalVerdictTests(unittest.TestCase):
    @staticmethod
    def sample(state, http):
        return {"race_code": "202611030111", "attempts": [attempt(state, http)]}

    def test_healthy_saved_response(self):
        self.assertEqual(verdict(record([self.sample("valid_200", 200)])),
                         "valid_200_observed")

    def test_initial_timeout_then_valid_200_is_operational_success(self):
        sample = {"race_code": "202611030111", "attempts": [
            attempt("transport_error:TimeoutError", None,
                    end="2026-11-03T03:00:26+00:00", latency=25000),
            attempt("valid_200", 200,
                    start="2026-11-03T03:00:28+00:00",
                    end="2026-11-03T03:00:29+00:00", latency=300)]}
        self.assertEqual(verdict(record([sample])), "valid_200_observed")
        sample["attempts"].insert(0, attempt("pending_202", 202, latency=100))
        self.assertEqual(verdict(record([sample])), "no_valid_200")

    def test_no_sample_and_unavailable_source_are_not_green(self):
        self.assertEqual(verdict(record([])), "no_eligible_races")
        self.assertEqual(verdict(record([self.sample("valid_200", 200)],
                                        status="unavailable:URLError")), "source_unavailable")
        self.assertEqual(verdict(record([], status="fallback_ineligible")),
                         "source_unavailable")

    def test_pending_or_invalid_response_are_not_green(self):
        for state, http in (("pending_202", 202), ("invalid_200", 200),
                            ("valid_200", 202)):
            self.assertEqual(verdict(record([self.sample(state, http)])), "no_valid_200")

    def test_valid_response_among_multiple_samples(self):
        self.assertEqual(verdict(record([
            self.sample("pending_202", 202), self.sample("valid_200", 200)])),
                         "valid_200_observed")

    def test_legacy_untimestamped_http200_cannot_certify_unattended_recovery(self):
        legacy = {"race_code": "202611030111",
                  "attempts": [{"http": 200, "state": "valid_200", "latency_ms": 44}]}
        self.assertEqual(verdict(record([legacy])), "no_valid_200")
        self.assertEqual(verdict(record([legacy, self.sample("valid_200", 200)])),
                         "valid_200_observed")

    def test_partial_timestamps_or_missing_run_clock_fail_closed(self):
        sample = self.sample("valid_200", 200)
        del sample["attempts"][0]["finished_at_utc"]
        self.assertEqual(verdict(record([sample])), "no_valid_200")
        self.assertEqual(verdict(record([self.sample("valid_200", 200)], checked=None)),
                         "no_valid_200")

    def test_missing_null_or_empty_attempts_fail_closed(self):
        for missing in ({}, {"attempts": None}, {"attempts": []}):
            bad_sample = {"race_code": "202611030111", **missing}
            self.assertEqual(verdict(record([bad_sample])), "no_valid_200")
            self.assertEqual(verdict(record([bad_sample, self.sample("valid_200", 200)])),
                             "valid_200_observed")

    def test_out_of_run_timestamps_fail_closed(self):
        self.assertEqual(verdict(record([self.sample("valid_200", 200)],
                                        checked="2026-11-04T12:00:00+09:00")),
                         "no_valid_200")


if __name__ == "__main__":
    unittest.main()

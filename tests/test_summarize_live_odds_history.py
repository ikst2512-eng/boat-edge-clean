"""Unit tests for 14-day live odds trend: exact denominators and no fabricated history."""
import importlib.util
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "history", Path(__file__).resolve().parents[1] / "scripts/summarize_live_odds_history.py"
)
history = importlib.util.module_from_spec(spec)
spec.loader.exec_module(history)


def race(code, states, elapsed=800):
    codes = {"valid_200": 200, "pending_202": 202, "http_error": 503,
             "invalid_200": 200, "transport_error:TimeoutError": None}
    return {"race_code": code, "attempts": [
        {"http": codes.get(state), "state": state, "latency_ms": 100 * (i+1)}
        for i, state in enumerate(states)], "elapsed_ms": elapsed}


class OddsHistoryTests(unittest.TestCase):
    def test_count_valid_pending_recovered_and_errors_without_duplicating(self):
        data = [
            {"source_status": "ok", "checked_at_jst": "2026-11-03T12:25:00+09:00",
             "samples": [race("202611030111", ["valid_200"]),
                         race("202611030112", ["pending_202", "valid_200"], 2300),
                         race("202611030113", ["pending_202", "pending_202", "pending_202"], 4500)]},
            {"source_status": "ok", "checked_at_jst": "2026-11-03T14:25:00+09:00",
             "samples": [race("202611030111", ["http_error"]),
                         race("202611030114", ["invalid_200"])]},
            {"source_status": "ok", "checked_at_jst": "2026-11-03T12:25:00+09:00",
             "samples": [race("202611030111", ["valid_200"])]},
        ]
        m = history.summarize(data)
        self.assertEqual(m["race_observations"], 5)
        self.assertEqual(m["unique_races"], 4)
        self.assertEqual(m["runs_with_eligible_observations"], 2)
        self.assertEqual(m["requests"], 8)
        self.assertEqual(m["http_200"], 3)
        self.assertEqual(m["http_202"], 4)
        self.assertEqual(m["http_503"], 1)
        self.assertEqual(m["first_attempt_valid_races"], 1)
        self.assertEqual(m["eventual_valid_races"], 2)
        self.assertEqual(m["eventual_valid_rate_pct"], 40.0)
        self.assertEqual(m["initially_pending_races"], 2)
        self.assertEqual(m["pending_recovered"], 1)
        self.assertEqual(m["pending_recovery_rate_pct"], 50.0)

    def test_no_observations_is_not_success(self):
        m = history.summarize([{"source_status": "no_upcoming_race", "checked_at_jst": "x", "samples": []}])
        self.assertEqual(m["race_observations"], 0)
        self.assertIsNone(m["eventual_valid_rate_pct"])
        self.assertIsNone(m["pending_recovery_rate_pct"])
        self.assertIsNone(m["median_request_latency_ms"])

    def test_exclude_invalid_evidence(self):
        m = history.summarize([{"source_status": "ok", "checked_at_jst": "2026-11-03T14:25:00+09:00",
                                "samples": [race("bad", ["valid_200"]),
                                            race("202611030111", ["fake_success"])]}])
        self.assertEqual(m["race_observations"], 0)

    def test_first_200_does_not_count_as_recovery(self):
        m = history.summarize([{"source_status": "ok", "checked_at_jst": "2026-11-03T14:25:00+09:00",
                                "samples": [race("202611030111", ["valid_200"])]}])
        self.assertEqual(m["eventual_valid_races"], 1)
        self.assertEqual(m["pending_recovered"], 0)
        self.assertIsNone(m["pending_recovery_rate_pct"])


if __name__ == "__main__":
    unittest.main()

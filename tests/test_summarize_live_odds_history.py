"""Unit tests for 14-day live odds trend: exact denominators and no fabricated history."""
import importlib.util
import io
import json
import unittest
import zipfile
from datetime import datetime, timezone
from unittest.mock import patch
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

    def test_daily_trend_missing_days_are_not_successes(self):
        from datetime import timezone, timedelta
        jst = timezone(timedelta(hours=9))
        now = datetime(2026, 11, 3, 14, 0, tzinfo=jst)
        data = [
            {"source_status": "ok", "checked_at_jst": "2026-11-03T12:25:00+09:00",
             "samples": [race("202611030111", ["valid_200"]),
                         race("202611030112", ["pending_202", "valid_200"])]},
            {"source_status": "ok", "checked_at_jst": "2026-11-02T14:25:00+09:00",
             "samples": [race("202611020111", ["pending_202", "pending_202", "pending_202"])]},
            {"source_status": "ok", "checked_at_jst": "2026-10-01T14:25:00+09:00",
             "samples": [race("202610010111", ["valid_200"])]},
        ]
        rows = history.daily_trends(data, now=now)
        self.assertEqual(len(rows), 14)
        self.assertEqual(rows[-1]["date_jst"], "2026-11-03")
        self.assertEqual(rows[-1]["valid_rate_pct"], 100.0)
        self.assertEqual(rows[-1]["pending_recovery_rate_pct"], 100.0)
        self.assertEqual(rows[-2]["date_jst"], "2026-11-02")
        self.assertEqual(rows[-2]["valid_rate_pct"], 0.0)
        self.assertEqual(rows[-2]["pending_recovery_rate_pct"], 0.0)
        self.assertEqual(sum(row["has_valid_observations"] for row in rows), 2)
        self.assertIsNone(rows[0]["valid_rate_pct"])
        self.assertIsNone(rows[0]["pending_recovery_rate_pct"])

    def test_daily_trend_rejects_naive_future_and_invalid_timestamps(self):
        from datetime import timezone, timedelta
        jst = timezone(timedelta(hours=9))
        now = datetime(2026, 11, 3, 14, 0, tzinfo=jst)
        rows = history.daily_trends([
            {"source_status": "ok", "checked_at_jst": "2026-11-04T12:25:00+09:00",
             "samples": [race("202611040111", ["valid_200"])]},
            {"source_status": "ok", "checked_at_jst": "2026-11-03T12:25:00",
             "samples": [race("202611030111", ["valid_200"])]},
            {"source_status": "ok", "checked_at_jst": "invalid",
             "samples": [race("202611030112", ["valid_200"])]},
        ], now=now)
        self.assertTrue(all(not row["has_valid_observations"] for row in rows))

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

    def test_load_prior_scheduled_artifact_from_zip(self):
        record = {"checked_at_jst": "2026-11-03T13:00:00+09:00", "source_status": "ok",
                  "samples": [race("202611030111", ["valid_200"])]}
        archive_bytes = io.BytesIO()
        with zipfile.ZipFile(archive_bytes, "w") as zf:
            zf.writestr(history.FILE, json.dumps(record))
        fake_run = {"id": 42, "event": "schedule", "conclusion": "success",
                    "created_at": "2026-11-03T04:00:00Z"}
        def fake_api(url, token):
            if "/runs?status=" in url:
                return {"workflow_runs": [fake_run]}
            return {"artifacts": [{"name": history.ARTIFACT, "id": 7, "expired": False}]}
        with patch.object(history, "api_json", side_effect=fake_api), patch.object(
                history, "urlopen", return_value=io.BytesIO(archive_bytes.getvalue())):
            rows, selected, errors = history.fetch_history(
                "ikst2512-eng/boat-edge-clean", "fake", {"source_status": "no_upcoming_race", "samples": []},
                now=datetime(2026, 11, 3, 5, 0, tzinfo=timezone.utc))
        self.assertEqual(selected, 1)
        self.assertEqual(errors, [])
        self.assertEqual(len(rows), 2)
        self.assertEqual(history.summarize(rows)["eventual_valid_races"], 1)

    def test_invalid_same_race_run_does_not_inflate_eligible_runs(self):
        code = "202611030111"
        rows = [
            {"source_status": "ok", "checked_at_jst": "2026-11-03T12:25:00+09:00",
             "samples": [race(code, ["valid_200"])]},
            {"source_status": "ok", "checked_at_jst": "2026-11-03T14:25:00+09:00",
             "samples": [race(code, ["fake_success"])]},
        ]
        result = history.summarize(rows)
        self.assertEqual(result["runs_with_eligible_observations"], 1)
        self.assertEqual(result["race_observations"], 1)

    def test_all_42_scheduled_runs_are_inside_history_capacity(self):
        self.assertGreaterEqual(history.MAX_RUNS, 42)

    def test_reject_http_status_and_retry_state_contradictions(self):
        code = "202611030111"
        valid = race(code, ["valid_200"])
        mismatched = race("202611030112", ["valid_200"])
        mismatched["attempts"][0]["http"] = 202
        impossible = race("202611030113", ["valid_200", "pending_202"])
        transport = race("202611030114", ["transport_error:TimeoutError"])
        transport["attempts"][0]["http"] = 200
        false_pending = race("202611030115", ["pending_202"])
        false_pending["attempts"][0]["http"] = 200
        rows = [{"source_status": "ok", "checked_at_jst": "2026-11-03T14:25:00+09:00",
                 "samples": [valid, mismatched, impossible, transport, false_pending]}]
        m = history.summarize(rows)
        self.assertEqual(m["race_observations"], 1)
        self.assertEqual(m["eventual_valid_races"], 1)
        self.assertEqual(m["http_202"], 0)
        self.assertEqual(m["http_200"], 1)

    def test_valid_pending_recovery_and_http_error_still_count(self):
        rows = [{"source_status": "ok", "checked_at_jst": "2026-11-03T14:25:00+09:00",
                 "samples": [race("202611030111", ["pending_202", "valid_200"]),
                             race("202611030112", ["http_error"]),
                             race("202611030113", ["transport_error:TimeoutError"])]}]
        m = history.summarize(rows)
        self.assertEqual(m["race_observations"], 3)
        self.assertEqual(m["pending_recovered"], 1)
        self.assertEqual(m["other_http_or_transport"], 1)
        self.assertEqual(m["http_503"], 1)

    def test_first_200_does_not_count_as_recovery(self):
        m = history.summarize([{"source_status": "ok", "checked_at_jst": "2026-11-03T14:25:00+09:00",
                                "samples": [race("202611030111", ["valid_200"])]}])
        self.assertEqual(m["eventual_valid_races"], 1)
        self.assertEqual(m["pending_recovered"], 0)
        self.assertIsNone(m["pending_recovery_rate_pct"])


if __name__ == "__main__":
    unittest.main()

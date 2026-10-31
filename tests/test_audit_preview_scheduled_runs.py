import unittest
from datetime import datetime, timezone, date
from scripts.audit_preview_scheduled_runs import summarize, daily_capture_health

NOW = datetime(2026, 11, 1, 15, 0, tzinfo=timezone.utc)

class ScheduledCaptureAuditTests(unittest.TestCase):
    def test_no_runs(self):
        result = summarize([], now=NOW)
        self.assertEqual(result["scheduled_last_24h"], 0)
        self.assertEqual(result["schedule_health"], "no_scheduled_run_in_last_24h")

    def test_stale_and_manual_runs_do_not_count(self):
        rows = [
            {"event": "schedule", "created_at": "2026-10-30T12:00:00Z", "status": "completed", "conclusion": "success"},
            {"event": "workflow_dispatch", "created_at": "2026-11-01T14:00:00Z", "status": "completed", "conclusion": "success"},
        ]
        result = summarize(rows, now=NOW)
        self.assertEqual(result["scheduled_runs"], 1)
        self.assertEqual(result["scheduled_last_24h"], 0)

    def test_recent_scheduled_run(self):
        rows = [{"event": "schedule", "created_at": "2026-11-01T14:00:00Z", "status": "completed", "conclusion": "success"}]
        result = summarize(rows, now=NOW)
        self.assertEqual(result["scheduled_last_24h"], 1)
        self.assertEqual(result["schedule_health"], "recent_scheduled_run_observed")

    def test_recent_failure_is_not_counted_as_success(self):
        rows = [
            {"event":"schedule", "created_at":"2026-11-01T13:00:00Z",
             "status":"completed", "conclusion":"failure"},
            {"event":"schedule", "created_at":"2026-11-01T14:00:00Z",
             "status":"completed", "conclusion":"success"},
            {"event":"workflow_dispatch", "created_at":"2026-11-01T14:30:00Z",
             "status":"completed", "conclusion":"success"},
        ]
        result = summarize(rows, now=NOW)
        self.assertEqual(result["scheduled_last_24h"], 2)
        self.assertEqual(result["successful_scheduled_last_24h"], 1)
        self.assertEqual(result["failed_scheduled_last_24h"], 1)

    def test_nightly_no_scheduled_capture_fails(self):
        rows=[{"event":"workflow_dispatch","created_at":"2026-11-01T12:00:00Z","status":"completed","conclusion":"success"}]
        result=daily_capture_health(rows,date(2026,11,1),True)
        self.assertTrue(result["schedule_missing_today"])
        self.assertFalse(result["all_today_captures_failed"])

    def test_nightly_all_scheduled_captures_failed(self):
        rows=[{"event":"schedule","created_at":"2026-11-01T02:00:00Z","status":"completed","conclusion":"failure"},
              {"event":"schedule","created_at":"2026-11-01T04:00:00Z","status":"completed","conclusion":"failure"}]
        result=daily_capture_health(rows,date(2026,11,1),True)
        self.assertEqual(result["today_scheduled_runs"],2)
        self.assertTrue(result["all_today_captures_failed"])

    def test_one_success_prevents_all_failed_alarm(self):
        rows=[{"event":"schedule","created_at":"2026-11-01T02:00:00Z","status":"completed","conclusion":"failure"},
              {"event":"schedule","created_at":"2026-11-01T03:00:00Z","status":"completed","conclusion":"success"}]
        self.assertFalse(daily_capture_health(rows,date(2026,11,1),True)["all_today_captures_failed"])
        self.assertFalse(daily_capture_health([],date(2026,11,1),False)["schedule_missing_today"])

    def test_invalid_timestamps_not_recent(self):
        result = summarize([{"event":"schedule", "created_at":"invalid"}], now=NOW)
        self.assertEqual(result["scheduled_last_24h"], 0)

if __name__ == "__main__":
    unittest.main()

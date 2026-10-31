import unittest
from datetime import datetime, timezone
from scripts.audit_preview_scheduled_runs import summarize

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

    def test_invalid_timestamps_not_recent(self):
        result = summarize([{"event":"schedule", "created_at":"invalid"}], now=NOW)
        self.assertEqual(result["scheduled_last_24h"], 0)

if __name__ == "__main__":
    unittest.main()

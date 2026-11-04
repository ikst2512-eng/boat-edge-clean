import unittest
from datetime import datetime, timezone, date, timedelta
from scripts.audit_preview_scheduled_runs import summarize, daily_capture_health, capture_window_health, audit_target_day

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

    def test_real_off_window_success_does_not_prove_daytime_capture(self):
        rows=[{"id":41880259578,"event":"schedule",
               "created_at":"2026-11-04T17:45:45Z",
               "run_started_at":"2026-11-04T17:45:45Z",
               "status":"completed","conclusion":"success"}]
        result=capture_window_health(rows,date(2026,11,5),True)
        self.assertEqual(result["today_in_nominal_window_run_ids"],[])
        self.assertEqual(result["today_outside_nominal_window_run_ids"],[41880259578])
        self.assertTrue(result["no_in_window_capture_start_today"])
        self.assertFalse(result["window_check_is_t12_evidence"])

    def test_valid_daytime_start_excludes_manual_and_other_day(self):
        rows=[
            {"id":101,"event":"schedule","created_at":"2026-11-04T23:08:00Z",
             "run_started_at":"2026-11-04T23:08:00Z"},
            {"id":102,"event":"workflow_dispatch","created_at":"2026-11-04T23:09:00Z",
             "run_started_at":"2026-11-04T23:09:00Z"},
            {"id":103,"event":"schedule","created_at":"2026-11-03T23:08:00Z",
             "run_started_at":"2026-11-03T23:08:00Z"},
        ]
        result=capture_window_health(rows,date(2026,11,5),True)
        self.assertEqual(result["today_in_nominal_window_run_ids"],[101])
        self.assertEqual(result["today_outside_nominal_window_run_ids"],[])
        self.assertFalse(result["no_in_window_capture_start_today"])

    def test_missing_or_reversed_start_cannot_prove_daytime(self):
        rows=[
            {"id":201,"event":"schedule","created_at":"2026-11-04T23:08:00Z"},
            {"id":202,"event":"schedule","created_at":"2026-11-04T23:08:00Z",
             "run_started_at":"2026-11-04T23:07:00Z"},
            {"id":203,"event":"schedule","created_at":"2026-11-04T23:08:00Z",
             "run_started_at":"invalid"},
        ]
        result=capture_window_health(rows,date(2026,11,5),True)
        self.assertEqual(result["today_in_nominal_window_run_ids"],[])
        self.assertEqual(result["today_unknown_start_run_ids"],[201,202,203])
        self.assertTrue(result["no_in_window_capture_start_today"])

    def test_delayed_nightly_audit_targets_previous_capture_day(self):
        # Nominal 11/04 23:17 JST audit executes after JST midnight.
        now=datetime(2026,11,4,17,45,tzinfo=timezone.utc)
        self.assertEqual(audit_target_day(now,True),date(2026,11,4))
        self.assertEqual(audit_target_day(now,False),date(2026,11,5))
        rows=[{"id":301,"event":"schedule",
               "created_at":"2026-11-04T11:00:00Z",
               "run_started_at":"2026-11-04T11:00:00Z"}]
        target=audit_target_day(now,True)
        self.assertEqual(capture_window_health(rows,target,True)["today_in_nominal_window_run_ids"],[301])

    def test_on_time_nightly_and_pre_slot_boundary(self):
        at_slot=datetime(2026,11,5,14,17,tzinfo=timezone.utc)  # 23:17 JST
        before=at_slot-timedelta(seconds=1)
        self.assertEqual(audit_target_day(at_slot,True),date(2026,11,5))
        self.assertEqual(audit_target_day(before,True),date(2026,11,4))

    def test_audit_target_day_rejects_naive_clock(self):
        with self.assertRaisesRegex(ValueError,"timezone-aware"):
            audit_target_day(datetime(2026,11,5,2,30),True)

if __name__ == "__main__":
    unittest.main()

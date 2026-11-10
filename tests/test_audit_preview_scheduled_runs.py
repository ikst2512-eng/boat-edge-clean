import unittest
from datetime import datetime, timezone, date, timedelta
from scripts.audit_preview_scheduled_runs import summarize, daily_capture_health, research_day_health, RESEARCH_PLANNED_DAILY_SLOTS

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


    def test_research_separate_cron_and_dispatch_counts(self):
        now=datetime(2026,11,10,23,17,tzinfo=timezone(timedelta(hours=9)))
        def item(id,event,at):
            return {"id":id,"event":event,"created_at":at,
                    "head_branch":"main","status":"completed","conclusion":"success"}
        source=[item(1,"schedule","2026-11-10T06:37:36Z")]
        rescue=[item(2,"workflow_dispatch","2026-11-10T11:46:14Z"),
                item(3,"workflow_dispatch","2026-11-10T11:52:21Z")]
        output=research_day_health(source,rescue,day=date(2026,11,10),observed_at=now)
        self.assertEqual(output["expected_five_minute_slots_due"],RESEARCH_PLANNED_DAILY_SLOTS)
        self.assertEqual(output["observed_schedule_runs"],1)
        self.assertEqual(output["observed_workflow_dispatch_runs"],2)
        self.assertEqual(output["cron_health"],"severely_sparse_cron_observation")
        self.assertEqual(output["saved_races"],"unverified_from_run_status")

    def test_manual_dispatch_never_masks_missing_schedule(self):
        now=datetime(2026,11,10,23,17,tzinfo=timezone(timedelta(hours=9)))
        dispatched=[{"id":10,"event":"workflow_dispatch",
                     "head_branch":"main","created_at":"2026-11-10T11:46:14Z"}]
        output=research_day_health([],dispatched,day=date(2026,11,10),observed_at=now)
        self.assertEqual(output["observed_schedule_runs"],0)
        self.assertEqual(output["observed_workflow_dispatch_runs"],1)
        self.assertEqual(output["cron_health"],"no_cron_run_observed")

    def test_research_day_uses_jst_and_partial_window(self):
        now=datetime(2026,11,10,9,12,tzinfo=timezone(timedelta(hours=9)))
        output=research_day_health([],[],day=date(2026,11,10),observed_at=now)
        self.assertEqual(output["expected_five_minute_slots_due"],3)
        earlier=research_day_health([],[],day=date(2026,11,11),observed_at=now)
        self.assertEqual(earlier["expected_five_minute_slots_due"],0)
        self.assertEqual(earlier["cron_health"],"no_planned_ticks_yet")

    def test_research_day_rejects_duplicated_and_wrong_event_inventory(self):
        now=datetime(2026,11,10,23,17,tzinfo=timezone(timedelta(hours=9)))
        run={"id":1,"event":"schedule","head_branch":"main",
             "created_at":"2026-11-10T06:37:36Z"}
        with self.assertRaisesRegex(ValueError,"invalid_or_duplicate_id"):
            research_day_health([run,run],[],day=date(2026,11,10),observed_at=now)
        with self.assertRaisesRegex(ValueError,"invalid_run_type"):
            research_day_health([], [run],day=date(2026,11,10),observed_at=now)

if __name__ == "__main__":
    unittest.main()

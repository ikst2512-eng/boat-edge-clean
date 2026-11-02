import unittest
from datetime import datetime, timezone
from scripts.four_mode_watchdog_policy import should_dispatch

def run(minutes, event="schedule", status="completed", conclusion="failure"):
    from datetime import timedelta
    now=datetime(2026,11,3,0,0,tzinfo=timezone.utc)
    return {"created_at":(now-timedelta(minutes=minutes)).isoformat(),
            "event":event,"status":status,"conclusion":conclusion}

class WatchdogPolicyTests(unittest.TestCase):
    def setUp(self):
        self.now=datetime(2026,11,3,0,0,tzinfo=timezone.utc) # 09:00 JST
    def test_no_runs_in_active_hours_dispatch(self):
        self.assertTrue(should_dispatch([],self.now,"schedule"))
    def test_failed_schedule_can_retry(self):
        self.assertTrue(should_dispatch([run(5)],self.now,"schedule"))
    def test_recent_success_prevents_dispatch(self):
        self.assertFalse(should_dispatch([run(5,conclusion="success")],self.now,"schedule"))
    def test_running_prevents_dispatch(self):
        self.assertFalse(should_dispatch([run(5,status="in_progress",conclusion=None)],self.now,"schedule"))
    def test_failed_fallback_cooldown(self):
        self.assertFalse(should_dispatch([run(5,event="workflow_dispatch")],self.now,"schedule"))
        self.assertTrue(should_dispatch([run(21,event="workflow_dispatch")],self.now,"schedule"))
    def test_pr_is_read_only(self):
        self.assertFalse(should_dispatch([],self.now,"pull_request"))
    def test_off_hours_disabled(self):
        from datetime import timedelta
        self.assertFalse(should_dispatch([],self.now-timedelta(hours=3),"schedule"))
        self.assertFalse(should_dispatch([],self.now+timedelta(hours=12),"schedule"))
    def test_default_watchdog_policy_still_uses_original_windows(self):
        self.assertFalse(should_dispatch([run(15,conclusion="success")],self.now,"schedule"))
        self.assertFalse(should_dispatch([run(15,event="workflow_dispatch")],self.now,"schedule"))
        self.assertTrue(should_dispatch([run(15,conclusion="success")],self.now,"render_cron",
                                        recent_minutes=14,cooldown_minutes=14))

    def test_old_queued_capture_not_duplicated_by_render(self):
        self.assertFalse(should_dispatch([run(16,status="queued",conclusion=None)],
                                         self.now,"render_cron",
                                         recent_minutes=14,cooldown_minutes=14))
        self.assertFalse(should_dispatch([run(19,status="in_progress",conclusion=None)],
                                         self.now,"render_cron",
                                         recent_minutes=14,cooldown_minutes=14))
        self.assertTrue(should_dispatch([run(121,status="queued",conclusion=None)],
                                        self.now,"render_cron",
                                        recent_minutes=14,cooldown_minutes=14))

    def test_timezone_required(self):
        with self.assertRaises(ValueError):
            should_dispatch([],self.now.replace(tzinfo=None),"schedule")
if __name__=="__main__":
    unittest.main()

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

    def test_watchdog_cron_checks_each_scheduled_capture_slot(self):
        from pathlib import Path
        workflow = (Path(__file__).resolve().parent /
                    ".github/workflows/four-mode-capture-watchdog.yml").read_text()
        self.assertIn("cron: '12,27,42,57 22-23,0-12 * * *'", workflow)
        self.assertIn("recent_minutes=14, cooldown_minutes=14", workflow)
        self.assertIn("cron: '12,27,42 13 * * *'", workflow)

    def test_fifteen_minute_watchdog_recovers_missed_slot(self):
        # A successful run 20 minutes ago must not hide a missed 15-minute slot.
        self.assertTrue(should_dispatch([run(20, conclusion="success")],
                                        self.now, "schedule",
                                        recent_minutes=14, cooldown_minutes=14))
        # A success or accepted fallback inside the current slot still blocks.
        self.assertFalse(should_dispatch([run(13, conclusion="success")],
                                         self.now, "schedule",
                                         recent_minutes=14, cooldown_minutes=14))
        self.assertFalse(should_dispatch([run(13, event="workflow_dispatch")],
                                         self.now, "schedule",
                                         recent_minutes=14, cooldown_minutes=14))
        self.assertTrue(should_dispatch([run(15, event="workflow_dispatch")],
                                        self.now, "schedule",
                                        recent_minutes=14, cooldown_minutes=14))
        # Even a delayed job is never duplicated.
        self.assertFalse(should_dispatch([run(20, status="queued", conclusion=None)],
                                         self.now, "schedule",
                                         recent_minutes=14, cooldown_minutes=14))

    def test_nonmain_manual_dispatch_does_not_suppress_main_recovery(self):
        other = dict(run(5, event="workflow_dispatch", conclusion="success"),
                     head_branch="research/alternative")
        self.assertTrue(should_dispatch([other], self.now, "schedule",
                                        recent_minutes=14, cooldown_minutes=14))
        for status, conclusion in (("queued", None), ("in_progress", None),
                                   ("completed", "failure")):
            other = dict(run(5, event="workflow_dispatch",
                             status=status, conclusion=conclusion),
                         head_branch="research/alternative")
            self.assertTrue(should_dispatch([other], self.now, "render_cron",
                                            recent_minutes=14, cooldown_minutes=14))
        main = dict(run(5, event="workflow_dispatch", conclusion="failure"),
                    head_branch="main")
        self.assertFalse(should_dispatch([other, main], self.now, "schedule",
                                         recent_minutes=14, cooldown_minutes=14))

    def test_nonmain_success_does_not_hide_main_failed_capture(self):
        offbranch = dict(run(3, event="workflow_dispatch", conclusion="success"),
                         head_branch="experiment")
        failed_main = dict(run(5), head_branch="main")
        self.assertTrue(should_dispatch([offbranch, failed_main], self.now,
                                        "schedule", recent_minutes=14,
                                        cooldown_minutes=14))

    def test_clean_night_hours_do_not_extend_other_watchdogs(self):
        from datetime import timedelta
        late = self.now + timedelta(hours=13, minutes=29)  # 22:29 JST
        self.assertFalse(should_dispatch([], late, 'schedule'))
        self.assertTrue(should_dispatch([], late, 'schedule',
                                        recent_minutes=14, cooldown_minutes=14,
                                        end_hour_jst=22))
        self.assertFalse(should_dispatch([], late + timedelta(minutes=31),
                                         'schedule', end_hour_jst=22))
        with self.assertRaisesRegex(ValueError, 'invalid_dispatch_window'):
            should_dispatch([], late, 'schedule', end_hour_jst=24)

    def test_timezone_required(self):
        with self.assertRaises(ValueError):
            should_dispatch([],self.now.replace(tzinfo=None),"schedule")
if __name__=="__main__":
    unittest.main()

import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from scripts.v2_nightly_watchdog_policy import should_dispatch_nightly

JST = timezone(timedelta(hours=9))
NOW = datetime(2026, 11, 3, 23, 35, tzinfo=JST)


def run(when="21:30", event="schedule", status="completed", conclusion="success",
        branch="main"):
    h, m = map(int, when.split(":"))
    return dict(created_at=NOW.replace(hour=h, minute=m).astimezone(timezone.utc).isoformat(),
                event=event, status=status, conclusion=conclusion, head_branch=branch)


class NightlyWatchdogPolicyTests(unittest.TestCase):
    def test_missing_nightly_schedule_after_start_dispatches(self):
        self.assertTrue(should_dispatch_nightly([], NOW, "push"))

    def test_prior_to_fallback_window_is_inert(self):
        self.assertFalse(should_dispatch_nightly([], NOW.replace(hour=21,minute=44), "push"))
        self.assertFalse(should_dispatch_nightly([], NOW.replace(hour=0,minute=1), "push"))

    def test_pr_is_read_only(self):
        self.assertFalse(should_dispatch_nightly([], NOW, "pull_request"))

    def test_success_or_active_schedule_suppresses_duplicate(self):
        self.assertFalse(should_dispatch_nightly([run()], NOW, "push"))
        self.assertFalse(should_dispatch_nightly(
            [run(status="in_progress", conclusion=None)], NOW, "schedule"))

    def test_failed_schedule_allows_one_fallback(self):
        self.assertTrue(should_dispatch_nightly(
            [run(conclusion="failure")], NOW, "push"))
        self.assertFalse(should_dispatch_nightly(
            [run(conclusion="failure"), run("22:00", event="workflow_dispatch",
                                            conclusion="failure")], NOW, "push"))

    def test_old_pr_and_other_branch_do_not_suppress(self):
        self.assertTrue(should_dispatch_nightly(
            [run(event="pull_request"), run(branch="experiment")], NOW, "push"))

    def test_previous_day_and_future_are_ignored(self):
        older = run()
        older["created_at"] = (datetime(2026, 11, 2, 12, 30,
                                         tzinfo=timezone.utc)).isoformat()
        later = run()
        later["created_at"] = (datetime(2026, 11, 4, 15, 0,
                                         tzinfo=timezone.utc)).isoformat()
        self.assertTrue(should_dispatch_nightly([older, later], NOW, "push"))

    def test_naive_clock_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "naive"):
            should_dispatch_nightly([], NOW.replace(tzinfo=None), "push")

    def test_workflow_wires_fallback_and_records_artifact(self):
        path = Path(".github/workflows/four-mode-capture-watchdog.yml")
        source = path.read_text(encoding="utf-8")
        self.assertIn("scripts.v2_nightly_watchdog_policy", source)
        self.assertIn("v2_nightly_watchdog_policy", source)
        self.assertIn("v2-nightly-decision.json", source)
        self.assertIn("50 12 * * *", source)
        self.assertIn("20 13 * * *", source)


if __name__ == "__main__":
    unittest.main()

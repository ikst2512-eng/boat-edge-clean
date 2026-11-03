import unittest

from scripts.audit_four_mode_daily_capture_liveness import report, should_fail

WF = "four-mode-prospective-capture.yml"


def run(i, at="2026-11-04T00:07:00+00:00", status="completed", conclusion="success",
        event="schedule"):
    return {"id": i, "created_at": at, "status": status, "conclusion": conclusion,
            "event": event, "workflow": WF}


class CaptureLivenessTests(unittest.TestCase):
    def test_empty_history_is_failure_only_on_scheduled_main(self):
        result = report("20261104", {"recent_capture_runs": []})
        self.assertEqual(result["status"], "no_capture_runs_observed")
        self.assertTrue(should_fail(result, "schedule", "refs/heads/main"))
        self.assertFalse(should_fail(result, "push", "refs/heads/main"))
        self.assertFalse(should_fail(result, "pull_request", "refs/pull/3/merge"))

    def test_prior_jst_day_does_not_count(self):
        result = report("20261104", {"recent_capture_runs": [
            run(1, "2026-11-03T14:59:59Z")]})
        self.assertEqual(result["same_day_run_ids"], [])
        result = report("20261104", {"recent_capture_runs": [
            run(2, "2026-11-03T15:00:01Z")]})
        self.assertEqual(result["same_day_run_ids"], [2])

    def test_one_success_after_failure_is_healthy(self):
        result = report("20261104", {"recent_capture_runs": [
            run(1, conclusion="failure"), run(2, event="workflow_dispatch")]})
        self.assertEqual(result["status"], "capture_success_observed")
        self.assertEqual(result["completed_success_count"], 1)
        self.assertFalse(should_fail(result, "schedule", "refs/heads/main"))
        self.assertFalse(result["publication_verified"])

    def test_all_failures_trigger_distinct_alert(self):
        result = report("20261104", {"recent_capture_runs": [run(1, conclusion="failure")]})
        self.assertEqual(result["status"], "all_observed_captures_failed")
        self.assertTrue(should_fail(result, "schedule", "refs/heads/main"))

    def test_in_progress_is_unverified_not_absent(self):
        result = report("20261104", {"recent_capture_runs": [
            run(1, status="in_progress", conclusion=None)]})
        self.assertEqual(result["status"], "capture_pending")
        self.assertFalse(should_fail(result, "schedule", "refs/heads/main"))

    def test_reject_malformed_metadata(self):
        cases = [{"recent_capture_runs": [{"id": True, "workflow": WF, "event": "schedule",
                                           "created_at": "2026-11-04T00:07:00Z"}]},
                 {"recent_capture_runs": [run(1, at="no-date")]},
                 {"recent_capture_runs": [run(1, event="pull_request")]}]
        for inventory in cases:
            with self.subTest(inventory=inventory), self.assertRaises(ValueError):
                report("20261104", inventory)


if __name__ == "__main__":
    unittest.main()

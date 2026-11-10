import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.audit_four_mode_daily_capture_liveness import report, should_fail, main

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

    def test_missing_inventory_is_fail_closed_on_scheduled_main(self):
        result = {"status": "capture_inventory_unavailable"}
        self.assertTrue(should_fail(result, "schedule", "refs/heads/main"))
        self.assertFalse(should_fail(result, "pull_request", "refs/pull/3/merge"))

    def test_missing_inventory_writes_artifact_even_when_scheduled_audit_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "liveness.json"
            missing = Path(directory) / "missing.json"
            args = ["audit", "--inventory", str(missing), "--output", str(output),
                    "--day-jst", "20261104"]
            with patch("sys.argv", args), patch.dict(
                    "os.environ", {"GITHUB_EVENT_NAME": "schedule",
                                   "GITHUB_REF": "refs/heads/main"}):
                with self.assertRaises(SystemExit) as error:
                    main()
            self.assertEqual(error.exception.code, 2)
            evidence = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(evidence["status"], "capture_inventory_unavailable")
            self.assertFalse(evidence["publication_verified"])

    def test_truncated_history_cannot_prove_all_runs_failed_or_absent(self):
        inventory = {"recent_capture_runs": [run(1, conclusion="failure")],
                     "source_coverage": {WF + ":schedule": {
                         "returned": 100, "may_be_truncated": True}}}
        result = report("20261104", inventory)
        self.assertEqual(result["status"], "capture_inventory_incomplete")
        self.assertTrue(should_fail(result, "schedule", "refs/heads/main"))
        inventory["recent_capture_runs"] = [run(2)]
        result = report("20261104", inventory)
        self.assertEqual(result["status"], "capture_success_observed")
        self.assertTrue(result["capture_coverage_incomplete"])

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


    def test_completed_without_conclusion_is_unknown_not_confirmed_failure(self):
        result = report("20261104", {"recent_capture_runs": [
            run(81, status="completed", conclusion=None),
        ]})
        self.assertEqual(result["status"], "capture_outcome_unknown")
        self.assertEqual(result["completed_success_count"], 0)
        self.assertEqual(result["completed_failure_count"], 0)
        self.assertEqual(result["completed_non_success_count"], 0)
        self.assertEqual(result["completed_unknown_outcome_count"], 1)
        self.assertEqual(result["completed_unknown_outcome_run_ids"], [81])
        self.assertTrue(should_fail(result, "schedule", "refs/heads/main"))
        self.assertFalse(should_fail(result, "pull_request", "refs/pull/3/merge"))
        self.assertFalse(result["publication_verified"])

    def test_failure_plus_unknown_is_not_all_observed_failed(self):
        result = report("20261104", {"recent_capture_runs": [
            run(82, conclusion="failure"),
            run(83, status="completed", conclusion=None),
        ]})
        self.assertEqual(result["status"], "capture_outcome_unknown")
        self.assertEqual(result["completed_failure_count"], 1)
        self.assertEqual(result["completed_non_success_count"], 1)
        self.assertEqual(result["completed_unknown_outcome_run_ids"], [83])
        self.assertTrue(should_fail(result, "schedule", "refs/heads/main"))

    def test_duplicate_run_ids_do_not_inflate_capture_success(self):
        for rows in (
            [run(84), run(84)],
            [run(84), run(84, event="workflow_dispatch")],
        ):
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                report("20261104", {"recent_capture_runs": rows})

    def test_malformed_coverage_returns_a_preserved_unavailable_report(self):
        malformed = {"recent_capture_runs": [run(85)],
                     "source_coverage": {WF + ":schedule": None}}
        with self.assertRaises(ValueError):
            report("20261104", malformed)
        with tempfile.TemporaryDirectory() as directory:
            inp = Path(directory) / "inventory.json"
            output = Path(directory) / "liveness.json"
            inp.write_text(json.dumps(malformed), encoding="utf-8")
            args = ["audit", "--inventory", str(inp), "--output",
                    str(output), "--day-jst", "20261104"]
            with patch("sys.argv", args), patch.dict(
                    "os.environ", {"GITHUB_EVENT_NAME": "schedule",
                                   "GITHUB_REF": "refs/heads/main"}):
                with self.assertRaises(SystemExit) as e:
                    main()
            self.assertEqual(e.exception.code, 2)
            saved = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(saved["status"], "capture_inventory_unavailable")
            self.assertEqual(saved["error_type"], "ValueError")

    def test_completed_cancelled_is_non_success_not_null_outcome(self):
        result = report("20261104", {"recent_capture_runs": [
            run(86, status="completed", conclusion="cancelled"),
        ]})
        self.assertEqual(result["status"], "all_observed_captures_failed")
        self.assertEqual(result["completed_failure_count"], 0)
        self.assertEqual(result["completed_non_success_count"], 1)
        self.assertEqual(result["completed_unknown_outcome_count"], 0)


    def test_preopening_success_cannot_certify_capture_window(self):
        result = report("20261109", {"recent_capture_runs": [
            run(901, "2026-11-09T03:03:00+09:00"),
        ]})
        # Keep raw execution truth, but do not claim this as a scheduled
        # 07:07+ observation; a delayed prior-night Cron can start at 03:03.
        self.assertEqual(result["status"], "capture_success_observed")
        self.assertEqual(result["completed_success_count"], 1)
        self.assertEqual(result["completed_success_in_capture_window_count"], 0)
        self.assertFalse(result["capture_window_success_observed"])
        self.assertEqual(
            result["same_day_outside_capture_window_run_ids"]["pre_opening"],
            [901])
        self.assertTrue(should_fail(result, "schedule", "refs/heads/main"))
        self.assertFalse(should_fail(result, "pull_request", "refs/pull/1/merge"))
        self.assertFalse(result["per_nominal_slot_capture_delivery_verified"])

    def test_postwindow_success_cannot_certify_capture_window(self):
        result = report("20261109", {"recent_capture_runs": [
            run(902, "2026-11-09T20:57:01+09:00"),
        ]})
        self.assertEqual(result["completed_success_count"], 1)
        self.assertEqual(result["completed_success_in_capture_window_count"], 0)
        self.assertEqual(
            result["same_day_outside_capture_window_run_ids"][
                "after_last_slot_grace"], [902])
        self.assertTrue(should_fail(result, "schedule", "refs/heads/main"))

    def test_window_boundaries_and_dispatch_do_not_prove_slot_identity(self):
        result = report("20261109", {"recent_capture_runs": [
            run(910, "2026-11-09T07:06:59+09:00"),
            run(911, "2026-11-09T07:07:00+09:00"),
            run(912, "2026-11-09T20:57:00+09:00", event="workflow_dispatch"),
            run(913, "2026-11-09T20:57:01+09:00"),
        ]})
        self.assertEqual(result["completed_success_count"], 4)
        self.assertEqual(result["completed_success_in_capture_window_count"], 2)
        self.assertEqual(result["same_day_in_capture_window_run_ids"], [911, 912])
        self.assertTrue(result["capture_window_success_observed"])
        self.assertEqual(result["same_day_outside_capture_window_run_ids"], {
            "pre_opening": [910], "after_last_slot_grace": [913]})
        self.assertFalse(result["per_nominal_slot_capture_delivery_verified"])
        self.assertFalse(result["publication_verified"])
        self.assertFalse(should_fail(result, "schedule", "refs/heads/main"))

    def test_only_in_window_pending_does_not_claim_success(self):
        result = report("20261109", {"recent_capture_runs": [
            run(920, "2026-11-09T07:07:00+09:00",
                status="in_progress", conclusion=None),
            run(921, "2026-11-09T03:03:00+09:00"),
        ]})
        self.assertEqual(result["status"], "capture_success_observed")
        self.assertEqual(result["completed_success_count"], 1)
        self.assertEqual(result["pending_count"], 1)
        self.assertFalse(result["capture_window_success_observed"])
        self.assertTrue(should_fail(result, "schedule", "refs/heads/main"))



if __name__ == "__main__":
    unittest.main()

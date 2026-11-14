"""Synthetic schedule-run visibility contract; never invokes GitHub network."""
from datetime import datetime
import unittest

from position_sensitive_schedule_run_inventory import (
    WORKFLOW, SCHEMA, audit_run_inventory, live_audit,
    schedule_run_url, _live_fetch_json,
)

DAY = "20261109"
NOW = datetime.fromisoformat("2026-11-09T10:30:00+00:00")
WORKFLOW_BYTES = b"""name: Four-mode prospective capture (research only)
on:
  workflow_dispatch:
  schedule:
    - cron: '7,22,37,52 22 * * *'
    - cron: '7,22,37,52 23 * * *'
    - cron: '7,22,37,52 0-11 * * *'
jobs:
  capture:
    if: github.ref == 'refs/heads/main' && (github.event_name == 'schedule')
"""


def run(i, path=WORKFLOW, at="2026-11-09T09:00:00Z",
        event="schedule", branch="main", conclusion="success"):
    return {
        "id": i, "path": path, "created_at": at, "event": event,
        "head_branch": branch, "status": "completed", "conclusion": conclusion,
    }


def page(runs, total=None):
    return {"total_count": len(runs) if total is None else total,
            "workflow_runs": runs}


class ScheduleVsRunVisibilityTests(unittest.TestCase):
    def test_50_elapsed_versus_3_runs_not_47_confirmed_misses(self):
        runs = [
            run(1, at="2026-11-09T01:37:58Z"),
            run(2, at="2026-11-09T02:36:27Z"),
            run(3, at="2026-11-09T06:10:20Z"),
        ]
        runs += [run(i, path=".github/workflows/unrelated.yml")
                 for i in range(4,39)]
        report = audit_run_inventory(DAY, NOW, WORKFLOW_BYTES, [page(runs)])
        self.assertEqual(report["schema"], SCHEMA)
        self.assertEqual(report["expected_slots_for_full_day"], 56)
        self.assertEqual(report["scheduled_slots_elapsed"], 50)
        self.assertEqual(report["scheduled_slots_not_yet_due"], 6)
        self.assertEqual(report["api_runs_all_repo_workflows_in_window"], 38)
        self.assertEqual(report["observed_matching_four_mode_scheduled_runs"], 3)
        self.assertEqual(report["observed_matching_workflow_success_conclusions"], 3)
        self.assertEqual(report["numerical_elapsed_minus_observed_run_count"], 47)
        self.assertFalse(
            report["this_difference_proves_individual_missed_or_failed_slots"])
        self.assertFalse(report["complete_scheduled_and_rescue_run_inventory_verified"])
        self.assertFalse(report["observed_run_success_proves_forecast_publication"])
        self.assertFalse(report["formal"])
        self.assertEqual(report["first_remote_candidate_receipts_verified"], 0)
        self.assertEqual(
            report["matching_scheduled_runs"][0]["created_at_utc"],
            "2026-11-09T01:37:58+00:00",
        )

    def test_zero_created_runs_is_observation_not_proven_failure(self):
        report = audit_run_inventory(DAY, NOW, WORKFLOW_BYTES, [page([])])
        self.assertEqual(report["scheduled_slots_elapsed"], 50)
        self.assertEqual(report["observed_matching_four_mode_scheduled_runs"], 0)
        self.assertFalse(report["this_difference_proves_individual_missed_or_failed_slots"])
        self.assertFalse(report["promotion_allowed"])

    def test_paginated_all_repo_results_are_complete_before_filtering(self):
        x = [run(i, path=".github/workflows/other.yml") for i in range(1,102)]
        x[0] = run(1)
        x[-1] = run(101)
        a = page(x[:100], 101)
        b = page(x[100:], 101)
        report = audit_run_inventory(DAY, NOW, WORKFLOW_BYTES, [a,b])
        self.assertEqual(report["observed_matching_four_mode_scheduled_runs"], 2)
        self.assertEqual(report["api_runs_all_repo_workflows_in_window"], 101)
        with self.assertRaisesRegex(ValueError, "pagination_incomplete"):
            audit_run_inventory(DAY, NOW, WORKFLOW_BYTES, [a])
        with self.assertRaisesRegex(ValueError, "pagination_incomplete"):
            audit_run_inventory(DAY, NOW, WORKFLOW_BYTES, [a,b,b])

    def test_duplicate_id_and_wrong_event_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "duplicate_id"):
            audit_run_inventory(DAY, NOW, WORKFLOW_BYTES, [page([run(1),run(1)])])
        with self.assertRaisesRegex(ValueError, "unexpected_actions_run"):
            audit_run_inventory(DAY, NOW, WORKFLOW_BYTES, [page([run(1,event="workflow_dispatch")])])

    def test_wrong_branch_and_forged_status_fail_closed(self):
        for item in (run(1,branch="research"), run(1,conclusion="fabricated")):
            with self.subTest(item=item), self.assertRaises(ValueError):
                audit_run_inventory(DAY, NOW, WORKFLOW_BYTES, [page([item])])

    def test_api_created_outside_window_fails(self):
        for created in ("2026-11-08T20:59:59Z",
                        "2026-11-09T10:30:01Z",
                        "2026-11-09T09:00:00+09:00",
                        "wrong"):
            with self.subTest(created=created), self.assertRaises(ValueError):
                audit_run_inventory(DAY, NOW, WORKFLOW_BYTES,
                                    [page([run(1,at=created)])])

    def test_mismatching_production_cron_fails_before_acceptance(self):
        for altered in (
            WORKFLOW_BYTES.replace(b"7,22,37,52 23",b"7,22,37,52 21"),
            WORKFLOW_BYTES.replace(b"    - cron: '7,22,37,52 23 * * *'\n", b""),
            WORKFLOW_BYTES.replace(b"refs/heads/main", b"refs/heads/research"),
        ):
            with self.subTest(altered=altered), self.assertRaisesRegex(
                    ValueError, "production_schedule_changed"):
                audit_run_inventory(DAY, NOW, altered, [page([])])

    def test_invalid_day_and_clock_rejected(self):
        for day in ("20261108","20270101","20261132","2026-11-09","../../"):
            with self.subTest(day=day), self.assertRaises(ValueError):
                audit_run_inventory(day, NOW, WORKFLOW_BYTES, [page([])])
        with self.assertRaisesRegex(ValueError, "invalid_observation_clock"):
            audit_run_inventory(DAY, datetime.now(), WORKFLOW_BYTES, [page([])])

    def test_live_readonly_audit_pins_main_and_one_page(self):
        expected = schedule_run_url(DAY,NOW,1)
        expected_manual = schedule_run_url(DAY,NOW,1,"workflow_dispatch")
        calls = []
        def git(*args):
            calls.append(("git",args))
            if args[0] == "rev-parse":
                return (("c"*40) + "\n").encode()
            if args[0] == "show":
                self.assertEqual(args[1], "c"*40 + ":" + WORKFLOW)
                return WORKFLOW_BYTES
            raise AssertionError("unallowlisted_git_call")
        def fetch(url):
            calls.append(("get",url))
            if url == expected:
                return page([run(1)])
            self.assertEqual(url,expected_manual)
            return page([run(2,event="workflow_dispatch")])
        report=live_audit(DAY,NOW,fetch=fetch,git=git)
        self.assertTrue(report["live_readonly_github_api_invoked"])
        self.assertEqual(report["main_git_snapshot_sha"],"c"*40)
        self.assertEqual(report["observed_matching_four_mode_scheduled_runs"],1)
        self.assertEqual(report["observed_matching_four_mode_manual_dispatch_runs"],1)
        self.assertEqual(report["observed_manual_dispatch_main_branch_runs"],1)
        self.assertEqual(sum(x[0]=="get" for x in calls),2)
        self.assertFalse(report["formal"])

    def test_manual_dispatch_reported_separately_no_claim_of_slot_filling(self):
        scheduled = [page([run(1)])]
        dispatched = [page([
            run(2,event="workflow_dispatch"),
            run(3,event="workflow_dispatch",branch="research/safe"),
        ])]
        out = audit_run_inventory(DAY,NOW,WORKFLOW_BYTES,scheduled,dispatched)
        self.assertEqual(out["observed_matching_four_mode_scheduled_runs"],1)
        self.assertEqual(out["observed_matching_four_mode_manual_dispatch_runs"],2)
        self.assertEqual(out["observed_manual_dispatch_main_branch_runs"],1)
        self.assertEqual(out["observed_manual_dispatch_nonmain_branch_runs"],1)
        self.assertEqual(out["numerical_elapsed_minus_observed_run_count"],49)
        self.assertFalse(out["manual_dispatch_success_proves_capture_publication"])
        self.assertFalse(out["complete_scheduled_and_rescue_run_inventory_verified"])
        self.assertFalse(out["run_to_exact_cron_slot_attribution_verified"])
        self.assertFalse(out["formal"])

    def test_manual_dispatch_bad_pagination_and_cross_event_duplicate_rejected(self):
        scheduled=[page([run(1)])]
        with self.assertRaisesRegex(ValueError, "manual_dispatch_pagination_incomplete"):
            audit_run_inventory(DAY,NOW,WORKFLOW_BYTES,scheduled,
                                [page([run(2,event="workflow_dispatch")],total=101)])
        with self.assertRaisesRegex(ValueError, "invalid_or_duplicate_manual_dispatch_run"):
            audit_run_inventory(DAY,NOW,WORKFLOW_BYTES,scheduled,
                                [page([run(1,event="workflow_dispatch")])])
        with self.assertRaisesRegex(ValueError, "invalid_or_duplicate_manual_dispatch_run"):
            audit_run_inventory(DAY,NOW,WORKFLOW_BYTES,scheduled,
                                [page([run(2)])])

    def test_unallowlisted_http_url_fails_without_network(self):
        with self.assertRaisesRegex(ValueError, "not_allowlisted"):
            _live_fetch_json("https://example.com/actions/runs")
        self.assertIn("/actions/runs?event=schedule&",
                      schedule_run_url(DAY,NOW,1))


if __name__ == "__main__":
    unittest.main()

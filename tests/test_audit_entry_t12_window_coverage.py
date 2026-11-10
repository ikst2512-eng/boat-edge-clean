"""Regression gates for research-only per-race T-12 run creation audit."""
import copy
import json
import unittest
from pathlib import Path

from scripts.audit_entry_t12_window_coverage import audit_snapshot

FIXTURE = (Path(__file__).resolve().parent / "fixtures" /
           "entry_t12_missing_nine_20261110.json")


def snapshot():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def extra_run(run_id, stamp, *, event="schedule", branch="main", workflow_id=405663641):
    return {"id": run_id, "created_at": stamp, "event": event,
            "head_branch": branch, "workflow_id": workflow_id}


class EntryT12WindowAuditTests(unittest.TestCase):
    def test_nov10_nine_missing_races_all_have_no_on_time_action_creation(self):
        report = audit_snapshot(snapshot())
        self.assertEqual(report["count"], 9)
        self.assertEqual(report["state_counts"]["no_on_time_action_creation_observed"], 9)
        self.assertEqual(report["state_counts"]["on_time_action_created_execution_unverified"], 0)
        self.assertEqual(len({r["race_code"] for r in report["races"]}), 9)
        self.assertTrue(all(not r["ledger_path_present"] for r in report["races"]))
        self.assertTrue(report["research_only"])
        self.assertFalse(report["formal"])
        self.assertFalse(report["independent_first_seen_verified"])
        self.assertFalse(report["collector_execution_proven"])
        self.assertTrue(report["no_dispatch_or_ledger_write"])

    def test_one_scheduled_run_can_cover_three_overlapping_windows_but_not_save_proof(self):
        payload = snapshot()
        payload["runs"].append(extra_run(900001, "2026-11-10T03:50:00Z"))
        report = audit_snapshot(payload)
        self.assertEqual(report["state_counts"]["on_time_action_created_execution_unverified"], 3)
        self.assertEqual(report["state_counts"]["no_on_time_action_creation_observed"], 6)
        for code in ("202611100406", "202611101010", "202611101406"):
            row = next(x for x in report["races"] if x["race_code"] == code)
            self.assertEqual(row["created_on_time_action_ids"], [900001])
            self.assertFalse(row["collector_step_executed_in_window_verified"])
            self.assertFalse(row["source_available_before_cutoff_verified"])
            self.assertFalse(row["first_git_add_before_cutoff_verified"])
            self.assertFalse(row["formal_t12_certified"])

    def test_boundary_window_at_exact_two_and_fourteen_minutes_before_cutoff(self):
        payload = snapshot()
        # 04/6R deadline 13:09, cutoff 12:57, window [12:43, 12:55].
        payload["runs"].extend([
            extra_run(900002, "2026-11-10T03:43:00Z"),
            extra_run(900003, "2026-11-10T03:55:00Z"),
            extra_run(900004, "2026-11-10T03:42:59Z"),
            extra_run(900005, "2026-11-10T03:55:01Z"),
        ])
        report = audit_snapshot(payload)
        row = next(x for x in report["races"] if x["race_code"] == "202611100406")
        self.assertEqual(row["created_on_time_action_ids"], [900002, 900003])

    def test_wrong_workflow_branch_and_pr_do_not_rescue_missing_races(self):
        payload = snapshot()
        payload["runs"].extend([
            extra_run(900006, "2026-11-10T03:50:00Z", branch="feature"),
            extra_run(900007, "2026-11-10T03:50:00Z", event="pull_request"),
            extra_run(900008, "2026-11-10T03:50:00Z", workflow_id=405586120),
        ])
        self.assertEqual(
            audit_snapshot(payload)["state_counts"]["no_on_time_action_creation_observed"], 9
        )

    def test_unfinished_window_or_incomplete_api_cannot_assert_absence(self):
        early = snapshot()
        early["observed_at_jst"] = "2026-11-10T12:50:00+09:00"
        early["runs"] = []
        report = audit_snapshot(early)
        first = next(x for x in report["races"] if x["race_code"] == "202611100406")
        self.assertEqual(first["action_creation_state"], "window_not_finished")
        partial = snapshot()
        partial["run_inventory_complete"] = False
        report = audit_snapshot(partial)
        self.assertEqual(report["state_counts"]["incomplete_action_inventory_unverified"], 9)
        self.assertEqual(report["state_counts"]["no_on_time_action_creation_observed"], 0)

    def test_incomplete_ledger_only_reports_unknown_path_presence(self):
        payload = snapshot()
        payload["ledger_inventory_complete"] = False
        row = audit_snapshot(payload)["races"][0]
        self.assertIsNone(row["ledger_path_present"])

    def test_bad_receipts_fail_closed_without_converting_to_zero_runs(self):
        for modify in (
            lambda p: p.update(event_types_checked=["schedule"]),
            lambda p: p.update(run_inventory_complete="yes"),
            lambda p: p["runs"].append(copy.deepcopy(p["runs"][0])),
            lambda p: p["races"].append(copy.deepcopy(p["races"][0])),
            lambda p: p["races"][0].update(source_deadline_jst="2026-11-10T13:09:00"),
            lambda p: p["runs"][0].update(created_at="2026-11-11T00:00:00+09:00"),
            lambda p: p.update(ledger_present_race_codes=["20261110999"]),
        ):
            with self.subTest(modify=modify):
                payload = snapshot()
                modify(payload)
                with self.assertRaises(ValueError):
                    audit_snapshot(payload)


if __name__ == "__main__":
    unittest.main()

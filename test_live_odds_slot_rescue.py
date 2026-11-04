"""Read-only policy tests for the existing-watchdog odds slot rescue."""
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from scripts import live_odds_slot_rescue as rescue

JST = timezone(timedelta(hours=9))
REPO = "ikst2512-eng/boat-edge-clean"
MAIN = "refs/heads/main"


def at(hour, minute, day=4):
    return datetime(2026, 11, day, hour, minute, tzinfo=JST)


def entry(event, when, *, status="completed", conclusion="success",
          branch="main", id=1):
    return {
        "id": id,
        "event": event,
        "head_branch": branch,
        "created_at": when.astimezone(timezone.utc).isoformat(),
        "status": status,
        "conclusion": conclusion,
    }


def history(*rows):
    return {"workflow_runs": list(rows)}


def judge(now, scheduled=None, dispatched=None, event="schedule",
          ref=MAIN, trigger=None):
    return rescue.decision(
        history(*(scheduled or [])), history(*(dispatched or [])),
        now, event, ref, trigger, REPO)


class OddsRescuePolicyTest(unittest.TestCase):
    def test_three_slots_and_strict_bounded_recovery(self):
        for hour in (12, 14, 16):
            self.assertIsNone(rescue.slot_for(at(hour, 39)))
            self.assertEqual(rescue.slot_for(at(hour, 40)), at(hour, 25))
            self.assertEqual(rescue.slot_for(at(hour + 1, 9)), at(hour, 25))
            self.assertIsNone(rescue.slot_for(at(hour + 1, 10)))
        self.assertIsNone(rescue.slot_for(at(22, 10)))
        self.assertIsNone(rescue.slot_for(at(12, 45, day=5) - timedelta(days=1, hours=1)))

    def test_missing_direct_is_only_eligible_not_proof(self):
        d = judge(at(12, 43))
        self.assertEqual(d["action"], "eligible_for_recovery")
        self.assertEqual(d["direct_runs_after_slot"], 0)
        self.assertNotIn("direct_cron_observed", d)

    def test_direct_success_or_active_suppresses_duplicate(self):
        for status, conclusion in (
            ("completed", "success"), ("queued", None),
            ("in_progress", None)):
            with self.subTest(status=status):
                d = judge(at(12, 43), scheduled=[
                    entry("schedule", at(12, 32), status=status,
                          conclusion=conclusion)])
                self.assertEqual(d["action"], "no_dispatch")
                self.assertEqual(d["reason"], "direct_schedule_success_or_active")

    def test_failed_direct_allows_one_catchup(self):
        d = judge(at(14, 50), scheduled=[
            entry("schedule", at(14, 32), conclusion="failure")])
        self.assertEqual(d["action"], "eligible_for_recovery")
        self.assertEqual(d["reason"], "direct_schedule_missing_or_failed")

    def test_prior_dispatch_any_outcome_blocks_retry_storm(self):
        for status, conclusion in (
            ("completed", "success"), ("completed", "failure"),
            ("queued", None)):
            with self.subTest(status=status):
                d = judge(at(16, 44), dispatched=[
                    entry("workflow_dispatch", at(16, 41),
                          status=status, conclusion=conclusion)])
                self.assertEqual(d["reason"], "prior_slot_dispatch_exists")

    def test_previous_day_runs_do_not_suppress_today(self):
        d = judge(at(12, 44), scheduled=[
            entry("schedule", at(12, 42, day=3))],
            dispatched=[entry("workflow_dispatch", at(12, 43, day=3))])
        self.assertEqual(d["action"], "eligible_for_recovery")

    def test_pr_manual_and_feature_ref_are_not_recovery_wakeups(self):
        for event, ref in (
            ("pull_request", MAIN),
            ("workflow_dispatch", MAIN),
            ("push", "refs/heads/feature"),
        ):
            self.assertEqual(judge(at(12, 43), event=event, ref=ref)["action"],
                             "no_dispatch")
        self.assertFalse(rescue.permitted_wakeup("workflow_run", MAIN, {}, REPO))

    def test_trusted_scheduled_upstream_completion_can_wake_recovery(self):
        trigger = {"workflow_run": {
            "name": "Preview capture (schedule)",
            "event": "schedule", "head_branch": "main",
            "status": "completed", "conclusion": "success",
            "head_repository": {"full_name": REPO},
        }}
        d = judge(at(12, 43), event="workflow_run", trigger=trigger)
        self.assertEqual(d["action"], "eligible_for_recovery")
        altered = {"workflow_run": {
            **trigger["workflow_run"], "head_repository":
                {"full_name": "other/repo"},
        }}
        self.assertEqual(judge(at(12, 43), event="workflow_run",
                               trigger=altered)["action"], "no_dispatch")

    def test_completed_direct_unknown_outcome_never_triggers_dispatch(self):
        d = judge(at(12, 44), scheduled=[
            entry("schedule", at(12, 35), conclusion=None)])
        self.assertEqual(d["action"], "no_dispatch")
        self.assertEqual(d["reason"], "direct_schedule_success_or_active")

    def test_main_accepts_one_real_dispatch_and_records_nonproof_receipt(self):
        with tempfile.TemporaryDirectory() as tmp, \
             patch.object(rescue, "OUTPUT", Path(tmp) / "decision.json"), \
             patch.object(rescue, "now_utc", return_value=at(12, 43)), \
             patch.object(rescue, "fetch_history", side_effect=[
                 history(), history()]) as fetch, \
             patch.object(rescue, "dispatch") as dispatch, \
             patch.dict("os.environ", {
                 "GITHUB_EVENT_NAME": "schedule", "GITHUB_REF": MAIN,
                 "GH_REPOSITORY": REPO, "GH_TOKEN": "test",
                 "GITHUB_RUN_ID": "777",
             }):
            rescue.main()
            result = json.loads((Path(tmp) / "decision.json").read_text())
            self.assertEqual(result["action"],
                             "fallback_dispatch_accepted_not_sample_proof")
            self.assertFalse(result["on_time_slot_verified"])
            self.assertFalse(result["recovery_odds_verified"])
            self.assertEqual(result["slot_jst"], at(12, 25).isoformat())
            self.assertEqual(fetch.call_count, 2)
            dispatch.assert_called_once()
            self.assertEqual(dispatch.call_args.args[2], at(12, 25))

    def test_missing_ambiguous_truncated_api_history_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "invalid_odds_run_history"):
            rescue.checked_history({}, "schedule", at(12, 25), at(12, 44))
        with self.assertRaisesRegex(ValueError, "invalid_odds_history_created_at"):
            rescue.checked_history(history({
                "event": "schedule", "id": 12,
                "head_branch": "main"}), "schedule", at(12, 25), at(12, 44))
        with self.assertRaisesRegex(ValueError, "page_truncated"):
            rows = [entry("schedule", at(12, 26), id=i+1) for i in range(100)]
            rescue.checked_history(history(*rows), "schedule",
                                   at(12, 25), at(12, 44))

    def test_outside_hours_writes_receipt_without_network_or_token(self):
        with tempfile.TemporaryDirectory() as tmp, \
             patch.object(rescue, "OUTPUT", Path(tmp) / "decision.json"), \
             patch.object(rescue, "fetch_history") as fetch, \
             patch.object(rescue, "dispatch") as dispatch, \
             patch.object(rescue, "now_utc", return_value=at(22, 10)), \
             patch.dict("os.environ", {
                 "GITHUB_EVENT_NAME": "push", "GITHUB_REF": MAIN,
                 "GH_REPOSITORY": REPO, "GITHUB_RUN_ID": "8",
             }):
            rescue.main()
            result = json.loads((Path(tmp) / "decision.json").read_text())
            self.assertEqual(result["action"], "no_dispatch")
            self.assertFalse(result["recovery_odds_verified"])
            self.assertFalse(result["on_time_slot_verified"])
            fetch.assert_not_called()
            dispatch.assert_not_called()

    def test_dispatch_marks_recovery_slot_in_github_webhook_payload(self):
        captured = []
        class Response:
            status = 204
            def __enter__(self): return self
            def __exit__(self, *_): return False
        def mock_open(req, timeout):
            captured.append(req)
            return Response()
        with patch.object(rescue, "urlopen", side_effect=mock_open):
            rescue.dispatch("https://api.github.com/repos/example/repo/actions/workflows/live-official-odds-probe.yml",
                            {"Authorization": "Bearer token"}, at(12, 25))
        self.assertEqual(len(captured), 1)
        self.assertEqual(captured[0].get_method(), "POST")
        self.assertEqual(json.loads(captured[0].data),
                         {"ref": "main", "inputs": {"rescue_slot_jst":
                          "2026-11-04T12:25:00+09:00"}})

    def test_watchdog_uses_existing_cadence_and_independent_evidence(self):
        wf = Path(".github/workflows/four-mode-capture-watchdog.yml").read_text()
        self.assertIn("python -m scripts.live_odds_slot_rescue", wf)
        self.assertIn("scripts/live_odds_slot_rescue.py", wf)
        self.assertIn("test_live_odds_slot_rescue", wf)
        self.assertIn("four-mode-evidence/odds-slot-rescue-decision.json", wf)
        self.assertEqual(wf.count("- cron:"), 4)
        self.assertIn("run: python -m scripts.clean_prospective_watchdog", wf)


if __name__ == "__main__":
    unittest.main()

"""Deterministic tests for the CLEAN capture missed-cron rescue."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from scripts.clean_prospective_watchdog import decide

NOW = datetime(2026, 11, 5, 0, 15, tzinfo=timezone.utc)  # 09:15 JST
MAIN = "refs/heads/main"


def run(age, event="schedule", status="completed", conclusion="success",
        branch="main"):
    return {
        "created_at": (NOW - timedelta(minutes=age)).isoformat(),
        "event": event,
        "status": status,
        "conclusion": conclusion,
        "head_branch": branch,
    }


class CleanProspectiveWatchdogTests(unittest.TestCase):
    def test_wakeup_only_dispatches_after_actual_clean_slot(self):
        # A main push is not a missed cron. Do not race a newly due
        # scheduled run, including the exceptional 22:28 final attempt.
        jst = timezone(timedelta(hours=9))
        cases = (
            (7, 0, False), (7, 3, False),
            (7, 4, False), (7, 5, False), (7, 9, False),
            (7, 10, True), (7, 17, True), (7, 18, False),
            (7, 19, False), (7, 24, False), (7, 25, True),
            (21, 59, True), (22, 0, True), (22, 3, False),
            (22, 4, False), (22, 9, False), (22, 10, True),
            (22, 18, False), (22, 19, False), (22, 25, True),
            (22, 27, True), (22, 28, False), (22, 29, True),
            (22, 32, True), (22, 33, False), (22, 44, False),
        )
        for hour, minute, expected in cases:
            with self.subTest(hour=hour, minute=minute):
                now = datetime(2026, 11, 5, hour, minute, tzinfo=jst)
                self.assertEqual(decide([], now, "push", MAIN), expected)
        # This also applies to a legitimate independent wakeup.
        from scripts.clean_prospective_watchdog import trusted_schedule_completion
        self.assertTrue(trusted_schedule_completion({
            "workflow_run": {"name": "Preview capture (schedule)",
                             "event": "schedule", "head_branch": "main",
                             "status": "completed", "conclusion": "success",
                             "head_repository": {"full_name":
                                "ikst2512-eng/boat-edge-clean"}}
        }, "ikst2512-eng/boat-edge-clean"))

    def test_no_fetch_before_first_scheduled_capture(self):
        from scripts import clean_prospective_watchdog as mod
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(mod, "OUTPUT", Path(tmp) / "decision.json"), \
                 patch.dict("os.environ", {
                     "GITHUB_EVENT_NAME": "push",
                     "GITHUB_REF": MAIN,
                     "GITHUB_RUN_ID": "20261105",
                 }), \
                 patch.object(mod, "fetch_runs") as fetch, \
                 patch.object(mod, "datetime") as clock:
                clock.now.return_value = datetime(
                    2026, 11, 4, 22, 0, tzinfo=timezone.utc)
                mod.main()
                fetch.assert_not_called()
                decision = json.loads((Path(tmp) / "decision.json").read_text())
                self.assertEqual(decision["action"], "no_dispatch")

    def test_missing_unattended_slot_triggers_bounded_main_only_recovery(self):
        self.assertTrue(decide([], NOW, "schedule", MAIN))
        self.assertTrue(decide([run(20)], NOW, "push", MAIN))
        self.assertFalse(decide([run(13)], NOW, "push", MAIN))

    def test_failed_cron_retries_but_failed_manual_has_cooldown(self):
        self.assertTrue(decide(
            [run(5, conclusion="failure")], NOW, "schedule", MAIN))
        self.assertFalse(decide(
            [run(5, event="workflow_dispatch", conclusion="failure")],
            NOW, "schedule", MAIN))
        self.assertTrue(decide(
            [run(15, event="workflow_dispatch", conclusion="failure")],
            NOW, "schedule", MAIN))

    def test_active_old_job_blocks_duplicates(self):
        self.assertFalse(decide(
            [run(30, status="queued", conclusion=None)], NOW, "schedule", MAIN))
        self.assertFalse(decide(
            [run(30, status="in_progress", conclusion=None)], NOW, "push", MAIN))
        self.assertTrue(decide(
            [run(121, status="queued", conclusion=None)], NOW, "push", MAIN))

    def test_pr_nonmain_and_offhours_never_dispatch(self):
        self.assertFalse(decide([], NOW, "pull_request", MAIN))
        self.assertFalse(decide([], NOW, "workflow_dispatch", "refs/heads/feature"))
        self.assertFalse(decide([], NOW - timedelta(hours=3), "schedule", MAIN))
        self.assertFalse(decide([], NOW + timedelta(hours=14), "schedule", MAIN))

    def test_night_race_end_hour_and_cooldown(self):
        # CLEAN final slot is 22:28 and its rescue is at 22:29; 23:15 is outside hours.
        late = NOW + timedelta(hours=12)
        last = NOW + timedelta(hours=13, minutes=14)
        after = NOW + timedelta(hours=14)
        self.assertTrue(decide([], late, 'schedule', MAIN))
        self.assertTrue(decide([], last, 'workflow_dispatch', MAIN))
        self.assertFalse(decide([], after, 'schedule', MAIN))
        self.assertFalse(decide([{
            'created_at': (last - timedelta(minutes=1)).isoformat(),
            'event': 'workflow_dispatch', 'status': 'completed',
            'conclusion': 'failure', 'head_branch': 'main',
        }], last, 'schedule', MAIN))

    def test_last_2228_slot_is_not_masked_by_2219_success(self):
        last = datetime(2026, 11, 4, 13, 29, tzinfo=timezone.utc)  # 22:29 JST
        def observed(minute, event="schedule", status="completed",
                     conclusion="success"):
            return {
                "created_at": last.replace(minute=minute).isoformat(),
                "event": event, "status": status,
                "conclusion": conclusion, "head_branch": "main",
            }
        # Earlier completed attempts belong to the 22:19 slot, not 22:28.
        self.assertTrue(decide([observed(19)], last, "schedule", MAIN))
        self.assertTrue(decide([observed(19, "workflow_dispatch")],
                               last, "push", MAIN))
        # The real 22:28 schedule, same-slot fallback, and older active
        # writer still prevent redundant dispatch.
        self.assertFalse(decide([observed(28)], last, "schedule", MAIN))
        self.assertFalse(decide([observed(28, "workflow_dispatch",
                                          conclusion="failure")],
                                last, "push", MAIN))
        self.assertFalse(decide([observed(19, status="queued",
                                          conclusion=None)],
                                last, "schedule", MAIN))
        # Before the dedicated 22:29 check, ordinary 14m policy is unchanged.
        self.assertFalse(decide([observed(19)],
                                last - timedelta(minutes=1), "schedule", MAIN))

    def test_feature_branch_manual_and_pr_runs_do_not_mask_missed_main(self):
        events = [
            run(2, event="workflow_dispatch", branch="experiment"),
            run(2, event="pull_request", branch="main"),
            run(2, event="push", branch="main"),
        ]
        self.assertTrue(decide(events, NOW, "schedule", MAIN))
        events.append(run(3, event="schedule", branch="main"))
        self.assertFalse(decide(events, NOW, "schedule", MAIN))

    def test_independent_schedule_completion_wakes_only_main_capture(self):
        repo = "ikst2512-eng/boat-edge-clean"
        allowed = (
            "Four-mode prospective capture (research only)",
            "CLEAN independent daily schedule capture",
            "Preview capture (schedule)",
            "CLEAN live official trifecta odds probe",
            "Entry research T-minus-12 baseline archival",
            "Research independent late preview evidence",
            "Entry course missed-cron activation watchdog",
            "Hole cumulative evidence rollup (research only)",
            "Hole future shadow batch evidence (research only)",
        )
        for source in allowed:
            with self.subTest(source=source):
                parent = {"workflow_run": {
                    "name": source,
                    "event": "schedule",
                    "head_branch": "main",
                    "status": "completed",
                    "conclusion": "success",
                    "head_repository": {"full_name": repo},
                    "id": 987,
                }}
                self.assertTrue(decide(
                    [], NOW, "workflow_run", MAIN,
                    trigger=parent, repository=repo))
                self.assertFalse(decide(
                    [run(5)], NOW, "workflow_run", MAIN,
                    trigger=parent, repository=repo))
                self.assertFalse(decide(
                    [run(3, status="in_progress", conclusion=None)],
                    NOW, "workflow_run", MAIN,
                    trigger=parent, repository=repo))

    def test_entry_watchdog_parent_requires_real_schedule_and_same_repo(self):
        repo = "ikst2512-eng/boat-edge-clean"
        original = {
            "name": "Entry course missed-cron activation watchdog",
            "event": "schedule",
            "head_branch": "main",
            "status": "completed",
            "conclusion": "success",
            "head_repository": {"full_name": repo},
        }
        self.assertTrue(decide(
            [], NOW, "workflow_run", MAIN,
            trigger={"workflow_run": original}, repository=repo))
        for field, bad in (
            ("event", "workflow_dispatch"),
            ("event", "pull_request"),
            ("event", "push"),
            ("head_branch", "feature"),
            ("status", "in_progress"),
            ("conclusion", "failure"),
            ("head_repository", {"full_name": "foreign/fork"}),
        ):
            with self.subTest(field=field, bad=bad):
                self.assertFalse(decide(
                    [], NOW, "workflow_run", MAIN,
                    trigger={"workflow_run": {**original, field: bad}},
                    repository=repo))

    def test_independent_wakeup_rejects_wrong_source_type_or_repo(self):
        repo = "ikst2512-eng/boat-edge-clean"
        valid = {
            "name": "Preview capture (schedule)",
            "event": "schedule",
            "head_branch": "main",
            "status": "completed",
            "conclusion": "success",
            "head_repository": {"full_name": repo},
        }
        self.assertFalse(decide([], NOW, "workflow_run", MAIN, repository=repo))
        self.assertFalse(decide(
            [], NOW, "workflow_run", "refs/heads/feature",
            trigger={"workflow_run": valid}, repository=repo))
        for prop, bad in (
            ("name", "Attacker PR"),
            ("event", "pull_request"),
            ("event", "workflow_dispatch"),
            ("head_branch", "feature"),
            ("status", "in_progress"),
            ("conclusion", "failure"),
            ("head_repository", {"full_name": "attacker/fork"}),
        ):
            with self.subTest(prop=prop, bad=bad):
                self.assertFalse(decide(
                    [], NOW, "workflow_run", MAIN,
                    trigger={"workflow_run": {**valid, prop: bad}},
                    repository=repo))
        self.assertFalse(decide(
            [], NOW - timedelta(hours=3), "workflow_run", MAIN,
            trigger={"workflow_run": valid}, repository=repo))

    def test_independent_wakeup_is_clean_only_and_does_not_expand_cron(self):
        workflow = Path(".github/workflows/four-mode-capture-watchdog.yml").read_text()
        self.assertIn("workflow_run:", workflow)
        self.assertIn("types: [completed]", workflow)
        for name in (
            "Four-mode prospective capture (research only)",
            "CLEAN independent daily schedule capture",
            "Preview capture (schedule)",
            "CLEAN live official trifecta odds probe",
            "Entry research T-minus-12 baseline archival",
            "Research independent late preview evidence",
            "Entry course missed-cron activation watchdog",
        ):
            self.assertIn("- '" + name + "'", workflow)
        self.assertIn("github.event.workflow_run.event == 'schedule'", workflow)
        self.assertIn("github.event.workflow_run.head_branch == 'main'", workflow)
        self.assertIn("github.event.workflow_run.conclusion == 'success'", workflow)
        self.assertIn("github.event_name != 'workflow_run'", workflow)
        self.assertIn("cron: '13,28,43,58 22-23,0-12 * * *'", workflow)
        self.assertIn("run: python -m scripts.clean_prospective_watchdog", workflow)
        self.assertIn("cron: '13,29,44 13 * * *'", workflow)

    def test_late_preview_parent_is_an_existing_independent_schedule(self):
        independent = Path(
            ".github/workflows/research-live-preview-evidence.yml"
        ).read_text(encoding="utf-8")
        self.assertIn("name: Research independent late preview evidence", independent)
        self.assertIn("  schedule:", independent)
        # The watcher does not react to this parent's PR/manual jobs:
        # only verified successful same-repository main schedule completions.
        self.assertIn("    - cron: '1-56/5 0-12 * * *'", independent)

    def test_untrusted_workflow_run_writes_no_dispatch_evidence_without_api(self):
        from scripts import clean_prospective_watchdog as mod
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp)
            payload=base/"event.json"
            payload.write_text(json.dumps({"workflow_run": {
                "name": "Preview capture (schedule)",
                "event": "pull_request",
                "head_branch": "main",
                "status": "completed",
                "conclusion": "success",
                "head_repository": {"full_name": "ikst2512-eng/boat-edge-clean"},
            }}))
            with patch.object(mod, "OUTPUT", base/"decision.json"), \
                 patch.dict("os.environ", {
                     "GITHUB_EVENT_NAME": "workflow_run",
                     "GITHUB_REF": MAIN,
                     "GITHUB_RUN_ID": "987",
                     "GITHUB_EVENT_PATH": str(payload),
                     "GH_REPOSITORY": "ikst2512-eng/boat-edge-clean",
                 }), \
                 patch.object(mod, "fetch_runs") as fetch:
                mod.main()
                fetch.assert_not_called()
            report = json.loads((base/"decision.json").read_text())
            self.assertEqual(report["action"], "no_dispatch")
            self.assertFalse(report["new_forecast_saved_proven"])

    def test_evidence_written_even_when_no_dispatch(self):
        from scripts import clean_prospective_watchdog as mod
        with tempfile.TemporaryDirectory() as tmp, \
             patch.object(mod, "OUTPUT", Path(tmp) / "decision.json"), \
             patch.dict("os.environ", {
                 "GITHUB_EVENT_NAME": "pull_request",
                 "GITHUB_REF": MAIN,
                 "GITHUB_RUN_ID": "321",
             }):
            mod.main()
            record = json.loads((Path(tmp) / "decision.json").read_text())
        self.assertEqual(record["action"], "no_dispatch")
        self.assertFalse(record["new_forecast_saved_proven"])
        self.assertFalse(record["remote_first_seen_verified"])
        self.assertFalse(record["formal"])

    def test_exact_workflow_module_entrypoint_executes(self):
        # Running a package file as a bare script changes sys.path on Actions:
        # the sibling 'scripts' package is then missing. Exercise the exact
        # module invocation instead of relying only on imported unit tests.
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(__file__).resolve().parent
            env = {
                **os.environ,
                "PYTHONPATH": str(repo_root),
                "GITHUB_EVENT_NAME": "pull_request",
                "GITHUB_REF": MAIN,
                "GITHUB_RUN_ID": "321",
            }
            run = subprocess.run(
                [sys.executable, "-m", "scripts.clean_prospective_watchdog"],
                cwd=tmp, env=env, capture_output=True, text=True,
            )
            self.assertEqual(run.returncode, 0, run.stderr)
            report = json.loads(
                (Path(tmp) / "four-mode-evidence" /
                 "clean-prospective-watchdog-decision.json").read_text())
            self.assertEqual(report["action"], "no_dispatch")

    def test_pr_and_untrusted_parent_cannot_block_operational_watchdog_queue(self):
        workflow = Path(".github/workflows/four-mode-capture-watchdog.yml").read_text()
        concurrency = workflow.split("concurrency:", 1)[1].split("jobs:", 1)[0]
        # The same operational group must serialize main push, schedule and
        # trusted scheduled-workflow completions to prevent double dispatch.
        self.assertIn("'four-mode-watchdog-main'", concurrency)
        self.assertIn("github.event_name == 'pull_request'", concurrency)
        self.assertIn("format('four-mode-watchdog-pr-{0}', github.run_id)", concurrency)
        self.assertIn("github.event_name == 'workflow_run'", concurrency)
        self.assertIn("github.event.workflow_run.event != 'schedule'", concurrency)
        self.assertIn("github.event.workflow_run.head_branch != 'main'", concurrency)
        self.assertIn("github.event.workflow_run.conclusion != 'success'", concurrency)
        self.assertIn("format('four-mode-watchdog-ineligible-{0}', github.run_id)", concurrency)
        self.assertIn("cancel-in-progress: false", concurrency)
        self.assertIn("queue: max", concurrency)
        # No additional wake-up schedule or authorization added by isolation.
        self.assertEqual(workflow.count("- cron:"), 4)
        self.assertIn("if: ${{ github.event_name != 'workflow_run'", workflow)

    def test_expired_kiryu12_recovery_skips_unrelated_future_schedules(self):
        # A Nov-3-only forensic recovery was actually triggered by the
        # 2026-11-04 23:25 JST four-mode schedule (run 41847531763).
        # Its expiry is not a failure of the healthy future collector.
        flow = Path(
            ".github/workflows/t12-kiryu12-upstream-recovery-20261103.yml"
        ).read_text(encoding="utf-8")
        self.assertIn(
            "startsWith(github.event.workflow_run.run_started_at, "
            "'2026-11-03T')", flow)
        self.assertIn(
            "github.event.workflow_run.event == 'schedule'", flow)
        self.assertIn(
            "github.event.workflow_run.head_branch == 'main'", flow)
        self.assertIn("check_window(datetime.now(timezone.utc)", flow)
        self.assertIn("--race-code 202611030112", flow)

    def test_workflow_reuses_existing_schedule_and_immutable_collector(self):
        p = Path(".github/workflows/four-mode-capture-watchdog.yml")
        workflow = p.read_text(encoding="utf-8")
        self.assertIn("run: python -m scripts.clean_prospective_watchdog", workflow)
        self.assertIn("cron: '13,29,44 13 * * *'", workflow)
        # Explicit always() overrides GitHub's implicit success() condition:
        # a separate Four-mode/V2 API failure must not skip CLEAN recovery.
        self.assertIn("id: policy_tests", workflow)
        self.assertIn("always() && steps.policy_tests.outcome == 'success'", workflow)
        policy_pos = workflow.index("- name: Test dispatch policy")
        other_pos = workflow.index("- name: Check recent capture runs before fallback dispatch")
        clean_pos = workflow.index("- name: Recover missed CLEAN prospective capture")
        self.assertLess(policy_pos, other_pos)
        self.assertLess(other_pos, clean_pos)
        condition = workflow[clean_pos:workflow.index("- name: Preserve watchdog decision evidence", clean_pos)]
        self.assertIn("github.event_name != 'pull_request'", condition)
        self.assertIn("github.ref == 'refs/heads/main'", condition)

        self.assertIn("test_clean_prospective_watchdog", workflow)
        self.assertIn("four-mode-evidence/clean-prospective-watchdog-decision.json",
                      workflow)
        self.assertIn("cron: '13,28,43,58 22-23,0-12 * * *'", workflow)
        self.assertIn("gh workflow run clean-prospective-evaluation.yml",
                      Path(".github/workflows/clean-prospective.yml").read_text())


if __name__ == "__main__":
    unittest.main()

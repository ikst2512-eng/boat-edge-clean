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
        self.assertFalse(decide([], NOW + timedelta(hours=12), "schedule", MAIN))

    def test_feature_branch_manual_and_pr_runs_do_not_mask_missed_main(self):
        events = [
            run(2, event="workflow_dispatch", branch="experiment"),
            run(2, event="pull_request", branch="main"),
            run(2, event="push", branch="main"),
        ]
        self.assertTrue(decide(events, NOW, "schedule", MAIN))
        events.append(run(3, event="schedule", branch="main"))
        self.assertFalse(decide(events, NOW, "schedule", MAIN))

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

    def test_workflow_reuses_existing_schedule_and_immutable_collector(self):
        p = Path(".github/workflows/four-mode-capture-watchdog.yml")
        workflow = p.read_text(encoding="utf-8")
        self.assertIn("run: python -m scripts.clean_prospective_watchdog", workflow)
        self.assertIn("test_clean_prospective_watchdog", workflow)
        self.assertIn("four-mode-evidence/clean-prospective-watchdog-decision.json",
                      workflow)
        self.assertIn("cron: '12,27,42,57 22-23,0-11 * * *'", workflow)
        self.assertIn("gh workflow run clean-prospective-evaluation.yml",
                      Path(".github/workflows/clean-prospective.yml").read_text())


if __name__ == "__main__":
    unittest.main()

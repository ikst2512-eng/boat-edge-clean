import json
import tempfile
import unittest
from pathlib import Path

from scripts.report_four_mode_watchdog_artifact_decisions import inspect


def run(run_id=10, event="push"):
    return {"id": run_id, "workflow": "four-mode-capture-watchdog.yml",
            "event": event, "created_at": "2026-11-03T06:23:49+00:00",
            "status": "completed", "conclusion": "success"}


def capture(run_id=20, at="2026-11-03T06:24:08+00:00"):
    return {"id": run_id, "event": "workflow_dispatch", "created_at": at}


def write(root, run_id, action="fallback_dispatch_accepted", **overrides):
    file = root / "four-mode-evidence/watchdog-decision.json"
    file.parent.mkdir(parents=True)
    file.write_text(json.dumps({
        "schema": "FOUR_MODE_WATCHDOG_DECISION_V1",
        "github_run_id": str(run_id), "github_event": "push",
        "checked_at_utc": "2026-11-03T06:24:08+00:00",
        "dry_run": False, "action": action, **overrides
    }), encoding="utf-8")


class ArtifactDecisionTests(unittest.TestCase):
    def test_accepted_decision_with_temporal_capture_not_causal_proof(self):
        history = {"recent_watchdog_runs": [run()],
                   "recent_capture_runs": [capture(), capture(21, "2026-11-03T06:27:09+00:00")]}
        def download(run_id, dest):
            write(dest, run_id)
        result = inspect(history, download)
        self.assertEqual(result["fallback_accepted_verified"], 1)
        self.assertEqual(result["runs"][0]["temporally_following_dispatch_ids"], [20])
        self.assertFalse(result["causal_link_proven"])
        self.assertFalse(result["remote_publication_proven"])

    def test_no_dispatch_not_reclassified_as_recovery(self):
        result = inspect({"recent_watchdog_runs": [run()], "recent_capture_runs": [capture()]},
                         lambda run_id, root: write(root, run_id, action="no_dispatch"))
        self.assertEqual(result["no_dispatch_verified"], 1)
        self.assertEqual(result["fallback_accepted_verified"], 0)
        self.assertEqual(result["runs"][0]["temporally_following_dispatch_ids"], [])

    def test_missing_artifact_is_unknown(self):
        history = {"recent_watchdog_runs": [run()], "recent_capture_runs": []}
        def download(run_id, root):
            raise OSError("not available")
        result = inspect(history, download)
        self.assertEqual(result["unknown_evidence"], 1)
        self.assertEqual(result["artifact_decisions_verified"], 0)
        self.assertIsNone(result["runs"][0]["decision"])

    def test_mismatched_run_id_and_dry_run_are_rejected(self):
        history = {"recent_watchdog_runs": [run()], "recent_capture_runs": []}
        result = inspect(history, lambda run_id, root: write(root, run_id + 1))
        self.assertEqual(result["unknown_evidence"], 1)
        result = inspect(history, lambda run_id, root: write(root, run_id, dry_run=True))
        self.assertEqual(result["unknown_evidence"], 1)

    def test_invalid_and_duplicate_watchdog_entries_are_rejected(self):
        with self.assertRaises(ValueError):
            inspect({"recent_watchdog_runs": [run(), run()], "recent_capture_runs": []},
                    lambda *_: None)
        with self.assertRaises(ValueError):
            inspect({"recent_watchdog_runs": [run(True)], "recent_capture_runs": []},
                    lambda *_: None)

    def test_only_bounded_recent_watchdogs_checked(self):
        history = {"recent_watchdog_runs": [run(3), run(2), run(1)],
                   "recent_capture_runs": []}
        result = inspect(history, lambda run_id, root: write(root, run_id),
                         limit=2)
        self.assertEqual(result["runs_checked"], 2)
        self.assertEqual(result["artifact_decisions_verified"], 2)


if __name__ == "__main__":
    unittest.main()

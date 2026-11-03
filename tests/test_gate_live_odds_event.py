"""Fail-closed tests for scheduled-upstream odds fallback."""
import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
spec = importlib.util.spec_from_file_location("gate_live_odds_event", SCRIPTS / "gate_live_odds_event.py")
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)


class FallbackGateTests(unittest.TestCase):
    def test_only_approved_schedule_upstream_is_operational(self):
        allowed = {"event": "workflow_run", "upstream_event": "schedule",
                   "upstream_workflow": gate.UPSTREAM, "upstream_branch": "main",
                   "upstream_run_id": 123}
        self.assertTrue(gate.eligible("workflow_run", allowed))
        self.assertTrue(gate.eligible("schedule", {"event": "schedule"}))
        self.assertTrue(gate.eligible("workflow_dispatch", {"event": "workflow_dispatch"}))
        self.assertTrue(gate.eligible("pull_request", {"event": "pull_request"}))
        for key, val in (("upstream_event", "push"), ("upstream_event", "pull_request"),
                         ("upstream_branch", "feature"), ("upstream_workflow", "unknown"),
                         ("upstream_run_id", None)):
            bad = dict(allowed)
            bad[key] = val
            self.assertFalse(gate.eligible("workflow_run", bad))
        self.assertFalse(gate.eligible("workflow_run", {}))

    def test_non_schedule_upstream_is_marked_ineligible_not_success(self):
        old = os.getcwd()
        with tempfile.TemporaryDirectory() as folder:
            try:
                os.chdir(folder)
                Path("event.json").write_text(json.dumps({"workflow_run": {
                    "id": 30, "event": "push", "name": gate.UPSTREAM, "head_branch": "main"}}))
                with patch.dict(os.environ, {
                    "GITHUB_EVENT_NAME": "workflow_run",
                    "GITHUB_EVENT_PATH": str(Path(folder) / "event.json"),
                    "GITHUB_OUTPUT": str(Path(folder) / "output")
                }):
                    gate.main()
                evidence = json.loads(Path("live_odds_metrics.json").read_text())
                self.assertEqual(evidence["source_status"], "fallback_ineligible")
                self.assertEqual(evidence["samples"], [])
                self.assertTrue(evidence["checked_at_jst"].endswith("+09:00"))
                self.assertIn("collect=false", Path("output").read_text())
            finally:
                os.chdir(old)


if __name__ == "__main__":
    unittest.main()

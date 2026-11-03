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
        from datetime import datetime, timezone
        allowed = {"event": "workflow_run", "upstream_event": "schedule",
                   "upstream_workflow": gate.UPSTREAM, "upstream_branch": "main",
                   "upstream_run_id": 123, "upstream_created_at": "2026-11-03T03:45:00Z"}
        now = datetime(2026, 11, 3, 3, 50, tzinfo=timezone.utc)
        self.assertTrue(gate.eligible("workflow_run", allowed, now=now))
        self.assertTrue(gate.eligible("schedule", {"event": "schedule"}))
        self.assertTrue(gate.eligible("workflow_dispatch", {"event": "workflow_dispatch"}))
        self.assertTrue(gate.eligible("pull_request", {"event": "pull_request"}))
        for key, val in (("upstream_event", "push"), ("upstream_event", "pull_request"),
                         ("upstream_branch", "feature"), ("upstream_workflow", "unknown"),
                         ("upstream_run_id", None)):
            bad = dict(allowed)
            bad[key] = val
            self.assertFalse(gate.eligible("workflow_run", bad, now=now))
        self.assertFalse(gate.eligible("workflow_run", {}))

    def test_fallback_only_in_three_jst_catchup_windows(self):
        from datetime import datetime, timezone, timedelta
        base = {"event": "workflow_run", "upstream_event": "schedule",
                "upstream_workflow": gate.UPSTREAM, "upstream_branch": "main",
                "upstream_run_id": 123}
        jst = timezone(timedelta(hours=9))
        for hour in (12, 14, 16):
            for minute in (40, 45, 54):
                source = datetime(2026, 11, 3, hour, minute, tzinfo=jst)
                trigger = {**base, "upstream_created_at": source.isoformat()}
                self.assertTrue(gate.eligible("workflow_run", trigger,
                                              now=source + timedelta(minutes=3)))
            for minute in (25, 30, 39, 55):
                source = datetime(2026, 11, 3, hour, minute, tzinfo=jst)
                trigger = {**base, "upstream_created_at": source.isoformat()}
                self.assertFalse(gate.eligible("workflow_run", trigger,
                                               now=source + timedelta(minutes=3)))
        for value in (None, "bad", "2026-11-03T12:45:00"):
            trigger = {**base, "upstream_created_at": value}
            self.assertFalse(gate.eligible("workflow_run", trigger,
                                           now=datetime(2026, 11, 3, 3, 50, tzinfo=timezone.utc)))

    def test_reject_stale_and_future_fallback_upstream(self):
        from datetime import datetime, timezone, timedelta
        trigger = {"event": "workflow_run", "upstream_event": "schedule",
                   "upstream_workflow": gate.UPSTREAM, "upstream_branch": "main",
                   "upstream_run_id": 123, "upstream_created_at": "2026-11-03T03:45:00Z"}
        source = datetime(2026, 11, 3, 3, 45, tzinfo=timezone.utc)
        self.assertFalse(gate.eligible("workflow_run", trigger, now=source - timedelta(seconds=1)))
        self.assertFalse(gate.eligible("workflow_run", trigger, now=source + timedelta(hours=2)))

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

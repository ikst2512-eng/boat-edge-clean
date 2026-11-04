"""Regression tests: unavailable Git first-add provenance must not become holdout success."""
import importlib.util
import time
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("holdout_server", ROOT / "server.py")
server = importlib.util.module_from_spec(spec)
spec.loader.exec_module(server)


class HoldoutShallowGitTests(unittest.TestCase):
    def test_shallow_git_returns_explicit_unavailable_not_a_success(self):
        with patch.object(server, "_compute_holdout_status",
                          side_effect=ValueError("incomplete local git history")):
            with patch.dict(server._HOLDOUT_STATE, {
                "value": None, "expires": 0.0, "running": False,
                "started": time.monotonic(), "last_duration": None,
                "last_error": None}):
                server._refresh_holdout_status()
                status, payload = server.holdout_status()
        self.assertEqual(status, 503)
        self.assertEqual(payload["error"], "HOLDOUT_GIT_HISTORY_INCOMPLETE")
        self.assertIs(payload["retryable"], False)
        self.assertIs(payload["ok"], False)
        self.assertIs(payload["running"], False)
        self.assertEqual(payload["last_error_type"], "GIT_HISTORY_INCOMPLETE")
        self.assertNotIn("evaluated_holdout_races", payload)

    def test_other_errors_stay_retryable_and_never_masquerade_as_data(self):
        with patch.object(server, "_compute_holdout_status", side_effect=OSError("IO fail")):
            with patch.dict(server._HOLDOUT_STATE, {
                "value": None, "expires": 0.0, "running": False,
                "started": time.monotonic(), "last_duration": None,
                "last_error": None}):
                server._refresh_holdout_status()
                status, payload = server.holdout_status()
        self.assertEqual(status, 503)
        self.assertEqual(payload["error"], "HOLDOUT_UNAVAILABLE")
        self.assertIs(payload["retryable"], True)
        self.assertEqual(payload["last_error_type"], "OSError")


if __name__ == "__main__":
    unittest.main()

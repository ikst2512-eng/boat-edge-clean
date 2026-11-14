"""Contract tests: holdout computation cannot block an HTTP request."""
import threading
import time
import unittest
from unittest.mock import patch

import server


class HoldoutAsyncTests(unittest.TestCase):
    def test_real_shallow_checkout_recovers_history_without_changing_head_or_bytes(self):
        import subprocess
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as tmp:
            source, checkout = Path(tmp)/"source", Path(tmp)/"checkout"
            source.mkdir()
            def git(*args, cwd=source):
                return subprocess.check_output(["git", *args], cwd=cwd, text=True).strip()
            git("init", "-b", "main")
            git("config", "user.name", "Fixture")
            git("config", "user.email", "fixture@example.test")
            (source/"original.json").write_text('{"immutable":true}')
            git("add", ".")
            git("commit", "-m", "original")
            original = git("rev-parse", "HEAD")
            (source/"later.txt").write_text("later")
            git("add", ".")
            git("commit", "-m", "later")
            git("clone", "--depth=1", source.as_uri(), str(checkout))
            before = git("rev-parse", "HEAD", cwd=checkout)
            real_run = subprocess.run
            def local_fetch(command, **kwargs):
                command = list(command)
                if command[:2] != ["git", "fetch"]:
                    return real_run(command, **kwargs)
                self.assertEqual(command[-2], "https://github.com/ikst2512-eng/boat-edge-clean.git")
                command[-2] = source.as_uri()
                return real_run(command, **kwargs)
            with patch.dict(server.os.environ, {"RENDER":"true"}), patch.object(
                server, "ROOT", checkout), patch("subprocess.run", side_effect=local_fetch):
                server._prepare_holdout_history()
            self.assertEqual(git("rev-parse", "--is-shallow-repository", cwd=checkout), "false")
            self.assertEqual(git("rev-parse", "HEAD", cwd=checkout), before)
            self.assertEqual(git("show", original+":original.json", cwd=checkout), '{"immutable":true}')
            self.assertEqual(git("status", "--porcelain", cwd=checkout), "")

    def test_render_history_fetch_is_bounded_and_never_checks_out_files(self):
        import subprocess
        with patch.dict(server.os.environ, {"RENDER": "true"}), patch(
            "subprocess.check_output", return_value="true\n"), patch("subprocess.run") as run:
            server._prepare_holdout_history()
        args, kwargs = run.call_args
        self.assertEqual(args[0], ["git", "fetch", "--unshallow", "--no-tags",
            "https://github.com/ikst2512-eng/boat-edge-clean.git", "main"])
        self.assertEqual(kwargs["timeout"], 90)
        self.assertTrue(kwargs["check"])
        self.assertEqual(kwargs["env"]["GIT_TERMINAL_PROMPT"], "0")

    def test_complete_history_and_non_render_never_fetch(self):
        with patch.dict(server.os.environ, {"RENDER": "true"}), patch(
            "subprocess.check_output", return_value="false\n"), patch("subprocess.run") as run:
            server._prepare_holdout_history()
            run.assert_not_called()
        with patch.dict(server.os.environ, {"RENDER": ""}), patch("subprocess.run") as run:
            server._prepare_holdout_history()
            run.assert_not_called()

    def test_history_failure_never_runs_evaluation(self):
        import subprocess
        with patch.object(server, "_prepare_holdout_history", side_effect=
            subprocess.TimeoutExpired("git", 90)), patch.object(server, "_compute_holdout_status") as compute:
            server._refresh_holdout_status()
        compute.assert_not_called()
        with server._HOLDOUT_LOCK:
            self.assertIsNone(server._HOLDOUT_STATE["value"])
            self.assertEqual(server._HOLDOUT_STATE["last_error"], "TimeoutExpired")

    def setUp(self):
        with server._HOLDOUT_LOCK:
            server._HOLDOUT_STATE.update(value=None, expires=0.0, running=False,
                                         started=None, last_duration=None, last_error=None)

    def test_first_request_is_nonblocking_and_fail_closed(self):
        gate = threading.Event()
        entered = threading.Event()
        def slow():
            entered.set()
            gate.wait(timeout=5)
            return {"schema": "CLEAN_SIGNAL70_HOLDOUT_STATUS_V1", "later_holdout_days": 1,
                    "evaluated_holdout_races": 3, "discovery_day": "20261029",
                    "independently_validated": False}
        try:
            with patch.object(server, "_compute_holdout_status", side_effect=slow):
                before = time.monotonic()
                status, data = server.holdout_status()
                self.assertLess(time.monotonic() - before, 0.5)
                self.assertEqual(status, 503)
                self.assertEqual(data["error"], "HOLDOUT_PENDING")
                self.assertTrue(data["running"])
                self.assertGreaterEqual(data["elapsed_seconds"], 0)
                self.assertEqual(data["worker_pid"], server.os.getpid())
                self.assertGreaterEqual(data["process_uptime_seconds"], 0)
                self.assertTrue(entered.wait(timeout=1))
                self.assertEqual(server.holdout_status()[0], 503)
                gate.set()
                deadline = time.monotonic() + 2
                while time.monotonic() < deadline and server.holdout_status()[0] != 200:
                    time.sleep(0.01)
                status, data = server.holdout_status()
                self.assertEqual(status, 200)
                self.assertEqual(data["evaluated_holdout_races"], 3)
        finally:
            gate.set()

    def test_status_only_audits_later_holdout_days(self):
        from unittest.mock import patch
        from pathlib import Path
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "prospective_predictions"
            folder.mkdir()
            for day in ("20261028", "20261029", "20261030", "20261101"):
                (folder / (day + "0101.json")).write_text("{}", encoding="utf-8")
            with patch.object(server, "ROOT", Path(tmp)):
                with patch("audit_clean_first_add.bulk_first_add", return_value=__import__("contextlib").nullcontext()), patch("audit_clean_first_add.inspect", side_effect=ValueError("unambiguous first addition not found")), patch("compare_topn_signal70_days.report", return_value={
                        "later_holdout_days": 2, "later_holdout_evaluated_races": 4}) as report:
                    status = server._compute_holdout_status()
        report.assert_called_once_with(["20261030", "20261101"])
        self.assertEqual(status["later_holdout_days"], 2)
        self.assertEqual(status["evaluated_holdout_races"], 4)
        self.assertFalse(status["first_add_probes"]["202610301306"]["ok"])
        self.assertEqual(status["first_add_probes"]["202610301306"]["reason_detail"],
                         "unambiguous first addition not found")
        self.assertFalse(status["independently_validated"])

    def test_holdout_outcomes_are_separate_from_validated_evaluation(self):
        from pathlib import Path
        import tempfile
        from contextlib import nullcontext
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            folder = root / "prospective_predictions"
            folder.mkdir()
            (folder / "202610300101.json").write_text("{}", encoding="utf-8")
            payload = {"later_holdout_days": 1, "later_holdout_evaluated_races": 2,
                       "days": [{"archived": 5, "groups": {
                           "signal_70_plus": {"evaluated": 1, "awaiting_result": 1, "rejected": 1},
                           "below_70": {"evaluated": 1, "awaiting_result": 1, "rejected": 0}}}]}
            with patch.object(server, "ROOT", root), patch(
                "audit_clean_first_add.bulk_first_add", return_value=nullcontext()), patch("audit_clean_first_add.inspect", side_effect=ValueError("unambiguous first addition not found")), patch(
                "compare_topn_signal70_days.report", return_value=payload):
                result = server._compute_holdout_status()
        self.assertEqual(result["evaluated_holdout_races"], 2)
        self.assertEqual(result["awaiting_result_races"], 2)
        self.assertEqual(result["audit_rejected_races"], 1)
        self.assertEqual(result["archived_candidates"], 5)
        self.assertFalse(result["independently_validated"])

    def test_failure_does_not_invent_zero(self):
        with patch.object(server, "_compute_holdout_status", side_effect=ValueError("bad evidence")):
            status, data = server.holdout_status()
            self.assertEqual(status, 503)
            self.assertNotIn("evaluated_holdout_races", data)
            self.assertIn(data["error"], ("HOLDOUT_PENDING", "HOLDOUT_UNAVAILABLE"))
            deadline = time.monotonic() + 2
            while time.monotonic() < deadline:
                with server._HOLDOUT_LOCK:
                    if not server._HOLDOUT_STATE["running"]:
                        break
                time.sleep(0.01)
            with server._HOLDOUT_LOCK:
                self.assertFalse(server._HOLDOUT_STATE["running"])


if __name__ == "__main__":
    unittest.main()

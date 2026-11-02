"""Contract tests: holdout computation cannot block an HTTP request."""
import threading
import time
import unittest
from unittest.mock import patch

import server


class HoldoutAsyncTests(unittest.TestCase):
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
                self.assertEqual(data["error"], "HOLDOUT_PENDING")\n                self.assertTrue(data["running"])\n                self.assertGreaterEqual(data["elapsed_seconds"], 0)
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
                with patch("compare_topn_signal70_days.report", return_value={
                        "later_holdout_days": 2, "later_holdout_evaluated_races": 4}) as report:
                    status = server._compute_holdout_status()
        report.assert_called_once_with(["20261030", "20261101"])
        self.assertEqual(status["later_holdout_days"], 2)
        self.assertEqual(status["evaluated_holdout_races"], 4)
        self.assertFalse(status["independently_validated"])

    def test_failure_does_not_invent_zero(self):
        with patch.object(server, "_compute_holdout_status", side_effect=ValueError("bad evidence")):
            status, data = server.holdout_status()
            self.assertEqual(status, 503)
            self.assertNotIn("evaluated_holdout_races", data)\n            self.assertIn(data["error"], ("HOLDOUT_PENDING", "HOLDOUT_UNAVAILABLE"))
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

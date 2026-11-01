"""Contract tests: holdout computation cannot block an HTTP request."""
import threading
import time
import unittest
from unittest.mock import patch

import server


class HoldoutAsyncTests(unittest.TestCase):
    def setUp(self):
        with server._HOLDOUT_LOCK:
            server._HOLDOUT_STATE.update(value=None, expires=0.0, running=False)

    def test_first_request_is_nonblocking_and_fail_closed(self):
        gate = threading.Event()
        entered = threading.Event()
        def slow():
            entered.set()
            gate.wait(timeout=2)
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

    def test_failure_does_not_invent_zero(self):
        with patch.object(server, "_compute_holdout_status", side_effect=ValueError("bad evidence")):
            status, data = server.holdout_status()
            self.assertEqual(status, 503)
            self.assertNotIn("evaluated_holdout_races", data)


if __name__ == "__main__":
    unittest.main()

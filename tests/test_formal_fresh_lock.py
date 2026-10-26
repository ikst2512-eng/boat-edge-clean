"""Regression tests for the temporary Formal Fresh API lock (no result access)."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import server


class FormalFeedLockTests(unittest.TestCase):
    def test_head_health_never_fetches_predictions(self):
        from io import BytesIO
        handler = object.__new__(server.Handler)
        handler.path = "/healthz"
        handler.wfile = BytesIO()
        status = []
        headers = []
        handler.send_response = lambda code: status.append(code)
        handler.send_header = lambda key, value: headers.append((key, value))
        handler.end_headers = lambda: None
        with patch.object(server, "get_predictions", side_effect=AssertionError("HEAD triggered predictions")), \\
             patch.object(server, "get_odds", side_effect=AssertionError("HEAD triggered odds")):
            handler.do_HEAD()
        self.assertEqual(status, [200])
        self.assertEqual(handler.wfile.getvalue(), b"")
        self.assertIn(("Cache-Control", "no-store"), headers)

    def test_claimed_validated_feed_stays_unavailable(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            tickets = [f"{a}-{b}-{c}" for a in range(1, 7)
                       for b in range(1, 7) for c in range(1, 7)
                       if len({a, b, c}) == 3]
            record = {
                "validated": True,
                "model_version": "V1.21.20",
                "generated_at": "2026-10-27T00:00:00+09:00",
                "predictions": [{"ticket": t} for t in tickets],
            }
            (root / "predictions.json").write_text(
                json.dumps({"20261027-01-01": record}), encoding="utf-8")
            with patch.object(server, "ROOT", root):
                status, body = server.get_predictions(
                    {"hd": ["20261027"], "jcd": ["01"], "rno": ["1"]})
            self.assertEqual(status, 200)
            self.assertEqual(body["status"], "unavailable")
            self.assertIs(body["validated"], False)
            self.assertEqual(body["predictions"], [])

    def test_invalid_feed_is_never_available(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "predictions.json").write_text('{"bad": ', encoding="utf-8")
            with patch.object(server, "ROOT", root):
                status, body = server.get_predictions(
                    {"hd": ["20261027"], "jcd": ["01"], "rno": ["1"]})
            self.assertEqual(status, 503)
            self.assertEqual(body["status"], "error")
            self.assertEqual(body["predictions"], [])


if __name__ == "__main__":
    unittest.main()

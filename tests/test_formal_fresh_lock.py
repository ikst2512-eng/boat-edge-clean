"""Regression tests for the temporary Formal Fresh API lock (no result access)."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import server


class FormalFeedLockTests(unittest.TestCase):
    def test_head_requests_never_trigger_prediction_or_odds(self):
        from io import BytesIO
        with (patch.object(server, "get_predictions", side_effect=AssertionError("HEAD triggered predictions")),
              patch.object(server, "get_odds", side_effect=AssertionError("HEAD triggered odds"))):
            for path, expected in (("/healthz", 200), ("/", 200),
                                   ("/api/predictions", 404), ("/api/odds", 404)):
                with self.subTest(path=path):
                    handler = object.__new__(server.Handler)
                    handler.path = path
                    handler.wfile = BytesIO()
                    statuses = []
                    headers = []
                    handler.send_response = lambda code: statuses.append(code)
                    handler.send_header = lambda key, value: headers.append((key, value))
                    handler.end_headers = lambda: None
                    handler.do_HEAD()
                    self.assertEqual(statuses, [expected])
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

    def test_research_fallback_is_never_formal(self):
        with tempfile.TemporaryDirectory() as directory:
            research = {"ok": True, "status": "research", "validated": False,
                        "model_version": "exploratory", "predictions": ["1-2-3"]}
            with (patch.object(server, "ROOT", Path(directory)),
                  patch("research_model.predict", return_value=research)):
                status, body = server.get_predictions(
                    {"hd": ["20261027"], "jcd": ["01"], "rno": ["1"]})
            self.assertEqual(status, 200)
            self.assertEqual(body["status"], "research")
            self.assertIs(body["validated"], False)
            self.assertNotEqual(body["status"], "available")

    def test_research_fallback_strips_forged_approval_metadata(self):
        with tempfile.TemporaryDirectory() as directory:
            research = {"ok": True, "status": "research", "validated": False,
                        "predictions": ["1-2-3"], "model_version": "exploratory",
                        "formal_approved": True, "independent_receipt_verified": True,
                        "result_unlock_token": "fake"}
            with (patch.object(server, "ROOT", Path(directory)),
                  patch("research_model.predict", return_value=research)):
                status, body = server.get_predictions(
                    {"hd": ["20261027"], "jcd": ["01"], "rno": ["1"]})
            self.assertEqual(status, 200)
            self.assertEqual(body["status"], "research")
            self.assertIs(body["validated"], False)
            self.assertNotIn("formal_approved", body)
            self.assertNotIn("independent_receipt_verified", body)
            self.assertNotIn("result_unlock_token", body)

    def test_research_fallback_rejects_invalid_tickets(self):
        for tickets in ([], ["1-2-3", "1-2-3"], ["1-1-2"], ["9-2-3"],
                        ["1-2-3"] * 11, "1-2-3"):
            with self.subTest(tickets=tickets), tempfile.TemporaryDirectory() as directory:
                research = {"ok": True, "status": "research", "validated": False,
                            "predictions": tickets}
                with (patch.object(server, "ROOT", Path(directory)),
                      patch("research_model.predict", return_value=research)):
                    status, body = server.get_predictions(
                        {"hd": ["20261027"], "jcd": ["01"], "rno": ["1"]})
                self.assertEqual(status, 200)
                self.assertEqual(body["status"], "unavailable")
                self.assertEqual(body["predictions"], [])

    def test_research_fallback_cannot_self_promote(self):
        with tempfile.TemporaryDirectory() as directory:
            fake = {"ok": True, "status": "available", "validated": True,
                    "predictions": ["1-2-3"]}
            with (patch.object(server, "ROOT", Path(directory)),
                  patch("research_model.predict", return_value=fake)):
                status, body = server.get_predictions(
                    {"hd": ["20261027"], "jcd": ["01"], "rno": ["1"]})
            self.assertEqual(status, 200)
            self.assertEqual(body["status"], "unavailable")
            self.assertEqual(body["predictions"], [])

    def test_locked_feed_ignores_untrusted_ticket_content(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            record = {"validated": True, "predictions": [{"ticket": "invalid"}]}
            (root / "predictions.json").write_text(
                json.dumps({"20261027-01-01": record}), encoding="utf-8")
            with patch.object(server, "ROOT", root):
                status, body = server.get_predictions(
                    {"hd": ["20261027"], "jcd": ["01"], "rno": ["1"]})
            self.assertEqual(status, 200)
            self.assertEqual(body["status"], "unavailable")
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

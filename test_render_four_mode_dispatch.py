import io
import json
import unittest
from datetime import datetime, timedelta, timezone
from scripts.render_four_mode_dispatch import run

NOW = datetime(2026, 11, 3, 0, 0, tzinfo=timezone.utc)

class Response(io.BytesIO):
    status = 200
    def __enter__(self):
        return self
    def __exit__(self, *args):
        self.close()

class DispatchTests(unittest.TestCase):
    def test_missing_token_rejected(self):
        with self.assertRaises(ValueError):
            run(token="", now=NOW)

    def test_recent_success_prevents_dispatch(self):
        calls = []
        def request(req, timeout):
            calls.append(req)
            record = {"created_at": (NOW-timedelta(minutes=5)).isoformat(),
                      "status":"completed","conclusion":"success","event":"schedule"}
            return Response(json.dumps({"workflow_runs":[record]}).encode())
        result = run(token="test-only", now=NOW, request=request)
        self.assertEqual(result["action"],"no_dispatch")
        self.assertEqual(len(calls),2)

    def test_missing_runs_dispatches_once(self):
        calls = []
        def request(req, timeout):
            calls.append(req)
            if req.get_method() == "POST":
                response = Response(b"")
                response.status = 204
                return response
            return Response(b'{"workflow_runs":[]}')
        result=run(token="test-only", now=NOW, request=request)
        self.assertEqual(result["action"],"dispatch_accepted_not_publication_proof")
        self.assertEqual([c.get_method() for c in calls],["GET","GET","POST"])

    def test_outside_hours_does_not_dispatch(self):
        def request(req, timeout):
            self.assertEqual(req.get_method(),"GET")
            return Response(b'{"workflow_runs":[]}')
        self.assertEqual(run(token="test-only",now=NOW-timedelta(hours=4),request=request)["action"],"no_dispatch")

if __name__ == "__main__":
    unittest.main()

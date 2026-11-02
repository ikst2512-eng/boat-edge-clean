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

    def test_failed_fallback_uses_retry_cooldown(self):
        calls=[]
        def request(req, timeout):
            calls.append(req)
            record={"created_at":(NOW-timedelta(minutes=5)).isoformat(),
                    "status":"completed","conclusion":"failure",
                    "event":"workflow_dispatch"}
            if "event=workflow_dispatch" in req.full_url:
                return Response(json.dumps({"workflow_runs":[record]}).encode())
            return Response(b'{"workflow_runs":[]}')
        result=run(token="test-only",now=NOW,request=request)
        self.assertEqual(result["action"],"no_dispatch")
        self.assertEqual(len(calls),2)

    def test_failed_schedule_triggers_recovery(self):
        calls=[]
        def request(req, timeout):
            calls.append(req)
            if req.get_method()=="POST":
                response=Response(b"")
                response.status=204
                return response
            record={"created_at":(NOW-timedelta(minutes=5)).isoformat(),
                    "status":"completed","conclusion":"failure","event":"schedule"}
            return Response(json.dumps({"workflow_runs":[record]}).encode()
                            if "event=schedule" in req.full_url else b'{"workflow_runs":[]}')
        result=run(token="test-only",now=NOW,request=request)
        self.assertEqual(result["action"],"dispatch_accepted_not_publication_proof")
        self.assertEqual([c.get_method() for c in calls],["GET","GET","POST"])

    def test_dispatch_rejection_is_error_not_success(self):
        def request(req, timeout):
            if req.get_method()=="POST":
                return Response(b"")
            return Response(b'{"workflow_runs":[]}')
        with self.assertRaises(RuntimeError):
            run(token="test-only",now=NOW,request=request)

    def test_fifteen_minute_cycle_not_blocked_by_previous_success(self):
        calls=[]
        def request(req, timeout):
            calls.append(req)
            if req.get_method()=="POST":
                response=Response(b"")
                response.status=204
                return response
            record={"created_at":(NOW-timedelta(minutes=15)).isoformat(),
                    "status":"completed","conclusion":"success",
                    "event":"workflow_dispatch"}
            return Response(json.dumps({"workflow_runs":[record]}).encode()
                            if "event=workflow_dispatch" in req.full_url else b'{"workflow_runs":[]}')
        result=run(token="test-only",now=NOW,request=request)
        self.assertEqual(result["action"],"dispatch_accepted_not_publication_proof")
        self.assertEqual([c.get_method() for c in calls],["GET","GET","POST"])

    def test_recent_dispatch_still_prevents_duplicates(self):
        calls=[]
        def request(req, timeout):
            calls.append(req)
            record={"created_at":(NOW-timedelta(minutes=13)).isoformat(),
                    "status":"completed","conclusion":"failure",
                    "event":"workflow_dispatch"}
            return Response(json.dumps({"workflow_runs":[record]}).encode()
                            if "event=workflow_dispatch" in req.full_url else b'{"workflow_runs":[]}')
        self.assertEqual(run(token="test-only",now=NOW,request=request)["action"],"no_dispatch")
        self.assertEqual(len(calls),2)

    def test_outside_hours_does_not_dispatch(self):
        def request(req, timeout):
            self.fail("Off-hours job must not call GitHub API")
        result=run(token="test-only",now=NOW-timedelta(hours=4),request=request)
        self.assertEqual(result["action"],"no_dispatch")
        self.assertEqual(result["reason"],"outside_capture_hours")

if __name__ == "__main__":
    unittest.main()

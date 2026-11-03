import json
import unittest
from scripts.audit_four_mode_watchdog_decisions import inspect, parse_decision

HISTORY = {"recent_watchdog_runs": [
    {"id": 123, "created_at": "2026-11-03T05:20:00+00:00",
     "event": "push", "conclusion": "success"}]}

class WatchdogDecisionAuditTest(unittest.TestCase):
    def test_accepted_dispatch_has_a_real_log_and_not_publication_proof(self):
        def fetch(url, token, json_result=True):
            if "/runs/123/jobs" in url:
                return {"jobs": [{"id": 456, "name": "watchdog", "conclusion": "success"}]}
            self.assertIn("/jobs/456/logs", url)
            self.assertFalse(json_result)
            return ('2026-11-03T05:20:01Z FOUR_MODE_WATCHDOG=' +
                    json.dumps({"action": "fallback_dispatch_accepted",
                                "capture_hours_jst": True,
                                "recent_publication_runs": 0}))
        d = inspect(HISTORY, "example/repo", "fake", fetch)
        self.assertEqual(d["decisions_verified"], 1)
        self.assertEqual(d["fallback_dispatchs_accepted"], 1)
        self.assertEqual(d["accepted_run_ids"], [123])
        self.assertFalse(d["capture_trigger_attribution_proven"])
        self.assertFalse(d["remote_publication_proven"])

    def test_no_dispatch_does_not_claim_accepted(self):
        def fetch(url, token, json_result=True):
            if "/runs/" in url:
                return {"jobs": [{"id": 2, "name": "watchdog", "conclusion": "success"}]}
            return 'FOUR_MODE_WATCHDOG={"action": "no_dispatch", "fallback_retry_cooldown": true}'
        d = inspect(HISTORY, "example/repo", "fake", fetch)
        self.assertEqual(d["fallback_dispatchs_accepted"], 0)
        self.assertEqual(d["runs"][0]["decision"]["fallback_retry_cooldown"], True)

    def test_missing_log_marker_is_unknown_not_no_dispatch(self):
        def fetch(url, token, json_result=True):
            if "/runs/" in url:
                return {"jobs": [{"id": 2, "name": "watchdog", "conclusion": "success"}]}
            return "No publication run shown"
        d = inspect(HISTORY, "example/repo", "fake", fetch)
        self.assertEqual(d["decisions_verified"], 0)
        self.assertIsNone(d["runs"][0]["decision"])
        self.assertEqual(d["runs"][0]["evidence_status"], "decision_marker_unverified")

    def test_multiple_conflicting_log_markers_fail_closed(self):
        self.assertIsNone(parse_decision(
            'FOUR_MODE_WATCHDOG={"action":"no_dispatch"}\n'
            'FOUR_MODE_WATCHDOG={"action":"fallback_dispatch_accepted"}'))
        self.assertIsNone(parse_decision('FOUR_MODE_WATCHDOG={broken'))

    def test_no_watchdog_job_is_not_success(self):
        d = inspect(HISTORY, "example/repo", "fake", lambda *_: {"jobs": []})
        self.assertEqual(d["runs"][0]["evidence_status"], "missing_or_duplicate_watchdog_job")

    def test_network_error_is_not_success(self):
        def fetch(*_args, **_kwargs):
            raise OSError("unavailable")
        d = inspect(HISTORY, "example/repo", "fake", fetch)
        self.assertEqual(d["decisions_verified"], 0)
        self.assertEqual(d["runs"][0]["evidence_status"], "retrieval_error:OSError")

    def test_reject_bad_inputs(self):
        with self.assertRaises(ValueError):
            inspect({"recent_watchdog_runs": []}, "example/repo", "", lambda *_: {})
        with self.assertRaises(ValueError):
            inspect({"recent_watchdog_runs": [{"id": True}]}, "example/repo", "fake", lambda *_: {})

if __name__ == "__main__":
    unittest.main()

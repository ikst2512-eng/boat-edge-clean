"""Offline tests for live-odds evidence classification; never depend on production."""
import importlib.util
import io
import base64
import hashlib
import json
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.error import HTTPError

spec = importlib.util.spec_from_file_location("probe", Path(__file__).resolve().parents[1] / "scripts/probe_live_odds_health.py")
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)
NOW = datetime(2026, 11, 3, 5, 0, tzinfo=timezone.utc)
CODE = "202611030211"


class Response:
    status = 200

    def __init__(self, body):
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def read(self, limit):
        return json.dumps(self.body).encode()


def valid_body():
    return {"ok": True, "hd": "20261103", "jcd": "02", "rno": 11,
            "fetched_at": NOW.isoformat(), "odds": {key: 2.1 for key in probe.EXPECTED}}


class ProbeTests(unittest.TestCase):
    def receipt(self, *, seconds=0, deadline="2026-11-03T14:13:00+09:00"):
        raw = json.dumps(valid_body()).encode()
        return {"race_code": CODE, "source_deadline_jst": deadline,
                "final_state": "valid_200", "elapsed_ms": 1,
                "attempts": [{"http": 200, "state": "valid_200", "latency_ms": 1,
                    "started_at_utc": NOW.isoformat(),
                    "finished_at_utc": (NOW + timedelta(seconds=seconds)).isoformat(),
                    "response_base64": base64.b64encode(raw).decode(),
                    "response_sha256": hashlib.sha256(raw).hexdigest()}]}

    def test_replays_exact_120_odds_and_source_t12_separately(self):
        sample = self.receipt()
        self.assertEqual(probe.replay_receipt(sample),
                         {"response_verified": True, "before_source_t12": True})
        # Equality with T-12 is too late; response can still be valid odds.
        self.assertEqual(probe.replay_receipt(self.receipt(seconds=60)),
                         {"response_verified": True, "before_source_t12": False})
        for deadline in (None, "bad", "2026-11-03T14:13:00", "2026-11-04T14:13:00+09:00"):
            state = probe.replay_receipt(self.receipt(deadline=deadline))
            self.assertTrue(state["response_verified"])
            self.assertFalse(state["before_source_t12"])

    def test_changed_body_hash_and_incomplete_odds_fail_replay(self):
        sample = self.receipt()
        sample["attempts"][0]["response_sha256"] = "0" * 64
        self.assertFalse(probe.replay_receipt(sample)["response_verified"])
        sample = self.receipt()
        body = valid_body(); body["odds"].pop("1-2-3")
        raw = json.dumps(body).encode()
        sample["attempts"][0].update(response_base64=base64.b64encode(raw).decode(),
                                     response_sha256=hashlib.sha256(raw).hexdigest())
        self.assertFalse(probe.replay_receipt(sample)["response_verified"])
        sample["attempts"][0]["response_base64"] = "invalid!"
        self.assertFalse(probe.replay_receipt(sample)["response_verified"])

    def test_replay_summary_does_not_trust_claimed_verification_flags(self):
        sample = self.receipt()
        sample["receipt_verification"] = {"response_verified": False, "before_source_t12": False}
        self.assertEqual(probe.summarize([sample])["before_source_t12_races"], 1)
        sample["attempts"][0]["response_sha256"] = "0" * 64
        sample["receipt_verification"] = {"response_verified": True, "before_source_t12": True}
        self.assertEqual(probe.summarize([sample])["replayable_120_odds_races"], 0)

    def test_deadline_requires_one_consistent_same_race_source(self):
        row = {"レースコード": CODE, "電話投票締切予定": "14:13"}
        self.assertEqual(probe.source_deadline([row], CODE), "2026-11-03T14:13:00+09:00")
        self.assertEqual(probe.source_deadline([row, row], CODE), "2026-11-03T14:13:00+09:00")
        self.assertIsNone(probe.source_deadline([], CODE))
        self.assertIsNone(probe.source_deadline([row, {**row, "電話投票締切予定":"14:14"}], CODE))

    def test_attempts_save_real_request_and_response_timestamps(self):
        before = datetime.now(timezone.utc)
        result = probe.sample_race(
            CODE, request=lambda req, timeout: Response(valid_body()),
            now=NOW, pause=lambda _: None)
        after = datetime.now(timezone.utc)
        attempt = result["attempts"][0]
        started = datetime.fromisoformat(attempt["started_at_utc"])
        finished = datetime.fromisoformat(attempt["finished_at_utc"])
        self.assertEqual(started.utcoffset(), timedelta(0))
        self.assertEqual(finished.utcoffset(), timedelta(0))
        self.assertLessEqual(before, started)
        self.assertLessEqual(started, finished)
        self.assertLessEqual(finished, after)
        self.assertEqual(attempt["state"], "valid_200")
        raw = base64.b64decode(attempt["response_base64"], validate=True)
        self.assertEqual(hashlib.sha256(raw).hexdigest(), attempt["response_sha256"])
        self.assertEqual(json.loads(raw), valid_body())

    def test_pending_retry_saves_independent_attempt_timestamps(self):
        calls = []
        def request(req, timeout):
            calls.append(True)
            if len(calls) == 1:
                raise HTTPError(req.full_url, 202, "pending", {}, io.BytesIO())
            return Response(valid_body())
        result = probe.sample_race(CODE, request=request, now=NOW, pause=lambda _: None)
        self.assertEqual(len(result["attempts"]), 2)
        for attempt in result["attempts"]:
            self.assertIn("started_at_utc", attempt)
            self.assertIn("finished_at_utc", attempt)
        self.assertLessEqual(
            result["attempts"][0]["finished_at_utc"],
            result["attempts"][1]["started_at_utc"])

    def test_exact_odds_and_timestamp(self):
        self.assertTrue(probe.valid_odds(valid_body(), CODE, NOW))
        bad = valid_body()
        bad["odds"].pop("1-2-3")
        self.assertFalse(probe.valid_odds(bad, CODE, NOW))
        bad = valid_body()
        bad["fetched_at"] = (NOW - timedelta(hours=2)).isoformat()
        self.assertFalse(probe.valid_odds(bad, CODE, NOW))
        bad = valid_body()
        bad["rno"] = 12
        self.assertFalse(probe.valid_odds(bad, CODE, NOW))

    def test_pending_then_success(self):
        calls = []

        def request(req, timeout):
            calls.append(1)
            if len(calls) == 1:
                raise HTTPError(req.full_url, 202, "pending", {}, io.BytesIO())
            return Response(valid_body())

        result = probe.sample_race(CODE, request=request, now=NOW, pause=lambda _: None)
        self.assertEqual([r["http"] for r in result["attempts"]], [202, 200])
        self.assertEqual(result["final_state"], "valid_200")
        summary = probe.summarize([result])
        self.assertEqual(summary["initially_pending_races"], 1)
        self.assertEqual(summary["pending_recovered_to_valid_200"], 1)
        self.assertEqual(summary["pending_still_202"], 0)
        self.assertEqual(summary["pending_recovery_rate_pct"], 100.0)
        self.assertEqual(summary["first_attempt_valid_races"], 0)

    def test_non_json_pending_202_is_retried(self):
        calls = []
        class PendingResponse:
            status = 202
            def __enter__(self):
                return self
            def __exit__(self, *args):
                pass
            def read(self, limit):
                return b""
        def request(req, timeout):
            calls.append(True)
            return PendingResponse() if len(calls) == 1 else Response(valid_body())
        result = probe.sample_race(CODE, request=request, now=NOW, pause=lambda _: None)
        self.assertEqual([step["state"] for step in result["attempts"]],
                         ["pending_202", "valid_200"])
        self.assertEqual([step["http"] for step in result["attempts"]], [202, 200])

    def test_non_json_http_200_is_invalid_not_transport(self):
        class InvalidResponse:
            status = 200
            def __enter__(self):
                return self
            def __exit__(self, *args):
                pass
            def read(self, limit):
                return b"<not-json>"
        result = probe.sample_race(
            CODE, request=lambda req, timeout: InvalidResponse(), now=NOW,
            pause=lambda _: None)
        self.assertEqual(result["attempts"][0]["http"], 200)
        self.assertEqual(result["final_state"], "invalid_200")
        self.assertEqual(len(result["attempts"]), 1)

    def test_initial_timeout_gets_one_bounded_retry(self):
        calls = []
        def request(req, timeout):
            calls.append(timeout)
            if len(calls) == 1:
                raise TimeoutError("transient connection timeout")
            return Response(valid_body())
        result = probe.sample_race(CODE, request=request, now=NOW, pause=lambda _: None)
        self.assertEqual(len(calls), 2)
        self.assertEqual([step["state"] for step in result["attempts"]],
                         ["transport_error:TimeoutError", "valid_200"])
        self.assertEqual(result["final_state"], "valid_200")

    def test_repeated_timeout_stops_after_two_attempts(self):
        calls = []
        def request(req, timeout):
            calls.append(timeout)
            raise TimeoutError("persistent timeout")
        result = probe.sample_race(CODE, request=request, now=NOW, pause=lambda _: None)
        self.assertEqual(len(calls), 2)
        self.assertEqual(result["final_state"], "transport_error:TimeoutError")
        self.assertEqual(len(result["attempts"]), 2)

    def test_timeout_after_pending_does_not_trigger_unbounded_retries(self):
        calls = []
        def request(req, timeout):
            calls.append(timeout)
            if len(calls) == 1:
                raise HTTPError(req.full_url, 202, "pending", {}, io.BytesIO())
            raise TimeoutError("no response")
        result = probe.sample_race(CODE, request=request, now=NOW, pause=lambda _: None)
        self.assertEqual(len(calls), 2)
        self.assertEqual(result["final_state"], "transport_error:TimeoutError")

    def test_repeated_pending_not_success(self):
        def request(req, timeout):
            raise HTTPError(req.full_url, 202, "pending", {}, io.BytesIO())

        result = probe.sample_race(CODE, request=request, now=NOW, pause=lambda _: None)
        self.assertEqual(len(result["attempts"]), 3)
        self.assertEqual(result["final_state"], "pending_202")
        stats = probe.summarize([result])
        self.assertEqual(stats["http_counts"]["202"], 3)
        self.assertEqual(stats["valid_200_races"], 0)
        self.assertEqual(stats["initially_pending_races"], 1)
        self.assertEqual(stats["pending_still_202"], 1)
        self.assertEqual(stats["pending_recovery_rate_pct"], 0.0)

    def test_no_samples_not_success(self):
        stats = probe.summarize([])
        self.assertEqual(stats["valid_200_races"], 0)
        self.assertIsNone(stats["median_race_elapsed_ms"])
        self.assertIsNone(stats["median_request_latency_ms"])
        self.assertIsNone(stats["pending_recovery_rate_pct"])
        self.assertEqual(stats["initially_pending_races"], 0)

    def test_first_attempt_valid_is_not_pending_recovery(self):
        result = probe.sample_race(CODE, request=lambda req, timeout: Response(valid_body()),
                                   now=NOW, pause=lambda _: None)
        stats = probe.summarize([result])
        self.assertEqual(stats["first_attempt_valid_races"], 1)
        self.assertEqual(stats["valid_200_races"], 1)
        self.assertEqual(stats["initially_pending_races"], 0)
        self.assertEqual(stats["pending_recovered_to_valid_200"], 0)
        self.assertIsNone(stats["pending_recovery_rate_pct"])
        self.assertIsInstance(stats["median_request_latency_ms"], int)

    def test_workflow_run_provenance_is_explicit(self):
        import os
        import tempfile
        from unittest.mock import patch
        from pathlib import Path
        parent = {"workflow_run": {"id": 778, "event": "schedule",
                  "name": "CLEAN prospective pre-cutoff capture",
                  "head_branch": "main"}}
        with tempfile.TemporaryDirectory() as folder:
            event_file = Path(folder) / "event.json"
            event_file.write_text(json.dumps(parent))
            with patch.dict(os.environ, {"GITHUB_EVENT_NAME": "workflow_run",
                      "GITHUB_EVENT_PATH": str(event_file)}):
                source = probe.event_provenance()
        self.assertEqual(source["event"], "workflow_run")
        self.assertEqual(source["upstream_event"], "schedule")
        self.assertEqual(source["upstream_workflow"], "CLEAN prospective pre-cutoff capture")
        self.assertEqual(source["upstream_run_id"], 778)

    def test_source_candidate_window(self):
        jst = timezone(timedelta(hours=9))
        now = datetime(2026, 11, 3, 14, 0, tzinfo=jst)
        titles = [{"レースコード": CODE, "電話投票締切予定": "14:25"},
                  {"レースコード": "202611030212", "電話投票締切予定": "14:05"}]
        self.assertEqual(probe.select_candidates(titles, "20261103", now, jst), [CODE])


if __name__ == "__main__":
    unittest.main()

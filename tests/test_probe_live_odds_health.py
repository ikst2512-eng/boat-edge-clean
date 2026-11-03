"""Offline tests for live-odds evidence classification; never depend on production."""
import importlib.util
import io
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

    def test_source_candidate_window(self):
        jst = timezone(timedelta(hours=9))
        now = datetime(2026, 11, 3, 14, 0, tzinfo=jst)
        titles = [{"レースコード": CODE, "電話投票締切予定": "14:25"},
                  {"レースコード": "202611030212", "電話投票締切予定": "14:05"}]
        self.assertEqual(probe.select_candidates(titles, "20261103", now, jst), [CODE])


if __name__ == "__main__":
    unittest.main()

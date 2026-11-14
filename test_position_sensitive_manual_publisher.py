"""Synthetic-only tests of optional, never-scheduled #1698 manual publisher."""
import base64
from datetime import datetime, timezone
from email.utils import format_datetime
import hashlib
import json
from unittest.mock import patch
import unittest

from position_sensitive_manual_publisher import (
    API, MIN_MARGIN_SECONDS, PROPOSED_LEDGER_BRANCH, SCHEMA,
    github_api_call, manual_publish_one,
)
from position_sensitive_receipt_intake import git_blob_sha
from test_four_mode_position_sensitive_forward import frozen

CODE = "202611090101"
MAIN_SHA = "b" * 40
COMMIT_SHA = "c" * 40


def date(jst):
    return format_datetime(
        datetime.fromisoformat(jst).astimezone(timezone.utc), usegmt=True)


def response(body, when, status=200):
    return status, {"Date": date(when)}, json.dumps(body).encode()


class MockGitHub:
    def __init__(self):
        snap, self.original = frozen()
        self.code = snap["race_code"]
        self.calls = []
        self.created_bytes = None
        self.original_status = 200
        self.occupied = None
        self.preflight_status = 404
        self.put_status = 201
        self.put_date = "2026-11-09T10:05:40+09:00"
        self.remote_date = "2026-11-09T10:05:50+09:00"
        self.readback_tamper = False
        self.put_payload = None

    def __call__(self, method, url, payload):
        self.calls.append((method, url))
        if method == "GET" and url == (
                API + "/git/ref/heads/" + PROPOSED_LEDGER_BRANCH):
            return response({
                "ref": "refs/heads/" + PROPOSED_LEDGER_BRANCH,
                "object": {"type": "commit", "sha": "d" * 40},
            }, "2026-11-09T10:05:25+09:00")
        if method == "GET" and url == API + "/git/commits/" + COMMIT_SHA:
            return response({
                "sha": COMMIT_SHA,
                "parents": [{"sha": "d" * 40}],
            }, "2026-11-09T10:05:45+09:00")
        if method == "GET" and url == API + "/git/ref/heads/main":
            return response({"ref": "refs/heads/main",
                             "object": {"type": "commit", "sha": MAIN_SHA}},
                            "2026-11-09T10:04:30+09:00")
        if method == "GET" and url == (
                API + "/contents/four_mode_forecasts/" + CODE + ".json?ref=" + MAIN_SHA):
            if self.original_status != 200:
                return response({"message": "not-found"}, "2026-11-09T10:04:40+09:00",
                                self.original_status)
            return response({
                "path": f"four_mode_forecasts/{CODE}.json",
                "type": "file",
                "encoding": "base64",
                "content": base64.b64encode(self.original).decode(),
                "sha": git_blob_sha(self.original),
            }, "2026-11-09T10:04:40+09:00")
        path = f"position_sensitive_research/{CODE}.json"
        if method == "GET" and url == API + "/contents/" + path + (
                "?ref=" + PROPOSED_LEDGER_BRANCH):
            if self.occupied is None:
                return response({"message": "Not Found"}, "2026-11-09T10:05:30+09:00",
                                self.preflight_status)
            return response({
                "path": path, "type": "file", "encoding": "base64",
                "content": base64.b64encode(self.occupied).decode(),
                "sha": git_blob_sha(self.occupied),
            }, "2026-11-09T10:05:30+09:00")
        if method == "PUT" and url == API + "/contents/" + path:
            self.put_payload = json.loads(payload)
            if self.put_status != 201:
                return response({"message": "Create failed"}, self.put_date,
                                self.put_status)
            self.created_bytes = base64.b64decode(self.put_payload["content"])
            return response({
                "content": {"path": path, "sha": git_blob_sha(self.created_bytes)},
                "commit": {"sha": COMMIT_SHA},
            }, self.put_date, 201)
        if method == "GET" and url == API + "/contents/" + path + "?ref=" + COMMIT_SHA:
            raw = self.created_bytes + b"tamper" if self.readback_tamper else self.created_bytes
            return response({
                "path": path, "type": "file", "encoding": "base64",
                "sha": git_blob_sha(raw),
                "content": base64.b64encode(raw).decode(),
            }, self.remote_date)
        return response({"message": "Not Found"}, "2026-11-09T10:05:40+09:00", 404)


def now_times(*times):
    queue = iter(times)
    return lambda: datetime.fromisoformat(next(queue))


def valid_clock():
    return now_times(
        "2026-11-09T10:05:00+09:00",
        "2026-11-09T10:05:10+09:00",
        "2026-11-09T10:05:20+09:00",
        "2026-11-09T10:05:35+09:00",
    )


class ManualPublisherSafetyTests(unittest.TestCase):
    def test_mock_atomic_research_only_create_is_nonformal(self):
        api = MockGitHub()
        out = manual_publish_one(CODE, api, valid_clock())
        self.assertEqual(out["status"], "manual_create_and_remote_observation_preT12_nonformal")
        self.assertEqual(out["schema"], SCHEMA)
        self.assertEqual(out["created_commit_sha"], COMMIT_SHA)
        self.assertEqual(out["research_head_before_create_sha"], "d" * 40)
        self.assertTrue(out["created_commit_parent_matches_preflight"])
        self.assertFalse(out["created_commit_parent_externally_attested"])
        self.assertEqual(out["research_branch"], PROPOSED_LEDGER_BRANCH)
        self.assertEqual(out["candidate_sha256"], hashlib.sha256(api.created_bytes).hexdigest())
        self.assertEqual(set(api.put_payload),
                         {"message", "branch", "content"})
        self.assertNotIn("sha", api.put_payload)
        self.assertEqual(api.put_payload["branch"], PROPOSED_LEDGER_BRANCH)
        self.assertEqual(len([x for x in api.calls if x[0] == "PUT"]), 1)
        self.assertFalse(out["candidate_first_remote_receipt_independently_verified"])
        self.assertFalse(out["formal"])
        self.assertFalse(out["promotion_allowed"])
        self.assertFalse(out["model_improvement_proven"])
        self.assertFalse(out["production_changed"])

    def test_absent_original_never_writes(self):
        api = MockGitHub()
        api.original_status = 404
        with self.assertRaisesRegex(ValueError, "github_http_404"):
            manual_publish_one(CODE, api, valid_clock())
        self.assertIsNone(api.created_bytes)

    def test_original_http_403_404_429_504_never_writes(self):
        for status in (403, 404, 429, 504):
            api = MockGitHub()
            api.original_status = status
            with self.subTest(status=status), self.assertRaises(ValueError):
                manual_publish_one(CODE, api, valid_clock())
            self.assertFalse(any(v[0] == "PUT" for v in api.calls))

    def test_candidate_already_exists_identical_or_other_cannot_republish(self):
        for raw in (b"not-the-same", b"{}"):
            api = MockGitHub()
            api.occupied = raw
            with self.assertRaisesRegex(ValueError, "immutable_candidate_collision"):
                manual_publish_one(CODE, api, valid_clock())
            self.assertFalse(any(v[0] == "PUT" for v in api.calls))

    def test_identical_candidate_retry_is_not_rewritten_or_certified(self):
        from four_mode_position_sensitive_forward import freeze_candidate
        api = MockGitHub()
        snap = freeze_candidate(api.original, "2026-11-09T10:05:10+09:00")
        api.occupied = (json.dumps(snap, ensure_ascii=False, sort_keys=True,
                                   indent=2) + "\n").encode()
        with self.assertRaisesRegex(
                ValueError, "candidate_already_exists_no_new_receipt"):
            manual_publish_one(CODE, api, valid_clock())
        self.assertFalse(any(v[0] == "PUT" for v in api.calls))
        self.assertIsNone(api.created_bytes)

    def test_missing_race_403_or_500_cannot_be_treated_as_404(self):
        for status in (403, 500, 429):
            api = MockGitHub()
            api.preflight_status = status
            with self.subTest(status=status), self.assertRaisesRegex(
                    ValueError, "github_preflight_http"):
                manual_publish_one(CODE, api, valid_clock())
            self.assertFalse(any(v[0] == "PUT" for v in api.calls))

    def test_create_conflict_or_bad_remote_status_fails_closed(self):
        for status in (200, 403, 409, 422, 504):
            api = MockGitHub()
            api.put_status = status
            with self.subTest(status=status), self.assertRaises(ValueError):
                manual_publish_one(CODE, api, valid_clock())

    def test_remote_after_cutoff_is_rejected_even_if_put_201(self):
        api = MockGitHub()
        api.put_date = "2026-11-09T12:28:00+09:00"
        with self.assertRaisesRegex(ValueError, "github_remote_create_response_after_T12"):
            manual_publish_one(CODE, api, valid_clock())
        api = MockGitHub()
        api.remote_date = "2026-11-09T12:28:00+09:00"
        with self.assertRaisesRegex(ValueError, "github_remote_candidate_not_early"):
            manual_publish_one(CODE, api, valid_clock())

    def test_wrong_readback_blob_rejected_after_create(self):
        api = MockGitHub()
        api.readback_tamper = True
        with self.assertRaises(ValueError):
            manual_publish_one(CODE, api, valid_clock())

    def test_late_local_timing_gate_fails_without_mutation(self):
        api = MockGitHub()
        times = now_times(
            "2026-11-09T12:27:00+09:00",
            "2026-11-09T12:27:10+09:00",
            "2026-11-09T12:27:20+09:00",
        )
        with self.assertRaisesRegex(ValueError, "too_late"):
            manual_publish_one(CODE, api, times)
        self.assertFalse(any(v[0] == "PUT" for v in api.calls))

    def test_wrong_cohort_and_missing_token_bail(self):
        api = MockGitHub()
        for code in ("202611080101", "202611090025", "wrong"):
            with self.subTest(code=code), self.assertRaises(ValueError):
                manual_publish_one(code, api, valid_clock())
        with patch.dict("os.environ", {"GH_TOKEN": ""}):
            with self.assertRaisesRegex(ValueError, "missing_explicit_GH_TOKEN"):
                github_api_call("GET", API + "/git/ref/heads/main", None)
        self.assertEqual(api.calls, [])

    def test_http_adapter_does_not_allow_main_writes(self):
        with self.assertRaisesRegex(ValueError, "write_outside_candidate_namespace"):
            github_api_call("PUT", API + "/contents/four_mode_forecasts/202611090101.json",
                            b'{}')
        with self.assertRaisesRegex(ValueError, "outside_fixed_repository"):
            github_api_call("GET", "https://example.com/attack", None)
        with self.assertRaisesRegex(ValueError, "read_outside_allowed_namespace"):
            github_api_call("GET", API + "/contents/confirmed_results/202611090101.json",
                            None)
        with patch.dict("os.environ", {"GH_TOKEN": "synthetic_fixture"}):
            with self.assertRaisesRegex(ValueError, "mutation_not_create_only"):
                github_api_call("PUT",
                                API + "/contents/position_sensitive_research/202611090101.json",
                                json.dumps({
                                    "message": "x", "branch": "main", "content": "e30="
                                }).encode())
            with self.assertRaisesRegex(ValueError, "mutation_not_create_only"):
                github_api_call("PUT",
                                API + "/contents/position_sensitive_research/202611090101.json",
                                json.dumps({
                                    "message": "x",
                                    "branch": PROPOSED_LEDGER_BRANCH,
                                    "content": "e30=", "sha": "0"*40,
                                }).encode())


if __name__ == "__main__":
    unittest.main()

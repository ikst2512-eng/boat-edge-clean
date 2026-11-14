"""Synthetic-only tests of independently HTTP-fetched candidate observer.

Mocked GitHub responses in this module are NOT genuine timestamp evidence.
"""
import base64
from copy import deepcopy
from datetime import datetime, timezone
from email.utils import format_datetime
import hashlib
import json
import unittest

from position_sensitive_remote_observer import (
    BRANCH, REPO, ROOT_URL, github_get, observe_candidate,
)
from position_sensitive_receipt_intake import git_blob_sha
from test_four_mode_position_sensitive_forward import frozen


def stamp(local_jst):
    return format_datetime(datetime.fromisoformat(local_jst).astimezone(timezone.utc),
                           usegmt=True)


def fixture():
    s, original = frozen()
    candidate = json.dumps(s, ensure_ascii=False, sort_keys=True).encode()
    code = s["race_code"]
    ref_url = ROOT_URL + "/git/ref/heads/" + BRANCH
    sha = "b" * 40
    contents_url = (ROOT_URL + "/contents/position_sensitive_research/" + code +
                    ".json?ref=" + sha)
    data = {
        ref_url: (200, {"Date": stamp("2026-11-09T10:05:30+09:00")},
                  json.dumps({
                      "ref": "refs/heads/" + BRANCH,
                      "object": {"type": "commit", "sha": sha},
                  }).encode()),
        contents_url: (200, {"Date": stamp("2026-11-09T10:06:00+09:00")},
                       json.dumps({
                           "type": "file",
                           "path": "position_sensitive_research/" + code + ".json",
                           "encoding": "base64",
                           "content": base64.b64encode(candidate).decode(),
                           "sha": git_blob_sha(candidate),
                       }).encode()),
    }
    return code, original, candidate, ref_url, contents_url, data


def fetcher(calls):
    def fetch(url):
        return calls.get(url, (404, {"Date": stamp("2026-11-09T10:06:00+09:00")}, b"{}"))
    return fetch


class RealRemoteWitnessTests(unittest.TestCase):
    def test_candidate_existing_before_t12_still_not_first_remote_receipt(self):
        code, original, candidate, ref_url, file_url, responses = fixture()
        observed = observe_candidate(code, original, fetcher(responses))
        self.assertEqual(observed["candidate_sha256"], hashlib.sha256(candidate).hexdigest())
        self.assertEqual(observed["observed_branch_commit_sha"], "b" * 40)
        self.assertIn("not_first_receipt", observed["status"])
        for flag in ("independent_candidate_first_remote_receipt_verified",
                     "original_first_remote_receipt_verified",
                     "branch_history_rewrite_excluded",
                     "run_inventory_complete",
                     "official_beforeinfo_exhibition_six_odds120_verified",
                     "formal", "model_improvement_proven",
                     "promotion_allowed", "production_changed"):
            self.assertIs(observed[flag], False, flag)

    def test_not_found_and_forbidden_cannot_look_successful(self):
        code, original, _, ref_url, file_url, base = fixture()
        for endpoint in (ref_url, file_url):
            for status in (403, 404, 408, 429, 500, 504):
                with self.subTest(endpoint=endpoint, status=status):
                    data = dict(base)
                    data[endpoint] = (status, {"Date": stamp("2026-11-09T10:06:00+09:00")},
                                      b"{}")
                    with self.assertRaisesRegex(ValueError, "github_http_not_200"):
                        observe_candidate(code, original, fetcher(data))

    def test_cached_or_missing_remote_date_fails_closed(self):
        code, original, _, _, file_url, base = fixture()
        for change in ({"Age": "1"}, {"date": "invalid"}, {"Date": None}):
            data = deepcopy(base)
            status, headers, body = data[file_url]
            headers = {**headers, **change}
            if "Date" in change:
                headers.pop("Date")
            if "date" in change:
                headers.pop("Date")
            data[file_url] = (status, headers, body)
            with self.assertRaises(ValueError):
                observe_candidate(code, original, fetcher(data))

    def test_remote_time_is_strictly_between_local_freeze_and_t12(self):
        code, original, _, _, file_url, base = fixture()
        for time in ("2026-11-09T10:04:59+09:00",
                     "2026-11-09T10:05:00+09:00",
                     "2026-11-09T12:28:00+09:00",
                     "2026-11-09T12:28:01+09:00"):
            data = deepcopy(base)
            status, headers, body = data[file_url]
            headers["Date"] = stamp(time)
            data[file_url] = (status, headers, body)
            with self.subTest(time=time), self.assertRaises(ValueError):
                observe_candidate(code, original, fetcher(data))

    def test_mismatched_branch_sha_and_content_rejected(self):
        code, original, candidate, ref_url, file_url, base = fixture()
        data = deepcopy(base)
        status, headers, body = data[ref_url]
        r = json.loads(body)
        r["object"]["sha"] = "c" * 40
        data[ref_url] = (status, headers, json.dumps(r).encode())
        with self.assertRaises(ValueError):
            observe_candidate(code, original, fetcher(data))
        data = deepcopy(base)
        status, headers, body = data[file_url]
        c = json.loads(body)
        c["sha"] = "0" * 40
        data[file_url] = (status, headers, json.dumps(c).encode())
        with self.assertRaisesRegex(ValueError, "github_candidate_blob_digest_invalid"):
            observe_candidate(code, original, fetcher(data))
        data = deepcopy(base)
        status, headers, body = data[file_url]
        c = json.loads(body)
        c["content"] = base64.b64encode(b"malicious").decode()
        c["sha"] = git_blob_sha(b"malicious")
        data[file_url] = (status, headers, json.dumps(c).encode())
        with self.assertRaisesRegex(ValueError, "github_candidate_replay_failed"):
            observe_candidate(code, original, fetcher(data))

    def test_modified_original_source_fails_replay(self):
        code, original, _, _, _, responses = fixture()
        with self.assertRaisesRegex(ValueError, "github_candidate_replay_failed"):
            observe_candidate(code, original + b" ", fetcher(responses))
        with self.assertRaisesRegex(ValueError, "invalid_observation_inputs"):
            observe_candidate("../etc/passwd", original, fetcher(responses))

    def test_forbidden_network_host_not_allowed(self):
        with self.assertRaisesRegex(ValueError, "unexpected_github_endpoint"):
            github_get("https://example.com/test")
        with self.assertRaisesRegex(ValueError, "unexpected_github_endpoint"):
            github_get(ROOT_URL + "/contents/confirmed_results/202611090101.json")


if __name__ == "__main__":
    unittest.main()

"""Fail-closed research-only candidate GitHub observation intake tests.

All GitHub responses here are synthetic fixtures, NOT genuine remote proof.
"""
import base64
from copy import deepcopy
from datetime import datetime, timezone
from email.utils import format_datetime
import json
import unittest

from test_four_mode_position_sensitive_forward import frozen
from position_sensitive_receipt_intake import assess_receipt_readiness, git_blob_sha


def evidence(raw, path, at, status=200):
    return {
        "repository": "ikst2512-eng/boat-edge-clean",
        "url_path": path,
        "http_status": status,
        "http_age_header_present": False,
        "github_api_date_header": format_datetime(
            datetime.fromisoformat(at).astimezone(timezone.utc), usegmt=True),
        "github_commit_sha": "d" * 40,
        "github_contents_response": {
            "path": path, "type": "file", "encoding": "base64",
            "sha": git_blob_sha(raw),
            "content": base64.b64encode(raw).decode(),
        },
    }


class CandidateReceiptIntakeTests(unittest.TestCase):
    def original_and_candidate(self):
        snap, original = frozen()
        candidate = json.dumps(snap, sort_keys=True).encode()
        code = snap["race_code"]
        return original, candidate, code

    def both(self):
        original, candidate, code = self.original_and_candidate()
        original_proof = evidence(original, f"four_mode_forecasts/{code}.json",
                                  "2026-11-09T10:02:00+09:00")
        candidate_proof = evidence(candidate, f"position_sensitive_research/{code}.json",
                                   "2026-11-09T10:06:00+09:00")
        return original, candidate, original_proof, candidate_proof

    def test_no_observations_is_not_a_remote_receipt(self):
        original, candidate, _ = self.original_and_candidate()
        out = assess_receipt_readiness(original, candidate)
        self.assertEqual(out["status"], "local_candidate_valid_external_evidence_missing")
        self.assertTrue(out["candidate_source_blob_verified_against_frozen_selector"])
        self.assertFalse(out["first_remote_candidate_receipt_verified"])
        self.assertFalse(out["formal"])
        self.assertFalse(out["promotion_allowed"])

    def test_supplied_early_200_responses_still_not_first_remote_receipt(self):
        original, candidate, o, c = self.both()
        out = assess_receipt_readiness(original, candidate, o, c)
        self.assertEqual(out["status"],
                         "two_supplied_pre_T12_observations_self_consistent_nonformal")
        self.assertEqual(out["original_remote_observation"]["sha256"],
                         __import__("hashlib").sha256(original).hexdigest())
        self.assertFalse(out["observations_are_externally_authenticated"])
        self.assertFalse(out["first_remote_candidate_receipt_verified"])
        self.assertFalse(out["official_beforeinfo_exhibition_six_odds120_verified"])
        self.assertFalse(out["model_improvement_proven"])
        self.assertFalse(out["promotion_allowed"])

    def test_one_observation_is_not_enough(self):
        original, candidate, o, _ = self.both()
        out = assess_receipt_readiness(original, candidate, original_observation=o)
        self.assertEqual(out["status"], "one_supplied_pre_T12_observation_incomplete_nonformal")
        self.assertIsNone(out["candidate_remote_observation"])

    def test_403_404_timeout_and_cached_response_fail_closed(self):
        original, candidate, o, c = self.both()
        for bad_status in (403, 404, 408, 504):
            attempt = deepcopy(c)
            attempt["http_status"] = bad_status
            with self.subTest(status=bad_status), self.assertRaises(ValueError):
                assess_receipt_readiness(original, candidate, o, attempt)
        cached = deepcopy(c)
        cached["http_age_header_present"] = True
        with self.assertRaises(ValueError):
            assess_receipt_readiness(original, candidate, o, cached)

    def test_after_T12_and_same_second_cutoff_rejected(self):
        original, candidate, o, c = self.both()
        for late in ("2026-11-09T12:28:00+09:00",
                     "2026-11-09T12:29:00+09:00",
                     "2026-11-09T13:00:00+09:00"):
            c1 = deepcopy(c)
            c1["github_api_date_header"] = format_datetime(
                datetime.fromisoformat(late).astimezone(timezone.utc), usegmt=True)
            with self.subTest(late=late), self.assertRaisesRegex(ValueError, "strictly"):
                assess_receipt_readiness(original, candidate, o, c1)

    def test_candidate_observation_before_local_freeze_rejected(self):
        original, candidate, o, c = self.both()
        c["github_api_date_header"] = format_datetime(
            datetime.fromisoformat("2026-11-09T10:05:00+09:00").astimezone(
                timezone.utc), usegmt=True)
        with self.assertRaisesRegex(ValueError, "strictly"):
            assess_receipt_readiness(original, candidate, o, c)

    def test_remote_body_or_git_sha_mismatch_fail(self):
        original, candidate, o, c = self.both()
        for edit in ("sha", "body", "path", "repo", "commit"):
            x = deepcopy(c)
            if edit == "sha":
                x["github_contents_response"]["sha"] = "a"*40
            elif edit == "body":
                x["github_contents_response"]["content"] = base64.b64encode(
                    b"altered").decode()
            elif edit == "path":
                x["url_path"] = "four_mode_forecasts/202611090101.json"
            elif edit == "repo":
                x["repository"] = "attacker/repository"
            elif edit == "commit":
                x["github_commit_sha"] = "wrong-sha"
            with self.subTest(edit=edit), self.assertRaises(ValueError):
                assess_receipt_readiness(original, candidate, o, x)

    def test_modified_candidate_and_original_fail_before_receipt(self):
        original, candidate, o, c = self.both()
        data = json.loads(candidate)
        data["candidate"]["hit"][0] = "6-5-4"
        with self.assertRaises(ValueError):
            assess_receipt_readiness(original, json.dumps(data).encode(), o, c)
        with self.assertRaises(ValueError):
            assess_receipt_readiness(original+b" ", candidate, o, c)

    def test_date_and_base64_tamper_fail_closed(self):
        original, candidate, o, c = self.both()
        malformed = deepcopy(o)
        malformed["github_api_date_header"] = "sunday"
        with self.assertRaises(ValueError):
            assess_receipt_readiness(original, candidate, malformed, c)
        malformed = deepcopy(c)
        malformed["github_contents_response"]["content"] = "not-base64***"
        with self.assertRaises(ValueError):
            assess_receipt_readiness(original, candidate, o, malformed)


if __name__ == "__main__":
    unittest.main()

"""Synthetic commit-ancestry safety cases for optional #1698 manual writer.

A mocked 201 or a passing unit test is NOT a real publication or first receipt.
"""
import json
from datetime import datetime, timezone
from email.utils import format_datetime
import unittest

from position_sensitive_manual_publisher import (
    API, PROPOSED_LEDGER_BRANCH, manual_publish_one,
)
from test_position_sensitive_manual_publisher import (
    CODE, COMMIT_SHA, MockGitHub, valid_clock,
)


def date(jst):
    return format_datetime(
        datetime.fromisoformat(jst).astimezone(timezone.utc), usegmt=True)


class TamperedProvenance:
    def __init__(self, scenario):
        self.inner = MockGitHub()
        self.scenario = scenario

    def __call__(self, method, url, raw):
        status, headers, body = self.inner(method, url, raw)
        if method != "GET":
            return status, headers, body
        ref_url = API + "/git/ref/heads/" + PROPOSED_LEDGER_BRANCH
        commit_url = API + "/git/commits/" + COMMIT_SHA
        if url == ref_url:
            if self.scenario == "missing_ledger":
                return 404, headers, b'{"message":"Not Found"}'
            if self.scenario == "wrong_ledger_ref":
                p = json.loads(body)
                p["ref"] = "refs/heads/main"
                return status, headers, json.dumps(p).encode()
            if self.scenario == "late_ledger_ref":
                return status, {**headers, "Date": date("2026-11-09T12:28:00+09:00")}, body
        if url == commit_url:
            if self.scenario == "commit_404":
                return 404, headers, b'{"message":"Not Found"}'
            p = json.loads(body)
            if self.scenario == "wrong_commit_sha":
                p["sha"] = "e"*40
            if self.scenario == "wrong_parent":
                p["parents"] = [{"sha": "e"*40}]
            if self.scenario == "merge_commit":
                p["parents"] = [{"sha": "d"*40}, {"sha": "e"*40}]
            if self.scenario == "no_parent":
                p["parents"] = []
            if self.scenario == "early_commit_meta":
                headers = {**headers, "Date": date("2026-11-09T10:05:39+09:00")}
            if self.scenario == "equal_second_commit_meta":
                headers = {**headers, "Date": date("2026-11-09T10:05:40+09:00")}
            return status, headers, json.dumps(p).encode()
        return status, headers, body


class ManualPublisherAncestryTests(unittest.TestCase):
    def test_ledger_must_exist_before_create_and_be_correct_branch(self):
        for scenario in ("missing_ledger", "wrong_ledger_ref", "late_ledger_ref"):
            api = TamperedProvenance(scenario)
            with self.subTest(scenario=scenario), self.assertRaises(ValueError):
                manual_publish_one(CODE, api, valid_clock())
            self.assertFalse(any(m == "PUT" for m, _ in api.inner.calls))

    def test_mismatched_or_orphan_or_merge_parent_denies_good_receipt_label(self):
        for scenario in ("commit_404", "wrong_commit_sha", "wrong_parent",
                         "merge_commit", "no_parent"):
            api = TamperedProvenance(scenario)
            with self.subTest(scenario=scenario), self.assertRaises(ValueError):
                manual_publish_one(CODE, api, valid_clock())
            # Failure AFTER a mocked 201 cannot roll back a real remote write.
            # Operator must independently inspect the branch before retrying.
            self.assertTrue(any(m == "PUT" for m, _ in api.inner.calls))

    def test_metadata_before_or_same_second_as_201_is_ambiguous(self):
        for scenario in ("early_commit_meta", "equal_second_commit_meta"):
            api = TamperedProvenance(scenario)
            with self.subTest(scenario=scenario), self.assertRaisesRegex(
                ValueError, "created_commit_metadata_clock_invalid"):
                manual_publish_one(CODE, api, valid_clock())

    def test_good_linear_commit_chain_is_still_nonformal(self):
        api = TamperedProvenance("normal")
        result = manual_publish_one(CODE, api, valid_clock())
        self.assertEqual(result["research_head_before_create_sha"], "d"*40)
        self.assertEqual(result["created_commit_sha"], "c"*40)
        self.assertTrue(result["created_commit_parent_matches_preflight"])
        self.assertFalse(result["created_commit_parent_externally_attested"])
        self.assertFalse(result["candidate_first_remote_receipt_independently_verified"])
        self.assertFalse(result["formal"])
        self.assertFalse(result["promotion_allowed"])


if __name__ == "__main__":
    unittest.main()

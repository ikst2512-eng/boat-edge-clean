"""Synthetic receipt cross-check tests: never grants formal approval."""
import hashlib
import json
import unittest
from tests.test_formal_candidate_validator import sample
from formal_candidate_validator import InvalidCandidate
from formal_receipt_inspector import inspect_receipt


class ReceiptTests(unittest.TestCase):
    def make_case(self):
        candidate = sample()
        raw = json.dumps(candidate, allow_nan=False).encode()
        receipt = {"artifact_sha256": hashlib.sha256(raw).hexdigest(),
                   "race_key": candidate["race_key"], "first_seen_at": "2026-10-28T09:02:00+09:00",
                   "repository": "sample/capture", "artifact_commit_sha": "d" * 40}
        return raw, receipt

    def test_matching_receipt_still_not_independent(self):
        raw, receipt = self.make_case()
        result = inspect_receipt(raw, receipt)
        self.assertTrue(result["receipt_shape_consistent"])
        self.assertFalse(result["independent_receipt_verified"])
        self.assertFalse(result["formal_approved"])

    def test_mismatched_bytes(self):
        raw, receipt = self.make_case()
        with self.assertRaises(InvalidCandidate):
            inspect_receipt(raw + b" ", receipt)

    def test_late_receipt(self):
        raw, receipt = self.make_case()
        receipt["first_seen_at"] = "2026-10-28T09:04:00+09:00"
        with self.assertRaises(InvalidCandidate):
            inspect_receipt(raw, receipt)

    def test_wrong_race(self):
        raw, receipt = self.make_case()
        receipt["race_key"] = "20261028-02-01"
        with self.assertRaises(InvalidCandidate):
            inspect_receipt(raw, receipt)

    def test_duplicate_json_key(self):
        raw, receipt = self.make_case()
        raw = raw.replace(b'"source_kind":', b'"race_key":"20261028-02-01","source_kind":', 1)
        receipt["artifact_sha256"] = hashlib.sha256(raw).hexdigest()
        with self.assertRaises(InvalidCandidate):
            inspect_receipt(raw, receipt)


if __name__ == "__main__":
    unittest.main()

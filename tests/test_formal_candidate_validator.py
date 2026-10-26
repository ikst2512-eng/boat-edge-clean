"""Synthetic, outcome-free candidate validator tests."""
import copy
from itertools import permutations
import unittest

from formal_candidate_validator import InvalidCandidate, validate_candidate


def sample():
    return {
        "race_key": "20261028-01-01",
        "source_kind": "formal_candidate",
        "model_sha256": "a" * 64,
        "input_sha256": "b" * 64,
        "git_sha": "c" * 40,
        "generated_at": "2026-10-28T09:00:00+09:00",
        "cutoff_at": "2026-10-28T09:03:00+09:00",
        "official_deadline_at": "2026-10-28T09:15:00+09:00",
        "ranked_120": [{"combo": "-".join(t), "probability": 1 / 120}
                       for t in permutations("123456", 3)],
    }


class CandidateTests(unittest.TestCase):
    def test_shape_does_not_approve(self):
        result = validate_candidate(sample())
        self.assertTrue(result["shape_valid"])
        self.assertFalse(result["formal_approved"])
        self.assertFalse(result["independent_receipt_verified"])

    def test_bad_probability(self):
        for value in (float("nan"), -1, True, float("inf")):
            with self.subTest(value=str(value)):
                v = sample()
                v["ranked_120"][0]["probability"] = value
                with self.assertRaises(InvalidCandidate):
                    validate_candidate(v)

    def test_duplicate_and_short(self):
        v = sample()
        v["ranked_120"][1]["combo"] = v["ranked_120"][0]["combo"]
        with self.assertRaises(InvalidCandidate):
            validate_candidate(v)
        v = sample()
        v["ranked_120"].pop()
        with self.assertRaises(InvalidCandidate):
            validate_candidate(v)

    def test_late_generation(self):
        v = sample()
        v["generated_at"] = v["cutoff_at"]
        with self.assertRaises(InvalidCandidate):
            validate_candidate(v)

    def test_cutoff_too_close_to_deadline(self):
        v = sample()
        v["cutoff_at"] = "2026-10-28T09:04:00+09:00"
        with self.assertRaises(InvalidCandidate):
            validate_candidate(v)

    def test_timezone_required(self):
        v = sample()
        v["generated_at"] = "2026-10-28T09:00:00"
        with self.assertRaises(InvalidCandidate):
            validate_candidate(v)

    def test_untrusted_identity(self):
        v = sample()
        v["git_sha"] = "fake"
        with self.assertRaises(InvalidCandidate):
            validate_candidate(v)


if __name__ == "__main__":
    unittest.main()

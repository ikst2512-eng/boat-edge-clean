"""Tests for paired research evaluation, no race-data fabrication in scored reports."""
import unittest
from datetime import datetime, timedelta, timezone
from itertools import permutations
from research_paired_evaluation import TICKETS, validate, metrics

class EvaluationTests(unittest.TestCase):
    def fixture(self):
        tickets = sorted(TICKETS)
        probs = {t: 1 / 120 for t in tickets}
        other = {t: 0.0 for t in tickets}
        other["1-2-3"] = 1.0
        return {"race_code": "202610271201",
                "generated_at": "2026-10-27T10:00:00+09:00",
                "cutoff_jst": "2026-10-27T10:12:00+09:00",
                "actual": "1-2-3", "baseline": probs, "candidate": other}

    def test_full_distribution_and_paired_hits(self):
        row = validate(self.fixture())
        result = metrics([row])
        self.assertEqual(result["races"], 1)
        self.assertEqual(result["candidate"]["top_hits"]["1"], 1)
        self.assertAlmostEqual(result["candidate"]["log_loss"], 0)

    def test_rejects_missing_ticket(self):
        row = self.fixture()
        row["baseline"].pop("1-2-3")
        with self.assertRaises(ValueError):
            validate(row)

    def test_rejects_post_cutoff(self):
        row = self.fixture()
        row["generated_at"] = row["cutoff_jst"]
        with self.assertRaises(ValueError):
            validate(row)

    def test_rejects_invalid_actual(self):
        row = self.fixture()
        row["actual"] = "1-1-2"
        with self.assertRaises(ValueError):
            validate(row)

    def test_rejects_wrong_normalization(self):
        row = self.fixture()
        row["candidate"]["1-2-3"] = 0.5
        with self.assertRaises(ValueError):
            validate(row)

if __name__ == "__main__":
    unittest.main()

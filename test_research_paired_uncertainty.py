"""Isolated research inference checks using synthetic examples only."""
import unittest
from research_paired_uncertainty import exact_mcnemar_p, summarize
from research_paired_evaluation import TICKETS


def example(code="202610271201", actual="1-2-3", flip=False):
    keys = sorted(TICKETS)
    baseline = {t: 0.0 for t in keys}
    candidate = {t: 0.0 for t in keys}
    baseline["1-2-3" if flip else "6-5-4"] = 1.0
    candidate["6-5-4" if flip else "1-2-3"] = 1.0
    return {"race_code": code, "generated_at": "2026-10-27T10:00:00+09:00",
            "cutoff_jst": "2026-10-27T10:12:00+09:00",
            "actual": actual, "baseline": baseline, "candidate": candidate}


class UncertaintyTests(unittest.TestCase):
    def test_exact_mcnemar(self):
        self.assertEqual(exact_mcnemar_p(0, 0), 1.0)
        self.assertEqual(exact_mcnemar_p(1, 0), 1.0)
        self.assertAlmostEqual(exact_mcnemar_p(6, 0), 0.03125)
        self.assertAlmostEqual(exact_mcnemar_p(3, 3), 1.0)

    def test_large_sample_no_underflow(self):
        value = exact_mcnemar_p(1200, 1000)
        self.assertGreater(value, 0.0)
        self.assertLess(value, 1.0)

    def test_counts_deterministic_and_uncertainty(self):
        rows = [example(), example("202610281201", flip=True)]
        a = summarize(rows, resamples=200, seed=7)
        b = summarize(rows, resamples=200, seed=7)
        self.assertEqual(a, b)
        self.assertEqual(a["races"], 2)
        self.assertEqual(a["days"], 2)
        self.assertEqual(a["top_k"]["1"]["candidate_only_hits"], 1)
        self.assertEqual(a["top_k"]["1"]["baseline_only_hits"], 1)
        self.assertEqual(a["top_k"]["1"]["paired_delta"], 0)

    def test_duplicate_key_rejected(self):
        with self.assertRaises(ValueError):
            summarize([example(), example()], resamples=100)

    def test_post_cutoff_rejected(self):
        row = example()
        row["generated_at"] = row["cutoff_jst"]
        with self.assertRaises(ValueError):
            summarize([row], resamples=100)


if __name__ == "__main__":
    unittest.main()

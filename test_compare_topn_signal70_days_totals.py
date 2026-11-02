"""Regression checks for later-holdout TopN aggregation (no real predictions changed)."""
import unittest
from compare_topn_signal70_days import report


def group(evaluated=0, hits=(0, 0, 0), payout=0, awaiting=0):
    return {"evaluated": evaluated, "awaiting_result": awaiting, "rejected": 0,
            "payout_verified": payout,
            "hits": dict(zip(("top3", "top5", "top10"), hits))}


class HoldoutTotalsTest(unittest.TestCase):
    def test_weighted_denominator_and_discovery_exclusion(self):
        samples = {
            "20261029": {"signal_70_plus": group(200, (90, 100, 110), 200)},
            "20261030": {"signal_70_plus": group(2, (1, 1, 2), 1),
                         "below_70": group(1, (0, 1, 1), 0, 1)},
            "20261031": {"signal_70_plus": group(7, (2, 3, 4), 4)},
        }

        def evaluator(day):
            return {"schema": "CLEAN_TOPN_SIGNAL70_RESEARCH_V1",
                    "day_jst": day, "signal_is_empirical_confidence": False,
                    "archived": 0, "groups": samples[day]}

        result = report(list(samples), evaluator=evaluator)
        total = result["later_holdout_totals"]
        self.assertEqual(total["evaluated"], 10)
        self.assertEqual(total["hits"], {"top3": 3, "top5": 5, "top10": 7})
        self.assertEqual(total["hit_rate_pct"], {"top3": 30.0, "top5": 50.0, "top10": 70.0})
        self.assertEqual(total["payout_verified"], 5)
        self.assertEqual(total["payout_coverage_pct"], 50.0)
        self.assertEqual(total["awaiting_result"], 1)
        self.assertFalse(total["formal"])
        self.assertFalse(total["independently_validated"])

    def test_no_evaluated_races_not_reported_as_zero_percent(self):
        def evaluator(day):
            return {"schema": "CLEAN_TOPN_SIGNAL70_RESEARCH_V1",
                    "day_jst": day, "signal_is_empirical_confidence": False,
                    "archived": 1, "groups": {"below_70": group(awaiting=1)}}
        total = report(["20261030"], evaluator=evaluator)["later_holdout_totals"]
        self.assertEqual(total["evaluated"], 0)
        self.assertTrue(all(value is None for value in total["hit_rate_pct"].values()))
        self.assertIsNone(total["payout_coverage_pct"])


if __name__ == "__main__":
    unittest.main()

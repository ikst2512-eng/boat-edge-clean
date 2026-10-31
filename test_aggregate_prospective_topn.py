import unittest
from aggregate_prospective_topn import summary


class MultiDayTopNTests(unittest.TestCase):
    @staticmethod
    def fake(day):
        hits = {"top3": 1, "top5": 2, "top10": 3} if day == "20261029" else {"top3": 0, "top5": 1, "top10": 1}
        evaluated = 4 if day == "20261029" else 2
        return {"schema": "CLEAN_PROSPECTIVE_TOPN_COHORT_V1", "day_jst": day,
                "formal": False, "simulated_only": True, "first_add_audit_required": True,
                "counts": {"archives": evaluated + 1, "evaluated": evaluated, "awaiting_result": 1, "audit_rejected": 0},
                "hits": hits,
                "roi": {k: {"races": 1, "invested_yen": 5000, "return_yen": 1000 if hits[k] else 0} for k in hits}}

    def test_weighted_race_denominator_not_average_of_daily_percentages(self):
        output = summary(["20261030", "20261029"], self.fake)
        self.assertEqual(output["counts"]["evaluated"], 6)
        self.assertEqual(output["hit_rate_pct"], {"top3": 16.67, "top5": 50.0, "top10": 66.67})
        self.assertEqual(output["roi"]["top10"]["invested_yen"], 10000)
        self.assertEqual(output["roi"]["top10"]["roi_pct"], 20.0)
        self.assertFalse(output["formal"])

    def test_pending_days_never_enter_denominator(self):
        def source(day):
            value = self.fake(day)
            value["counts"] = {"archives": 2, "evaluated": 0, "awaiting_result": 2, "audit_rejected": 0}
            value["hits"] = {"top3": 0, "top5": 0, "top10": 0}
            value["roi"] = {k: {"races": 0, "invested_yen": 0, "return_yen": 0} for k in value["hits"]}
            return value
        result = summary(["20261029"], source)
        self.assertIsNone(result["hit_rate_pct"]["top10"])
        self.assertIsNone(result["roi"]["top10"]["roi_pct"])

    def test_missing_audit_accounting_rejected(self):
        def source(day):
            value = self.fake(day)
            value["counts"]["archives"] += 1
            return value
        with self.assertRaises(ValueError):
            summary(["20261029"], source)

    def test_duplicate_dates_rejected(self):
        with self.assertRaises(ValueError):
            summary(["20261029", "20261029"], self.fake)


if __name__ == "__main__":
    unittest.main()

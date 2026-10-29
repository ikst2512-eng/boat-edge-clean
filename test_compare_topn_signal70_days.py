import unittest
from compare_topn_signal70_days import report


class Tests(unittest.TestCase):
    @staticmethod
    def fake(day):
        return {"schema": "CLEAN_TOPN_SIGNAL70_RESEARCH_V1", "day_jst": day,
                "signal_is_empirical_confidence": False, "archived": 1, "groups": {}}

    def test_separate_discovery_and_future(self):
        r = report(["20261028", "20261029", "20261030"], self.fake)
        self.assertEqual([x["role"] for x in r["days"]],
                         ["earlier_exploratory", "discovery", "later_holdout"])
        self.assertEqual(r["later_holdout_days"], 1)
        self.assertFalse(r["calibrated_confidence"])
        self.assertFalse(r["formal"])
        self.assertEqual(r["threshold"], 0.70)

    def test_discovery_only_is_not_holdout(self):
        r = report(["20261028", "20261029"], self.fake)
        self.assertEqual(r["later_holdout_days"], 0)
        self.assertFalse(r["calibrated_confidence"])
        self.assertFalse(r["formal"])

    def test_discovery_never_becomes_holdout_when_no_future_date_exists(self):
        r = report(["20261029"], self.fake)
        self.assertEqual(r["later_holdout_days"], 0)
        self.assertEqual(r["days"][0]["role"], "discovery")
        self.assertFalse(r["calibrated_confidence"])

    def test_empty_future_day_does_not_count_as_evaluated_holdout(self):
        r = report(["20261029", "20261030"], self.fake)
        self.assertEqual(r["later_holdout_days"], 1)
        self.assertEqual(r["later_holdout_evaluated_days"], 0)
        self.assertEqual(r["later_holdout_evaluated_races"], 0)

    def test_evaluated_future_day_counts_only_observed_races(self):
        def source(day):
            data = self.fake(day)
            data["groups"] = {"signal_70_plus": {"evaluated": 2}, "below_70": {"evaluated": 3}}
            return data
        r = report(["20261029", "20261030"], source)
        self.assertEqual(r["later_holdout_evaluated_days"], 1)
        self.assertEqual(r["later_holdout_evaluated_races"], 5)

    def test_duplicate_day_fails(self):
        with self.assertRaises(ValueError):
            report(["20261029", "20261029"])

    def test_invalid_date_formats_fail(self):
        for day in ("invalid", "2026-10-30", "２０２６１０３０", "2030103", ""):
            with self.subTest(day=day), self.assertRaises(ValueError):
                report([day], self.fake)

    def test_reject_wrong_source_schema(self):
        def wrong(day):
            result = self.fake(day)
            result["schema"] = "UNTRUSTED"
            return result
        with self.assertRaises(ValueError):
            report(["20261030"], wrong)

    def test_reject_mismatched_source_day(self):
        def wrong(day):
            result = self.fake(day)
            result["day_jst"] = "20261029"
            return result
        with self.assertRaises(ValueError):
            report(["20261030"], wrong)

    def test_reject_empirical_confidence_claim(self):
        def wrong(day):
            result = self.fake(day)
            result["signal_is_empirical_confidence"] = True
            return result
        with self.assertRaises(ValueError):
            report(["20261030"], wrong)


if __name__ == "__main__":
    unittest.main()

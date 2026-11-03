import copy
import unittest

from four_mode_v2_research_readiness import summarize, paired_one_sided_pvalue


def fixture():
    report = {"formal": False, "independent_remote_first_seen_verified": False,
            "v2_comparable": 8, "model_version": "CLEAN_FOUR_MODES_V2_PROVISIONAL_UNCALIBRATED",
            "protocol": "V2_FIRST_HEAD_GAP_0_5_BONUS_0_30_SHADOW_V1",
            "groups": {"20261103": {
                "forecast_files": 149, "comparable": 8, "pending_results": 141,
                "pending_by_deadline": {"before_deadline": 67,
                    "within_60m_after_deadline": 16, "over_60m_after_deadline": 58},
                "applied": 3, "gained_top3": 0, "lost_top3": 0,
                "baseline": {"top3": 1, "top5": 2, "top10": 5},
                "candidate": {"top3": 1, "top5": 2, "top10": 5},
                "modes": {m: {"top3": 1, "top5": 2, "top10": (6 if m=="balance" else 5)}
                          for m in ("narrow", "hit", "balance", "hole")}}}}

    modes = report["groups"]["20261103"]["modes"]
    pairs = {}
    for left, right in (("hit", "balance"), ("narrow", "hit"), ("balance", "hole")):
        pairs[f"{left}_vs_{right}"] = {}
        for n in (3, 5, 10):
            key = f"top{n}"
            a, b = modes[left][key], modes[right][key]
            pairs[f"{left}_vs_{right}"][key] = {
                "both": min(a, b), "left_only": max(a-b, 0),
                "right_only": max(b-a, 0), "neither": 8-max(a,b)}
    report["groups"]["20261103"]["paired_modes"] = pairs
    return report


class V2ReadinessTests(unittest.TestCase):
    def test_rejects_small_sample_and_remains_research_only(self):
        r = summarize(fixture())
        self.assertFalse(r["production_promotion_allowed"])
        self.assertEqual(r["total"]["saved_forecasts"], 149)
        self.assertEqual(r["comparable_denominator"], 8)
        self.assertEqual(r["total"]["over_60m_after_deadline"], 58)
        self.assertIn("fewer_than_100_paired_races", r["blocking_reasons"])

    def test_rejects_false_paired_mode_counts(self):
        d = fixture()
        d["groups"]["20261103"]["paired_modes"]["hit_vs_balance"]["top10"]["right_only"] += 1
        with self.assertRaises(ValueError):
            summarize(d)

    def test_valid_paired_mode_totals(self):
        report = summarize(fixture())
        self.assertEqual(report["total"]["paired_modes"]["hit_vs_balance"]["top10"]["right_only"], 1)
        self.assertEqual(report["total"]["paired_modes"]["hit_vs_balance"]["top10"]["both"], 5)

    def test_rejects_false_formal_promotion(self):
        d = fixture()
        d["formal"] = True
        with self.assertRaises(ValueError):
            summarize(d)

    def test_rejects_false_missing_result_total(self):
        d = fixture()
        d["groups"]["20261103"]["pending_by_deadline"]["over_60m_after_deadline"] -= 1
        with self.assertRaises(ValueError):
            summarize(d)

    def test_rejects_top10_membership_change(self):
        d = fixture()
        d["groups"]["20261103"]["candidate"]["top10"] = 4
        with self.assertRaises(ValueError):
            summarize(d)

    def test_rejects_impossible_discordances(self):
        d = fixture()
        d["groups"]["20261103"]["gained_top3"] = 4
        with self.assertRaises(ValueError):
            summarize(d)

    def test_paired_sign_test_no_discordance(self):
        self.assertIsNone(paired_one_sided_pvalue(0,0))
        self.assertEqual(paired_one_sided_pvalue(2,0),0.25)
        self.assertEqual(paired_one_sided_pvalue(0,2),1.0)


if __name__ == "__main__":
    unittest.main()

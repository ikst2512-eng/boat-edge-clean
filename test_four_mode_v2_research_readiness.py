import copy
import unittest

from four_mode_v2_research_readiness import summarize, paired_one_sided_pvalue


def fixture():
    report = {"formal": False, "independent_remote_first_seen_verified": False,
            "v2_comparable": 8, "model_version": "CLEAN_FOUR_MODES_V2_PROVISIONAL_UNCALIBRATED",
            "protocol": "V2_FIRST_HEAD_GAP_0_5_BONUS_0_30_SHADOW_V1",
            "groups": {"20261103": {
                "forecast_files": 149, "comparable": 8, "pending_results": 141,
                "matured_comparable": 8,
                "matured_modes": {m: {"top3": 1, "top5": 2, "top10": (6 if m == "balance" else 5)}
                                  for m in ("narrow", "hit", "balance", "hole")},
                "pending_by_deadline": {"before_deadline": 67,
                    "within_60m_after_deadline": 16, "over_60m_after_deadline": 58},
                "applied": 3, "reordered_top10": 2,
                "changed_top3_membership": 1, "changed_top5_membership": 1,
                "gained_top3": 0, "lost_top3": 0,
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
        self.assertIn("insufficient_mature_result_coverage", r["blocking_reasons"])
        self.assertEqual(r["mature_outcome_denominator"], 66)
        self.assertAlmostEqual(r["mature_result_coverage"], 8/66, places=6)

    def test_rejects_false_paired_mode_counts(self):
        d = fixture()
        d["groups"]["20261103"]["paired_modes"]["hit_vs_balance"]["top10"]["right_only"] += 1
        with self.assertRaises(ValueError):
            summarize(d)

    def test_valid_paired_mode_totals(self):
        report = summarize(fixture())
        self.assertEqual(report["total"]["paired_modes"]["hit_vs_balance"]["top10"]["right_only"], 1)
        self.assertEqual(report["total"]["paired_modes"]["hit_vs_balance"]["top10"]["both"], 5)

    def test_rejects_excessive_mature_count(self):
        d = fixture()
        d["groups"]["20261103"]["matured_comparable"] = 9
        with self.assertRaises(ValueError):
            summarize(d)

    def test_no_overdue_result_coverage_is_unproven(self):
        d = fixture()
        d["groups"]["20261103"]["matured_comparable"] = 0
        for mode in d["groups"]["20261103"]["matured_modes"].values():
            for key in mode:
                mode[key] = 0
        d["groups"]["20261103"]["pending_by_deadline"]["before_deadline"] += 58
        d["groups"]["20261103"]["pending_by_deadline"]["over_60m_after_deadline"] = 0
        result = summarize(d)
        self.assertIsNone(result["mature_result_coverage"])
        self.assertIn("insufficient_mature_result_coverage", result["blocking_reasons"])

    def test_missing_outcome_extremes_stay_descriptive(self):
        d = summarize(fixture())
        result = d["overdue_missingness_sensitivity"]["hit"]["top3"]
        self.assertEqual(result["scenario_denominator"], 66)
        self.assertEqual(result["unresolved_overdue"], 58)
        self.assertAlmostEqual(result["all_missing_miss_rate"], 1/66, places=6)
        self.assertAlmostEqual(result["all_missing_hit_rate"], 59/66, places=6)
        self.assertFalse(d["production_promotion_allowed"])

    def test_rejects_mature_hits_exceeding_mature_cohort(self):
        d = fixture()
        d["groups"]["20261103"]["matured_modes"]["hit"]["top3"] = 9
        with self.assertRaises(ValueError):
            summarize(d)

    def test_venue_gap_blocks_interpretation_even_if_global_stats_exist(self):
        d = fixture()
        venues = {"20261103:02": {"mature_confirmed": 0, "missing_over_60m": 58},
                  "20261103:10": {"mature_confirmed": 8, "missing_over_60m": 0}}
        audit = {"formal": False, "verified_first_remote_publication": False,
                 "total_saved": 149, "total_confirmed": 8,
                 "total_overdue_missing": 58, "venues": venues}
        r = summarize(d, venue_report=audit)
        self.assertIn("uneven_venue_result_coverage", r["blocking_reasons"])
        self.assertEqual(r["venue_coverage"]["zero_confirmed_venues"], ["20261103:02"])
        self.assertEqual(r["venue_coverage"]["mature_venues"], 2)
        self.assertFalse(r["production_promotion_allowed"])

    def test_mismatched_venue_denominator_fails_closed(self):
        audit = {"formal": False, "verified_first_remote_publication": False,
                 "total_saved": 149, "total_confirmed": 9,
                 "total_overdue_missing": 58, "venues": {}}
        with self.assertRaises(ValueError):
            summarize(fixture(), venue_report=audit)

    def test_unvalidated_venue_audit_is_not_promoted(self):
        r = summarize(fixture())
        self.assertIn("venue_representation_not_audited", r["blocking_reasons"])

    def test_rejects_misreported_actual_changes(self):
        d = fixture()
        d["groups"]["20261103"]["changed_top3_membership"] = 4
        with self.assertRaises(ValueError):
            summarize(d)

    def test_reports_eligibility_separately_from_actual_reorder(self):
        r = summarize(fixture())
        self.assertEqual(r["total"]["applied"], 3)
        self.assertEqual(r["total"]["reordered_top10"], 2)
        self.assertEqual(r["total"]["changed_top3_membership"], 1)

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

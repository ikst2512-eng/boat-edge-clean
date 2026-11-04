import unittest
from four_mode_research_batch import summarize

class BatchTests(unittest.TestCase):
    def test_separate_modes_and_no_formal_claims(self):
        def case(code, root):
            return {"race_code": code, "status": "historical_comparison_only",
                    "formal": False, "remote_first_seen_verified": False,
                    "modes": {m: {"coverage_diagnostic": "covered" if m == "hit" else "winner_head_absent",
                                   "race_dynamics_cause": "not_determined",
                                   "winning_rank": 1 if m == "hit" else None,
                                   "top3": m == "hit", "top5": m == "hit", "top10": m == "hit"}
                              for m in ("hit", "balance", "hole", "narrow")}}
        result = summarize(["202610280101", "202610280102"], comparator=case)
        self.assertEqual(result["modes"]["hit"]["topn_hits"]["top1"], 2)
        self.assertEqual(result["modes"]["hit"]["topn_hits"]["top3"], 2)
        self.assertEqual(result["paired_top10"]["narrow_vs_hit"]["topn"]["top1"]["right_only"], 2)
        self.assertEqual(len(result["pairwise_topn"]), 6)
        self.assertEqual(result["pairwise_topn"]["hit_vs_hole"]["topn"]["top1"]["left_only"], 2)
        self.assertEqual(len(result["per_race"]), 2)
        self.assertEqual(result["per_race"][0]["modes"]["hit"]["winning_rank"], 1)
        self.assertEqual(result["modes"]["hole"]["topn_hits"]["top10"], 0)
        paired = result["paired_top10"]["narrow_vs_hit"]
        self.assertEqual(paired["right_only_top10"], 2)
        self.assertEqual(paired["left_only_top10"], 0)
        self.assertEqual(paired["evaluated"], 2)
        self.assertFalse(paired["formal"])
        self.assertEqual(paired["topn"]["top3"]["net_additional_hits"], 2)
        self.assertEqual(paired["topn"]["top5"]["net_percentage_points"], 100.0)
        self.assertEqual(paired["topn"]["top10"]["both"], 0)
        self.assertFalse(result["formal"])
        self.assertFalse(result["model_improvement_proven"])
    def test_pending_not_counted_as_miss(self):
        def pending(code, root):
            return {"race_code": code, "status": "result_unavailable", "formal": False}
        x = summarize(["202610280101"], comparator=pending)
        self.assertEqual(x["historical_comparable"], 0)
        self.assertIsNone(x["modes"]["hit"]["historical_topn_pct"]["top3"])
        self.assertEqual(x["paired_top10"]["hit_vs_balance"]["evaluated"], 0)
        self.assertIsNone(x["paired_top10"]["hit_vs_balance"]["topn"]["top5"]["net_percentage_points"])
    def test_missing_flags_not_silently_counted_as_misses(self):
        def faulty(code, root):
            modes = {mode: {"coverage_diagnostic": "winner_head_absent",
                           "race_dynamics_cause": "not_determined",
                           "winning_rank": None, "top3": False, "top5": False, "top10": False}
                     for mode in ("narrow", "hit", "balance", "hole")}
            del modes["hole"]["top5"]
            return {"race_code": code, "status": "historical_comparison_only",
                    "formal": False, "remote_first_seen_verified": False, "modes": modes}
        with self.assertRaisesRegex(ValueError, "invalid_topn_flags"):
            summarize(["202610280101"], comparator=faulty)

    def test_nonmonotonic_flags_rejected(self):
        def faulty(code, root):
            modes = {mode: {"coverage_diagnostic": "winner_head_absent",
                           "race_dynamics_cause": "not_determined",
                           "winning_rank": None,
                           "top3": False, "top5": False, "top10": False}
                     for mode in ("narrow", "hit", "balance", "hole")}
            modes["hit"]["top3"] = True
            modes["hit"]["winning_rank"] = 4
            return {"race_code": code, "status": "historical_comparison_only",
                    "formal": False, "remote_first_seen_verified": False, "modes": modes}
        with self.assertRaisesRegex(ValueError, "rank_topn_mismatch"):
            summarize(["202610280101"], comparator=faulty)

    def test_covered_beyond_top10_is_valid(self):
        def case(code, root):
            return {"race_code": code, "status": "historical_comparison_only",
                    "formal": False, "remote_first_seen_verified": False,
                    "modes": {m: {"coverage_diagnostic": "covered",
                                  "race_dynamics_cause": "not_determined",
                                  "winning_rank": 11, "top3": False, "top5": False, "top10": False}
                              for m in ("narrow", "hit", "balance", "hole")}}
        result = summarize(["202610280101"], comparator=case)
        self.assertEqual(result["historical_comparable"], 1)
        self.assertEqual(result["modes"]["hit"]["coverage"]["covered"], 1)
        self.assertEqual(result["modes"]["hit"]["topn_hits"]["top10"], 0)

    def test_missing_rank_rejected(self):
        def case(code, root):
            return {"race_code": code, "status": "historical_comparison_only",
                    "formal": False, "remote_first_seen_verified": False,
                    "modes": {m: {"coverage_diagnostic": "winner_head_absent",
                                   "race_dynamics_cause": "not_determined",
                                   "top3": False, "top5": False, "top10": False}
                              for m in ("hit", "balance", "hole", "narrow")}}
        with self.assertRaisesRegex(ValueError, "missing_winning_rank"):
            summarize(["202610280101"], comparator=case)

    def test_rank_2_is_not_top1(self):
        def case(code, root):
            return {"race_code": code, "status": "historical_comparison_only",
                    "formal": False, "remote_first_seen_verified": False,
                    "modes": {m: {"coverage_diagnostic": "covered",
                                   "race_dynamics_cause": "not_determined",
                                   "winning_rank": 2, "top3": True,
                                   "top5": True, "top10": True}
                              for m in ("hit", "balance", "hole", "narrow")}}
        x = summarize(["202610280101"], comparator=case)
        self.assertEqual(x["modes"]["hit"]["topn_hits"]["top1"], 0)
        self.assertEqual(x["modes"]["hit"]["topn_hits"]["top3"], 1)

    def test_real_cohort_top1_same_denominator(self):
        from four_mode_historical_cohort import run
        result = run(limit=12)
        if result["status"] != "historical_research_only":
            self.skipTest("No real frozen race/result pairs")
        self.assertEqual(result["requested"], 12)
        self.assertEqual(len(result["cohort_codes"]), 12)
        self.assertFalse(result["cohort_membership_frozen"])
        import hashlib
        expected_hash = hashlib.sha256(
            ("\n".join(sorted(result["cohort_codes"])) + "\n").encode("ascii")
        ).hexdigest()
        self.assertEqual(result["cohort_sha256"], expected_hash)
        self.assertEqual(len(result["per_race"]), result["historical_comparable"])
        self.assertEqual(len(result["pairwise_topn"]), 6)
        for pair, item in result["pairwise_topn"].items():
            left, right = pair.split("_vs_")
            for k in ("top1", "top3", "top5", "top10"):
                v = item["topn"][k]
                self.assertEqual(sum(v[x] for x in ("both", "left_only", "right_only", "neither")),
                                 result["historical_comparable"])
                self.assertEqual(v["both"] + v["left_only"], result["topn_hits"][left][k])
                self.assertEqual(v["both"] + v["right_only"], result["topn_hits"][right][k])
        self.assertEqual({row["race_code"] for row in result["per_race"]},
                         set(result["cohort_codes"]))
        n = result["historical_comparable"]
        self.assertGreater(n, 0)
        for mode in ("narrow", "hit", "balance", "hole"):
            counts = result["topn_hits"][mode]
            self.assertLessEqual(counts["top1"], counts["top3"])
            self.assertLessEqual(counts["top3"], counts["top5"])
            self.assertLessEqual(counts["top5"], counts["top10"])
            self.assertLessEqual(counts["top10"], n)

    def test_duplicates_rejected(self):
        with self.assertRaises(ValueError):
            summarize(["202610280101"]*2)

if __name__=="__main__":
    unittest.main()

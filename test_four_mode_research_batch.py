import unittest
from four_mode_research_batch import summarize

class BatchTests(unittest.TestCase):
    def test_separate_modes_and_no_formal_claims(self):
        def case(code, root):
            return {"race_code": code, "status": "historical_comparison_only",
                    "formal": False, "remote_first_seen_verified": False,
                    "modes": {m: {"coverage_diagnostic": "covered" if m == "hit" else "winner_head_absent",
                                   "race_dynamics_cause": "not_determined",
                                   "top3": m == "hit", "top5": m == "hit", "top10": m == "hit"}
                              for m in ("hit", "balance", "hole", "narrow")}}
        result = summarize(["202610280101", "202610280102"], comparator=case)
        self.assertEqual(result["modes"]["hit"]["topn_hits"]["top3"], 2)
        self.assertEqual(result["modes"]["hole"]["topn_hits"]["top10"], 0)
        paired = result["paired_top10"]["narrow_vs_hit"]
        self.assertEqual(paired["right_only_top10"], 2)
        self.assertEqual(paired["left_only_top10"], 0)
        self.assertEqual(paired["evaluated"], 2)
        self.assertFalse(paired["formal"])
        self.assertFalse(result["formal"])
        self.assertFalse(result["model_improvement_proven"])
    def test_pending_not_counted_as_miss(self):
        def pending(code, root):
            return {"race_code": code, "status": "result_unavailable", "formal": False}
        x = summarize(["202610280101"], comparator=pending)
        self.assertEqual(x["historical_comparable"], 0)
        self.assertIsNone(x["modes"]["hit"]["historical_topn_pct"]["top3"])
        self.assertEqual(x["paired_top10"]["hit_vs_balance"]["evaluated"], 0)
    def test_duplicates_rejected(self):
        with self.assertRaises(ValueError):
            summarize(["202610280101"]*2)

if __name__=="__main__":
    unittest.main()

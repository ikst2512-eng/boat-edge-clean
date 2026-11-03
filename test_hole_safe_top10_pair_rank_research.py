import unittest
from unittest.mock import patch
from hole_safe_top10_pair_rank_research import pick,compare

def archive(high_discard=False):
    base=["1-2-3","1-3-4","1-2-4","1-3-5","1-4-2",
          "1-4-3","1-4-5","1-2-5","1-3-2","1-2-6"]
    rows=[{"combo":t,"p":100.0 if high_discard else 0.3} for t in base]
    hit=[("1-5-2",3.0),("1-5-3",2.0),("1-6-2",8.0),("1-6-3",6.0)]
    return {"modes":{"hole":{"tickets":rows},
        "hit":{"tickets":[{"combo":t,"p":p} for t,p in hit]},
        "balance":{"tickets":[{"combo":"1-5-4","p":0.1}]}}}

class SafeRankingTests(unittest.TestCase):
    def test_pair_ranking_and_top5_preservation(self):
        a=archive()
        for name in ("first_eligible","highest_joint_p","pair_agreement","score_margin_guard"):
            new=pick(a,name);base=pick(a,"baseline")
            self.assertEqual(new[:5],base[:5])
            self.assertEqual(len(new),len(base))
            self.assertEqual(len(set(new)),len(base))
            self.assertTrue({tuple(x.split("-")[:2]) for x in base}.issubset(
                {tuple(x.split("-")[:2]) for x in new}))
        self.assertEqual(pick(a,"highest_joint_p")[5:7],["1-6-2","1-6-3"])
        self.assertEqual(pick(a,"pair_agreement")[5:7],["1-5-2","1-5-3"])
    def test_uncalibrated_guard_can_abstain(self):
        self.assertEqual(pick(archive(high_discard=True),"score_margin_guard"),
                         pick(archive(high_discard=True),"baseline"))
    def test_tenth_ticket_gain_without_displacing_top5(self):
        a=archive()
        with patch("hole_safe_top10_pair_rank_research.archived_four_modes",return_value=(200,a)),patch(
            "hole_safe_top10_pair_rank_research.compare_race",
            return_value={"status":"historical_comparison_only","winning_ticket":"1-6-3"}):
            r=compare(["202611031001"],".")
        self.assertEqual(r["topn"]["highest_joint_p"]["top10"]["gained"],1)
        self.assertEqual(r["topn"]["highest_joint_p"]["top5"]["gained"],0)
        self.assertEqual(r["topn"]["highest_joint_p"]["top5"]["lost"],0)
    def test_missing_confirmed_results_not_in_hits(self):
        with patch("hole_safe_top10_pair_rank_research.archived_four_modes",return_value=(200,archive())),patch(
            "hole_safe_top10_pair_rank_research.compare_race",
            return_value={"status":"result_unavailable"}):
            r=compare(["202611031001"],".")
        self.assertEqual(r["comparable"],0)
        self.assertEqual(r["unavailable"]["unconfirmed_result"],1)
    def test_invalid_policy(self):
        with self.assertRaises(ValueError):pick(archive(),"unlisted")
if __name__=="__main__":unittest.main()

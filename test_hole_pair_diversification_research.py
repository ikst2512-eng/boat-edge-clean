import unittest
from unittest.mock import patch
from hole_pair_diversification_research import diversify,inspect,first_second

def example():
    base=["1-2-3","1-3-4","1-2-4","1-3-5","1-4-2",
          "1-4-3","1-4-5","1-2-5","1-3-2","1-2-6"]
    return {"modes":{
      "hole":{"tickets":[{"combo":x,"p":1.0} for x in base]},
      "hit":{"tickets":[{"combo":x,"p":2.0} for x in
                         ("1-5-2","1-5-3","1-6-2","1-6-3")]},
      "balance":{"tickets":[{"combo":"1-5-4","p":1.0}]}}}

class DiversificationTests(unittest.TestCase):
 def test_two_distinct_pairs_without_top5_loss(self):
  a=example()
  old=[r["combo"] for r in a["modes"]["hole"]["tickets"]]
  new=diversify(a)
  self.assertEqual(old[:5],new[:5])
  self.assertEqual(new[5:7],["1-5-2","1-6-2"])
  self.assertEqual(len(set(new)),10)
  self.assertTrue({first_second(t) for t in old}.issubset({first_second(t) for t in new}))
 def test_single_donor_pair_abstains(self):
  a=example()
  a["modes"]["hit"]["tickets"]=a["modes"]["hit"]["tickets"][:2]
  self.assertEqual(diversify(a),[r["combo"] for r in a["modes"]["hole"]["tickets"]])
 def test_pair_rank_two_is_covered_but_third_specific(self):
  a=example()
  with patch("hole_pair_diversification_research.archived_four_modes",return_value=(200,a)),patch(
       "hole_pair_diversification_research.compare_race",
       return_value={"status":"historical_comparison_only","winning_ticket":"1-6-2"}):
   r=inspect(["202611031801"],".")
  self.assertEqual(r["pair_selection"]["second_pair_selected"],1)
  self.assertEqual(r["topn"]["two_pairs_one_third"]["top10"]["gained"],1)
  self.assertEqual(r["topn"]["two_pairs_one_third"]["top5"]["lost"],0)
 def test_correct_pair_wrong_third_not_miscounted(self):
  a=example()
  with patch("hole_pair_diversification_research.archived_four_modes",return_value=(200,a)),patch(
       "hole_pair_diversification_research.compare_race",
       return_value={"status":"historical_comparison_only","winning_ticket":"1-6-3"}):
   r=inspect(["202611031801"],".")
  self.assertEqual(r["pair_selection"]["second_pair_selected"],1)
  self.assertEqual(r["pair_selection"]["correct_ticket_added"],0)
  self.assertEqual(r["topn"]["two_pairs_one_third"]["top10"]["gained"],0)
 def test_result_not_required_for_choice(self):
  self.assertEqual(len(diversify(example())),10)
if __name__=="__main__":unittest.main()

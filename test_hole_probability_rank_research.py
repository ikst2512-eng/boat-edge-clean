import unittest
from hole_probability_rank_research import sorted_donor
class FrozenScoreTests(unittest.TestCase):
 def test_ticket_score(self):
  h=[{"combo":"1-2-3","p":2.0},{"combo":"1-3-2","p":3.0}]
  self.assertEqual(sorted_donor(h,[],"ticket_p")[0],"1-3-2")
 def test_pair_sum_changes_priority(self):
  h=[{"combo":"1-2-3","p":2.0},{"combo":"1-2-4","p":2.0},{"combo":"1-3-2","p":3.0}]
  self.assertEqual(sorted_donor(h,[],"pair_sum_p")[0],"1-2-3")
 def test_duplicate_ticket_not_double_counted(self):
  h=[{"combo":"1-2-3","p":2.0}]
  b=[{"combo":"1-2-3","p":2.0}]
  self.assertEqual(sorted_donor(h,b,"pair_sum_p"),["1-2-3"])
 def test_unknown_policy_fails(self):
  with self.assertRaises(ValueError):sorted_donor([],[],"bad")
if __name__=="__main__": unittest.main()

import unittest
from hole_donor_ranking_research import donor_order
class RankingTest(unittest.TestCase):
 def test_agreement_first(self):
  a=donor_order(["1-2-3","1-3-4"],["1-3-5","1-4-2"],"pair_agreement")
  self.assertEqual(a[0],"1-3-4")
 def test_no_duplicates(self):
  a=donor_order(["1-2-3"],["1-2-3","1-3-4"],"hit_first")
  self.assertEqual(a,["1-2-3","1-3-4"])
 def test_unknown_rejected(self):
  with self.assertRaises(ValueError):donor_order([],[],"invalid")
if __name__=="__main__":unittest.main()

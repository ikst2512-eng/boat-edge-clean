import unittest
from hole_pair_blocker_diagnostic import reason
class PairBlockers(unittest.TestCase):
 def test_insert_possible(self):
  self.assertEqual(reason(["1-2-3","1-2-4","1-3-4"],["1-4-2"],3),"insertion_possible")
 def test_no_pair_to_evict(self):
  self.assertEqual(reason(["1-2-3","1-3-4","1-4-2"],["1-5-2"],3),"no_redundant_pair_to_evict")
 def test_donor_no_same_head(self):
  self.assertEqual(reason(["1-2-3","1-2-4","1-3-4"],["2-4-1"],3),"no_new_same_head_pair_in_donor")
if __name__=="__main__":unittest.main()

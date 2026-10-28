import unittest
from research_compare_hit12_stakes import weights
from four_mode_performance import allocate
class StakeTests(unittest.TestCase):
    def test_fixed_budget_all_tickets_covered(self):
        tickets=[{"combo":c} for c in ("1-2-3","1-2-4","1-2-5","1-2-6","1-3-2","1-3-4","1-3-5","1-3-6","1-4-2","1-4-3","1-4-5","1-4-6")]
        for n in (3,5):
            w=weights(tickets,n)
            self.assertEqual(sum(w.values()),10000)
            self.assertEqual(len(w),12)
            self.assertTrue(all(x>=100 and x%100==0 for x in w.values()))
            self.assertGreater(w["1-2-3"],w["1-4-6"])
        self.assertEqual(sum(allocate(tickets,10000).values()),10000)
if __name__=="__main__":unittest.main()

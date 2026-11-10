import unittest
from four_mode_first_diversity_experiment import rerank

class DiversityTests(unittest.TestCase):
    def test_membership_and_baseline(self):
        tickets = [{"combo": c, "p": p} for c,p in [
            ("1-2-3",10),("1-2-4",9),("1-3-2",8),("2-1-3",7),
            ("3-1-2",6),("1-4-2",5),("2-3-1",4),("3-2-1",3),
            ("4-1-2",2),("5-1-2",1)]]
        original = [t["combo"] for t in tickets]
        self.assertEqual(rerank(tickets,0),original)
        changed = rerank(tickets,.30)
        self.assertEqual(set(changed),set(original))
        self.assertEqual(len(changed),10)
        self.assertEqual(changed[0],original[0])
    def test_reject_duplicate(self):
        with self.assertRaises(ValueError):
            rerank([{"combo":"1-2-3","p":10}]*10,.30)

if __name__=="__main__":
    unittest.main()

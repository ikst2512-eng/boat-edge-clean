import unittest
from hole_upper_rank_pair_protection import propose

class UpperRankTests(unittest.TestCase):
    def setUp(self):
        self.base=["1-2-3","1-2-4","1-3-2","2-3-1","2-3-4",
                   "3-4-1","3-4-2","1-2-5","2-3-5","3-4-5"]
    def test_rank3_preserves_pairs(self):
        out=propose(self.base,["1-4-2"],3)
        self.assertEqual(out[:2],self.base[:2])
        self.assertEqual(out[2],"1-4-2")
        self.assertEqual(len(out),10)
        self.assertEqual(len(set(out)),10)
        self.assertTrue({tuple(x.split("-")[:2]) for x in self.base}.issubset({tuple(x.split("-")[:2]) for x in out}))
    def test_rank5(self):
        self.assertEqual(propose(self.base,["1-4-2"],5)[4],"1-4-2")
    def test_no_duplicate_pair_to_evict(self):
        base=["1-2-3","1-3-2","1-4-2"]
        self.assertEqual(propose(base,["1-5-2"],3),base)
    def test_unknown_head(self):
        self.assertEqual(propose(self.base,["4-2-1"],3),self.base)

if __name__=="__main__":
    unittest.main()

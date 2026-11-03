import unittest
from hole_second_pair_preservation import preserve_pair_coverage

class PreservationTest(unittest.TestCase):
    def test_preserves_pairs_and_budget(self):
        base=["1-2-3","1-2-4","1-3-2","2-3-1","2-3-4","3-4-1","3-4-2","1-2-5","2-3-5","3-4-5"]
        new=preserve_pair_coverage(base,["1-4-2"],protect_top=3)
        self.assertEqual(new[:3],base[:3])
        self.assertEqual(len(new),len(base))
        self.assertEqual(len(set(new)),len(new))
        self.assertIn("1-4-2",new)
        self.assertTrue({tuple(x.split("-")[:2]) for x in base}.issubset({tuple(x.split("-")[:2]) for x in new}))
    def test_no_duplicated_pair_means_no_swap(self):
        base=["1-2-3","1-3-2","1-4-2"]
        self.assertEqual(preserve_pair_coverage(base,["1-5-2"],protect_top=0),base)
    def test_only_protected_duplicate_means_no_swap(self):
        base=["1-2-3","1-2-4","1-3-2"]
        self.assertEqual(preserve_pair_coverage(base,["1-5-2"],protect_top=2),base)

if __name__=="__main__":unittest.main()

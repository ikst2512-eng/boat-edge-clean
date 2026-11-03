import unittest
from hole_pair_third_bundle_research import bundle
class BundleTests(unittest.TestCase):
 def test_two_new_thirds_preserve_pairs(self):
  base=["1-2-3","1-3-4","1-2-4","1-3-5","1-4-2"]
  result=bundle(base,["1-5-2","1-5-3"],3,2)
  self.assertEqual(len(result),5)
  self.assertEqual(result[2:4],["1-5-2","1-5-3"])
  self.assertIn("1-2",["-".join(t.split("-")[:2]) for t in result])
  self.assertIn("1-3",["-".join(t.split("-")[:2]) for t in result])
 def test_no_double_eviction_without_duplicates(self):
  base=["1-2-3","1-3-4","1-4-2","1-5-3"]
  self.assertEqual(bundle(base,["1-6-2","1-6-3"],3,2),base)
 def test_no_partial_bundle(self):
  base=["1-2-3","1-3-4","1-2-4","1-3-5"]
  self.assertEqual(bundle(base,["1-5-2"],3,2),base)
if __name__=="__main__":unittest.main()

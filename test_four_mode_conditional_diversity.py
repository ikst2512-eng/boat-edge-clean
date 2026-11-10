import unittest
from four_mode_conditional_diversity import reorder
class ConditionalTests(unittest.TestCase):
 def test_membership(self):
  t=[{"combo":c,"p":10-i} for i,c in enumerate(["1-2-3","1-2-4","1-3-2","2-1-3","3-1-2","1-4-2","2-3-1","3-2-1","4-1-2","5-1-2"])]
  self.assertEqual(set(reorder(t,0.30)),{x["combo"] for x in t})
  self.assertEqual(reorder(t,0),[x["combo"] for x in t])
if __name__=="__main__":unittest.main()

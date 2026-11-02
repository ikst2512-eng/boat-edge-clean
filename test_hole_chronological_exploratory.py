import unittest
from hole_chronological_exploratory import date_blocks
class DateBlockTest(unittest.TestCase):
    def test_disjoint_chronology(self):
        r=date_blocks(["202610300101","202611010101","202611020101","202611030101"])
        self.assertEqual(r["status"],"date_blocked")
        self.assertLess(max(x[:8] for x in r["earlier"]),min(x[:8] for x in r["later"]))
    def test_single_date_fails_closed(self):
        r=date_blocks(["202611020101","202611020102"])
        self.assertEqual(r["status"],"insufficient_distinct_dates")
        self.assertEqual(r["later"],[])
    def test_same_day_stays_together(self):
        r=date_blocks(["202611010101","202611010102","202611020101"])
        self.assertTrue(all(c[:8]=="20261101" for c in r["earlier"]))
        self.assertTrue(all(c[:8]=="20261102" for c in r["later"]))
if __name__=="__main__": unittest.main()

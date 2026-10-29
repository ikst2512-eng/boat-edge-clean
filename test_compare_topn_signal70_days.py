import unittest
from compare_topn_signal70_days import report
class Tests(unittest.TestCase):
    def test_separate_discovery_and_future(self):
        def fake(day):
            return {"schema":"CLEAN_TOPN_SIGNAL70_RESEARCH_V1","day_jst":day,
                    "signal_is_empirical_confidence":False,"archived":1,"groups":{}}
        r=report(["20261028","20261029","20261030"],fake)
        self.assertEqual([x["role"] for x in r["days"]],["earlier_exploratory","discovery","later_holdout"])
        self.assertEqual(r["later_holdout_days"],1)
        self.assertFalse(r["calibrated_confidence"])
    def test_duplicate_day_fails(self):
        with self.assertRaises(ValueError):report(["20261029","20261029"])
if __name__=="__main__":unittest.main()

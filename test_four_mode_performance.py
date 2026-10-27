import unittest
from four_mode_performance import allocate,evaluate,summary

class FourModePerformanceTests(unittest.TestCase):
    def test_budgets(self):
        picks=["1-2-3","2-1-3","3-2-1"]
        for budget in (5000,7500,10000):
            self.assertEqual(sum(allocate(picks,budget).values()),budget)
        for budget in (4999,10001,5050,True,5000.0):
            with self.assertRaises(ValueError):allocate(picks,budget)

    def test_proven_only(self):
        archive={"schema":"CLEAN_FOUR_MODES_PREDEADLINE_V1","race_code":"202610280101","generated_at_jst":"2026-10-28T10:00:00+09:00","deadline_jst":"2026-10-28T11:00:00+09:00","modes":{m:{"tickets":[{"combo":"1-2-3"},{"combo":"2-1-3"}]} for m in ("hit","balance","hole","narrow")}}
        result={"race_code":"202610280101","status":"confirmed","finish_order":[1,2,3]}
        self.assertIsNone(summary([])["hit"]["actual_hit_rate_pct"])
        self.assertIsNone(summary([])["hit"]["actual_roi_pct"])
        with self.assertRaises(ValueError):evaluate(archive,result,2400)
        x=evaluate(archive,result,2400,5000,True)
        self.assertEqual(x["modes"]["hit"]["return_yen"],60000)
        self.assertEqual(summary([x])["hit"]["actual_roi_pct"],1200)
        archive["generated_at_jst"]=archive["deadline_jst"]
        with self.assertRaises(ValueError):evaluate(archive,result,2400,5000,True)

if __name__=="__main__":unittest.main()

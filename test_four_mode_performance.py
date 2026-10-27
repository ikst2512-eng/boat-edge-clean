import unittest
from datetime import datetime, timezone, timedelta
from collect_four_mode_performance import pending_result_state
from four_mode_performance import allocate,evaluate,summary

class FourModePerformanceTests(unittest.TestCase):
    def test_pending_vs_overdue_is_not_counted_as_miss(self):
        record={"deadline_jst":"2026-10-28T15:19:00+09:00"}
        early=datetime(2026,10,28,8,0,tzinfo=timezone(timedelta(hours=9)))
        late=datetime(2026,10,28,16,0,tzinfo=timezone(timedelta(hours=9)))
        self.assertEqual(pending_result_state(record,early),"before_deadline")
        self.assertEqual(pending_result_state(record,late),"overdue_result")
        with self.assertRaises(ValueError):
            pending_result_state({"deadline_jst":"2026-10-28T15:19:00"},early)
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

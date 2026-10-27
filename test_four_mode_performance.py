import unittest
from four_mode_performance import allocate, evaluate_archive, aggregate

def example():
    a={"schema":"CLEAN_FOUR_MODES_PREDEADLINE_V1","race_code":"202610280101",
       "generated_at_jst":"2026-10-28T11:00:00+09:00","deadline_jst":"2026-10-28T12:00:00+09:00",
       "modes":{name:{"tickets":[{"combo":"1-2-3"},{"combo":"2-1-3"}]} for name in ("hit","balance","hole","narrow")}}
    return a, {"race_code":a["race_code"],"status":"confirmed","finish_order":[1,2,3]}

class PerformanceTests(unittest.TestCase):
    def test_exact_budget(self):
        tickets=["1-2-3","2-1-3","3-1-2"]
        for budget in (5000, 7500, 10000):
            self.assertEqual(sum(allocate(tickets,budget).values()),budget)
        for bad in (4999, 10001, 5050, 5000.0, True):
            with self.assertRaises(ValueError):allocate(tickets,bad)

    def test_verified_returns(self):
        a,r=example()
        out=evaluate_archive(a,r,2500,7500,True)
        self.assertEqual(out["modes"]["hit"]["return_yen"],3800*25)
        self.assertEqual(out["modes"]["hit"]["budget_yen"],7500)
        summary=aggregate([out])
        self.assertEqual(summary["hit"]["actual_hit_rate_pct"],100)
        self.assertEqual(summary["hit"]["actual_roi_pct"],round(95000/7500*100,2))

    def test_reject_nonverified(self):
        a,r=example()
        with self.assertRaises(ValueError):evaluate_archive(a,r,2500,5000,False)
        a["generated_at_jst"]=a["deadline_jst"]
        with self.assertRaises(ValueError):evaluate_archive(a,r,2500,5000,True)
        self.assertIsNone(aggregate([])["hit"]["actual_hit_rate_pct"])
        self.assertIsNone(aggregate([])["hit"]["actual_roi_pct"])

if __name__=="__main__":unittest.main()

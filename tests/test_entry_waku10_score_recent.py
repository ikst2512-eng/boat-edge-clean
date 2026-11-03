import unittest
from datetime import datetime,timedelta,timezone
from entry_waku10_score_recent import score_recent

JST=timezone(timedelta(hours=9))
NOW=datetime(2026,11,4,23,30,tzinfo=JST)

class CatchupTests(unittest.TestCase):
    def test_today_yesterday_and_two_days_prior_remain_separate(self):
        seen=[]
        def score(root,day):
            seen.append(day)
            return {"day":day,"paired_races":1 if day=="20261103" else 0}
        r=score_recent(".",now=NOW,evaluator=score)
        self.assertEqual(seen,["20261104","20261103","20261102"])
        self.assertEqual(r["sum_of_disjoint_day_matched_races"],1)
        self.assertEqual(r["days_with_paired_races"],1)
        self.assertEqual(r["completed_days"],3)
        self.assertFalse(r["empirical_accuracy_improvement_proven"])
    def test_api_failure_not_misreported_as_zero_hits(self):
        def score(root,day):
            if day=="20261103":raise OSError("source not published yet")
            return {"day":day,"paired_races":0}
        r=score_recent(".",now=NOW,evaluator=score)
        self.assertEqual(r["completed_days"],2)
        self.assertEqual(r["failed_days"],[{"day":"20261103","error_type":"OSError"}])
        self.assertEqual(len(r["day_reports"]),2)
    def test_wrong_day_response_cannot_pollute_cohort(self):
        r=score_recent(".",now=NOW,days_back=0,
                      evaluator=lambda root,day:{"day":"20261103","paired_races":1})
        self.assertEqual(r["completed_days"],0)
        self.assertEqual(r["failed_days"][0]["error_type"],"ValueError")
    def test_clock_is_japan_local_even_if_utc_argument(self):
        now=datetime(2026,11,3,15,15,tzinfo=timezone.utc)
        r=score_recent(".",now=now,days_back=0,
                       evaluator=lambda root,day:{"day":day,"paired_races":0})
        self.assertEqual(r["checked_days"],["20261104"])
    def test_window_and_naive_time_guard(self):
        with self.assertRaisesRegex(ValueError,"out_of_bounds"):
            score_recent(".",now=NOW,days_back=30)
        with self.assertRaisesRegex(ValueError,"requires_timezone"):
            score_recent(".",now=datetime(2026,11,4,23,30))
if __name__=="__main__":unittest.main()

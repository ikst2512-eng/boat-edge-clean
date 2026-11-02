import unittest
from scripts.joint_t12_decision import decision, can_retry
class DecisionTests(unittest.TestCase):
    def test_fetch_before_cutoff(self):
        self.assertEqual(decision("2026-11-02T22:29:00+09:00","2026-11-02T22:45:00+09:00","2026-11-02T22:30:00+09:00")["status"],"fetch_odds")
    def test_observation_after_cutoff_rejected(self):
        self.assertEqual(decision("2026-11-02T22:33:01+09:00","2026-11-02T22:45:00+09:00","2026-11-02T22:33:01+09:00")["status"],"beforeinfo_after_t12")
    def test_near_cutoff_no_request(self):
        self.assertEqual(decision("2026-11-02T22:32:00+09:00","2026-11-02T22:45:00+09:00","2026-11-02T22:32:40+09:00")["status"],"insufficient_time_to_fetch_odds")
    def test_retry_guards(self):
        deadline="2026-11-02T22:45:00+09:00"
        self.assertTrue(can_retry("2026-11-02T22:30:00+09:00",deadline,1,6))
        self.assertFalse(can_retry("2026-11-02T22:32:20+09:00",deadline,1,6))
        self.assertFalse(can_retry("2026-11-02T22:30:00+09:00",deadline,6,6))
    def test_fail_closed(self):
        self.assertFalse(decision("2026-11-02T22:29:00+09:00","2026-11-02T22:45:00+09:00","2026-11-02T22:30:00+09:00")["forecast_usable"])
    def test_reject_naive_timestamp(self):
        with self.assertRaises(ValueError): decision("2026-11-02T22:29:00","2026-11-02T22:45:00+09:00","2026-11-02T22:30:00+09:00")
if __name__=="__main__": unittest.main()

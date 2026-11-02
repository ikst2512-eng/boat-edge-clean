import unittest
from scripts.joint_t12_decision import decision, can_retry, receipt_at_or_before_t12
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
    def test_retry_invalid_counters_fail_closed(self):
        deadline="2026-11-02T22:45:00+09:00"
        now="2026-11-02T22:30:00+09:00"
        for attempt, attempts in [(0,6),(-1,6),(1,0),(1,7),(7,8),(6,6),(1,1),(True,6),(1,True),(1.0,6),(1,6.0)]:
            with self.subTest(attempt=attempt, attempts=attempts):
                self.assertFalse(can_retry(now,deadline,attempt,attempts))
        self.assertTrue(can_retry(now,deadline,1,6))
        self.assertTrue(can_retry(now,deadline,5,6))

    def test_retry_exact_safety_margin(self):
        deadline="2026-11-02T22:45:00+09:00"
        self.assertFalse(can_retry("2026-11-02T22:32:05+09:00",deadline,1,6))
        self.assertTrue(can_retry("2026-11-02T22:32:04.999999+09:00",deadline,1,6))

    def test_receipt_time_boundary(self):
        deadline="2026-11-02T22:45:00+09:00"
        self.assertTrue(receipt_at_or_before_t12("2026-11-02T22:33:00+09:00",deadline))
        self.assertFalse(receipt_at_or_before_t12("2026-11-02T22:33:00.000001+09:00",deadline))
        self.assertFalse(receipt_at_or_before_t12("2026-11-02T22:34:00+09:00",deadline))
    def test_receipt_naive_timestamp_rejected(self):
        with self.assertRaises(ValueError): receipt_at_or_before_t12("2026-11-02T22:33:00","2026-11-02T22:45:00+09:00")
    def test_fail_closed(self):
        self.assertFalse(decision("2026-11-02T22:29:00+09:00","2026-11-02T22:45:00+09:00","2026-11-02T22:30:00+09:00")["forecast_usable"])
    def test_reject_naive_timestamp(self):
        with self.assertRaises(ValueError): decision("2026-11-02T22:29:00","2026-11-02T22:45:00+09:00","2026-11-02T22:30:00+09:00")
if __name__=="__main__": unittest.main()

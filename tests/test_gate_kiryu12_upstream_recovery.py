import unittest
from datetime import datetime, timedelta, timezone
from scripts.gate_kiryu12_upstream_recovery import check_window

JST = timezone(timedelta(hours=9))
def when(h,m,s=0):
    return datetime(2026,11,3,h,m,s,tzinfo=JST)

class Kiryu12GateTests(unittest.TestCase):
    def test_open_inclusive(self):
        self.assertTrue(check_window(when(19,30),when(19,30).isoformat()))
    def test_before_open_rejected(self):
        with self.assertRaisesRegex(ValueError,"outside safe"):
            check_window(when(19,29,59),when(19,29).isoformat())
    def test_last_second_allowed(self):
        self.assertTrue(check_window(when(20,17,29),when(20,7).isoformat()))
    def test_ninety_second_buffer_strict(self):
        with self.assertRaisesRegex(ValueError,"outside safe"):
            check_window(when(20,17,30),when(20,7).isoformat())
    def test_t12_cutoff_rejected(self):
        with self.assertRaisesRegex(ValueError,"outside safe"):
            check_window(when(20,19),when(20,7).isoformat())
    def test_previous_day_rejected(self):
        with self.assertRaisesRegex(ValueError,"upstream run stale"):
            check_window(when(19,52),datetime(2026,11,2,19,37,tzinfo=JST).isoformat())
    def test_future_started_rejected(self):
        with self.assertRaisesRegex(ValueError,"upstream run stale"):
            check_window(when(19,52),when(20,7).isoformat())
    def test_naive_datetime_rejected(self):
        with self.assertRaisesRegex(ValueError,"now needs timezone"):
            check_window(datetime(2026,11,3,19,52),when(19,37).isoformat())
    def test_naive_upstream_rejected(self):
        with self.assertRaisesRegex(ValueError,"upstream needs timezone"):
            check_window(when(19,52),"2026-11-03T19:37:00")
    def test_utc_upstream_accepted(self):
        self.assertTrue(check_window(when(19,52),when(19,37).astimezone(timezone.utc).isoformat().replace("+00:00","Z")))
    def test_wrong_year_rejected(self):
        with self.assertRaisesRegex(ValueError,"outside safe"):
            check_window(datetime(2027,11,3,19,52,tzinfo=JST),when(19,37).isoformat())
if __name__=="__main__":
    unittest.main()

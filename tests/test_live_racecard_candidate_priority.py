"""T-12 opportunity ranking cannot be mistaken for verified source evidence."""
import unittest
from datetime import datetime,timedelta
from zoneinfo import ZoneInfo
from scripts.live_racecard_candidate_priority import rank_candidates,t12_window_open

JST=ZoneInfo("Asia/Tokyo")
NOW=datetime(2026,11,4,17,30,tzinfo=JST)

def race(code,minutes):
    return (NOW+timedelta(minutes=minutes),code)

class LiveRacecardCandidatePriorityTests(unittest.TestCase):
    def test_t12_possible_precedes_last_minute_matched_preview(self):
        candidates=[race("near",5),race("future_missing",28),race("future_matched",21)]
        ranked=rank_candidates(candidates,{"near","future_matched"},NOW)
        self.assertEqual([code for _,code in ranked],
                         ["future_matched","future_missing","near"])

    def test_near_cutoff_never_claimed_t12_eligible(self):
        self.assertFalse(t12_window_open(NOW+timedelta(minutes=2),NOW))
        self.assertFalse(t12_window_open(NOW+timedelta(minutes=11,seconds=59),NOW))
        self.assertFalse(t12_window_open(NOW+timedelta(minutes=12),NOW))
        self.assertTrue(t12_window_open(NOW+timedelta(minutes=12,seconds=1),NOW))

    def test_no_t12_opportunity_still_preserves_card_diagnostics(self):
        candidates=[race("near_matched",5),race("near_unmatched",7)]
        ranked=rank_candidates(candidates,{"near_matched"},NOW)
        self.assertEqual(len(ranked),2)
        self.assertEqual([code for _,code in ranked],["near_matched","near_unmatched"])
        self.assertTrue(all(not t12_window_open(deadline,NOW) for deadline,_ in ranked))

    def test_timezone_missing_fails_closed(self):
        with self.assertRaisesRegex(ValueError,"t12_clock_timezone_missing"):
            t12_window_open(datetime(2026,11,4,17,45),NOW)
        with self.assertRaisesRegex(ValueError,"t12_clock_timezone_missing"):
            rank_candidates([race("valid",20)],set(),datetime(2026,11,4,17,30))

if __name__=="__main__":
    unittest.main()

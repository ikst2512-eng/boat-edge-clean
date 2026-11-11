"""T-12 opportunity ranking cannot be mistaken for verified source evidence."""
import unittest
from datetime import datetime,timedelta
from zoneinfo import ZoneInfo
from scripts.live_racecard_candidate_priority import (rank_candidates,t12_window_open,
    live_sampling_window_open,preview_codes_at_receipt,fresh_candidates_at_selection,
    verified_csv_pair_receipts)

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

    def test_schedule_delayed_across_midnight_is_not_valid_race_window(self):
        self.assertFalse(live_sampling_window_open(datetime(2026,11,4,0,23,tzinfo=JST)))
        self.assertTrue(live_sampling_window_open(datetime(2026,11,4,9,30,tzinfo=JST)))
        self.assertTrue(live_sampling_window_open(datetime(2026,11,4,21,30,tzinfo=JST)))
        self.assertFalse(live_sampling_window_open(datetime(2026,11,4,23,30,tzinfo=JST)))

    def test_preview_published_during_http_fetch_is_eligible_by_receipt(self):
        row={"レースコード":"202611041911","締切時刻":"18:00",
             "取得日時":"2026-11-04T17:30:30+09:00"}
        receipt=datetime(2026,11,4,17,31,tzinfo=JST)
        self.assertEqual(preview_codes_at_receipt([row],"20261104",receipt),{"202611041911"})

    def test_preview_source_in_future_or_after_cutoff_does_not_qualify(self):
        future={"レースコード":"202611041911","締切時刻":"18:00",
                "取得日時":"2026-11-04T17:31:01+09:00"}
        receipt=datetime(2026,11,4,17,31,tzinfo=JST)
        self.assertEqual(preview_codes_at_receipt([future],"20261104",receipt),set())
        future["取得日時"]="2026-11-04T17:20:00+09:00"
        after=datetime(2026,11,4,18,0,tzinfo=JST)
        self.assertEqual(preview_codes_at_receipt([future],"20261104",after),set())

    def test_preview_rejects_wrong_date_and_naive_source_timestamp(self):
        receipt=datetime(2026,11,4,17,31,tzinfo=JST)
        rows=[{"レースコード":"202611031911","締切時刻":"18:00",
               "取得日時":"2026-11-03T17:20:00+09:00"},
              {"レースコード":"202611041911","締切時刻":"18:00",
               "取得日時":"2026-11-04T17:20:00"}]
        self.assertEqual(preview_codes_at_receipt(rows,"20261104",receipt),set())
        with self.assertRaisesRegex(ValueError,"preview_receipt_timezone_missing"):
            preview_codes_at_receipt(rows,"20261104",datetime(2026,11,4,17,31))
        with self.assertRaisesRegex(ValueError,"sample_clock_timezone_missing"):
            live_sampling_window_open(datetime(2026,11,4,0,23))

    def test_just_expired_during_http_is_excluded_from_live_sample(self):
        # At job start both races were upcoming; 3 minutes passed in HTTP.
        started=NOW
        selection=NOW+timedelta(minutes=3)
        candidates=[race("expired",5),race("still_valid",18)]
        eligible,expired=fresh_candidates_at_selection(candidates,selection)
        self.assertEqual([code for _,code in eligible],["still_valid"])
        self.assertEqual([code for _,code in expired],["expired"])
        self.assertTrue(t12_window_open(eligible[0][0],selection))

    def test_two_minute_sampling_margin_is_strict(self):
        selection=NOW+timedelta(minutes=4)
        candidates=[race("at_margin",6),race("just_over",6.1)]
        eligible,expired=fresh_candidates_at_selection(candidates,selection)
        self.assertEqual([code for _,code in eligible],["just_over"])
        self.assertEqual([code for _,code in expired],["at_margin"])

    def test_expired_candidates_preserved_as_diagnostics(self):
        eligible,expired=fresh_candidates_at_selection([race("closed",0),race("almost",1)],NOW)
        self.assertEqual(eligible,[])
        self.assertEqual(len(expired),2)

    def test_selection_rejects_naive_time_and_deadline(self):
        with self.assertRaisesRegex(ValueError,"candidate_selection_timezone_missing"):
            fresh_candidates_at_selection([race("x",5)],datetime(2026,11,4,17,30))
        with self.assertRaisesRegex(ValueError,"candidate_deadline_timezone_missing"):
            fresh_candidates_at_selection([(datetime(2026,11,4,17,50),"x")],NOW)

    def test_live_e2e_logs_each_independent_preview_failure(self):
        from pathlib import Path
        source=(Path(__file__).resolve().parents[1] /
                "scripts/verify_live_racecard_e2e.py").read_text()
        self.assertIn('for kind in ("tkz","stt"):',source)
        self.assertIn('"outcome":"PREVIEW_SOURCE_UNAVAILABLE","kind":kind',source)
        self.assertIn('"preview_source_status":preview_source_status',source)
        self.assertIn('preview_source_codes.get("tkz",set()) & preview_source_codes.get("stt",set())',source)

    def test_live_e2e_resamples_candidates_before_api_calls(self):
        from pathlib import Path
        source=(Path(__file__).resolve().parents[1] /
                "scripts/verify_live_racecard_e2e.py").read_text()
        refresh=source.index("fresh_candidates_at_selection(candidates,selection_now)")
        api=source.index("for source_deadline,code in candidates[:3]:")
        self.assertLess(refresh,api)
        self.assertIn('"outcome":"RACECARD_CANDIDATES_EXPIRED_DURING_SOURCE_PROBE"',source)

    def test_timezone_missing_fails_closed(self):
        with self.assertRaisesRegex(ValueError,"t12_clock_timezone_missing"):
            t12_window_open(datetime(2026,11,4,17,45),NOW)
        with self.assertRaisesRegex(ValueError,"t12_clock_timezone_missing"):
            rank_candidates([race("valid",20)],set(),datetime(2026,11,4,17,30))


    def test_official_fallback_is_valid_exhibition_but_not_a_csv_t12_pair(self):
        deadline=NOW+timedelta(minutes=20)
        receipt=NOW+timedelta(minutes=1)
        official={"status":"ok","source":"BOAT RACE official beforeinfo JSON",
                  "sources":{"official":{"received_at_jst":receipt.isoformat(),
                                         "sha256":"a"*64}}}
        times,problems=verified_csv_pair_receipts(official,deadline,receipt)
        self.assertEqual(times,{})
        self.assertEqual(problems,["tkz:source_receipt_missing",
                                   "stt:source_receipt_missing"])

    def test_valid_independent_csv_pair_is_still_eligible(self):
        deadline=NOW+timedelta(minutes=20)
        received=NOW+timedelta(minutes=2)
        audit={"sources":{kind:{"observed_at":NOW.isoformat(),"sha256":"f"*64}
                          for kind in ("tkz","stt")}}
        times,problems=verified_csv_pair_receipts(audit,deadline,received)
        self.assertEqual(problems,[])
        self.assertEqual(set(times),{"tkz","stt"})

    def test_missing_or_invalid_csv_receipts_fail_closed(self):
        deadline=NOW+timedelta(minutes=20)
        received=NOW+timedelta(minutes=1)
        audit={"sources":{"tkz":{"observed_at":"","sha256":"f"*64},
                          "stt":{"observed_at":NOW.isoformat(),"sha256":"bad"}}}
        times,problems=verified_csv_pair_receipts(audit,deadline,received)
        self.assertFalse(times)
        self.assertEqual(problems,["tkz:observed_at_missing",
                                   "stt:sha256_missing_or_invalid"])
        audit["sources"]["tkz"]["observed_at"]=(deadline+timedelta(seconds=1)).isoformat()
        audit["sources"]["stt"]["sha256"]="f"*64
        times,problems=verified_csv_pair_receipts(audit,deadline,received)
        self.assertEqual(set(times),{"stt"})
        self.assertEqual(problems,["tkz:observed_at_not_predeadline"])
        with self.assertRaisesRegex(ValueError,"csv_pair_clock_timezone_missing"):
            verified_csv_pair_receipts(audit,deadline.replace(tzinfo=None),received)

    def test_live_e2e_separates_official_exhibition_and_csv_pair(self):
        from pathlib import Path
        source=(Path(__file__).resolve().parents[1] /
                "scripts/verify_live_racecard_e2e.py").read_text()
        self.assertIn("verified_csv_pair_receipts(",source)
        self.assertIn('"reason":"independent_csv_source_pair_incomplete"',source)
        self.assertIn('"outcome":"EXHIBITION_PASS"',source)
        self.assertIn('if all(t12_checks.values()):',source)

if __name__=="__main__":
    unittest.main()

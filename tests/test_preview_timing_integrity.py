import unittest
from datetime import datetime,timedelta
from research_model import JST
from scripts.preview_timing_integrity import classify

class Timing(unittest.TestCase):
    def test_no_post_cutoff_leak(self):
        row={"締切時刻":"2026-10-31 18:00:00","取得日時":"2026-10-31 17:40:00"}
        self.assertEqual(classify(row,datetime(2026,10,31,17,45,tzinfo=JST)),"pre_cutoff_observed")
        self.assertEqual(classify(row,datetime(2026,10,31,17,50,tzinfo=JST)),"too_late")
        row["取得日時"]="2026-10-31 17:49:00"
        self.assertEqual(classify(row,datetime(2026,10,31,17,40,tzinfo=JST)),"unknown_time")
        row.update({"レースコード":"202610310101","締切時刻":"18:00","取得日時":"2026-10-31T17:40:00+09:00"})
        self.assertEqual(classify(row,datetime(2026,10,31,17,45,tzinfo=JST)),"pre_cutoff_observed")
        row.pop("取得日時")
        self.assertEqual(classify(row,datetime(2026,10,31,17,40,tzinfo=JST)),"unknown_time")
    def test_cross_day_stale_source_cannot_pass_t12(self):
        row={"レースコード":"202611010101","締切時刻":"19:00",
             "取得日時":"2026-10-31T18:30:00+09:00"}
        received=datetime(2026,11,1,18,40,tzinfo=JST)
        self.assertEqual(classify(row,received,margin_minutes=12),"unknown_time")
        row["取得日時"]="2026-11-01T18:30:00+09:00"
        self.assertEqual(classify(row,received,margin_minutes=12),"pre_cutoff_observed")
        yesterday=datetime(2026,10,31,18,40,tzinfo=JST)
        self.assertEqual(classify(row,yesterday,margin_minutes=12),"unknown_time")

    def test_deadline_date_must_match_race_code(self):
        row={"レースコード":"202611010101","締切時刻":"2026-10-31 19:00:00",
             "取得日時":"2026-10-31T18:30:00+09:00"}
        received=datetime(2026,10,31,18,40,tzinfo=JST)
        self.assertEqual(classify(row,received,margin_minutes=12),"unknown_time")
        row["締切時刻"]="2026-11-01 19:00:00"
        row["取得日時"]="2026-11-01T18:30:00+09:00"
        received=datetime(2026,11,1,18,40,tzinfo=JST)
        self.assertEqual(classify(row,received,margin_minutes=12),"pre_cutoff_observed")

    def test_t12_cutoff_boundary_rejects_source_or_receipt_at_cutoff(self):
        row={"レースコード":"202611010101","締切時刻":"2026-11-01 19:00:00",
             "取得日時":"2026-11-01T18:47:59+09:00"}
        received=datetime(2026,11,1,18,47,59,tzinfo=JST)
        self.assertEqual(classify(row,received,margin_minutes=12),"pre_cutoff_observed")
        received=datetime(2026,11,1,18,48,0,tzinfo=JST)
        self.assertEqual(classify(row,received,margin_minutes=12),"too_late")
        row["取得日時"]="2026-11-01T18:48:00+09:00"
        self.assertEqual(classify(row,received,margin_minutes=12),"too_late")

if __name__=="__main__":unittest.main()

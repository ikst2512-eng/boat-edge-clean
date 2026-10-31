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
        self.assertEqual(classify(row,datetime(2026,10,31,17,40,tzinfo=JST)),"too_late")
        row.update({"レースコード":"202610310101","締切時刻":"18:00","取得日時":"2026-10-31T17:40:00+09:00"})
        self.assertEqual(classify(row,datetime(2026,10,31,17,45,tzinfo=JST)),"pre_cutoff_observed")
        row.pop("取得日時")
        self.assertEqual(classify(row,datetime(2026,10,31,17,40,tzinfo=JST)),"unknown_time")
if __name__=="__main__":unittest.main()

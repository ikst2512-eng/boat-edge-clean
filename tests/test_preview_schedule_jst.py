"""Regression test for early JST preview collection across UTC midnight."""
import unittest
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo
import re

ROOT=Path(__file__).resolve().parents[1]
JST=ZoneInfo("Asia/Tokyo")

class ScheduleJstTest(unittest.TestCase):
    def test_start_end_and_midnight_boundaries(self):
        workflow=(ROOT/".github/workflows/late-preview-capture.yml").read_text()
        expressions=re.findall(r"cron:\s*['\"]([^'\"]+)['\"]",workflow)
        self.assertIn("3-58/5 23,0-12 * * *",expressions)
        hours={23,*range(0,13)}
        minutes=set(range(3,59,5))
        jst_times={(datetime(2026,11,1,h,m,tzinfo=timezone.utc).astimezone(JST).hour,
                    datetime(2026,11,1,h,m,tzinfo=timezone.utc).astimezone(JST).minute)
                   for h in hours for m in minutes}
        self.assertNotIn((7,3),jst_times)
        self.assertIn((8,58),jst_times)
        self.assertIn((9,3),jst_times)
        self.assertIn((21,58),jst_times)
        self.assertNotIn((6,58),jst_times)
        self.assertNotIn((22,3),jst_times)
        self.assertEqual(len(jst_times),14*12)
    def test_capture_day_is_jst_not_utc(self):
        from collect_late_preview_once import collect
        seen=[]
        # 22:03Z on Oct 31 is 07:03 JST on Nov 1
        def clock():
            return datetime(2026,11,1,7,3,tzinfo=JST)
        def fetch(url):
            seen.append(url)
            raise ValueError("no upstream fixture")
        result=collect(fetch=fetch,clock=clock)
        self.assertEqual(result["date"],"20261101")
        self.assertTrue(all("/2026/11/01.csv" in url for url in seen))
        self.assertEqual(len(seen),5)

if __name__=="__main__":unittest.main()

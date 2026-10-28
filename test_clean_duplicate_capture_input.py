"""Capture may not silently choose a forecast input from duplicate upstream race rows."""
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from clean_four_mode_capture import collect
from research_model import JST

class DuplicateCaptureInputTests(unittest.TestCase):
    def test_duplicate_race_card_is_excluded(self):
        now=datetime(2026,10,28,8,0,tzinfo=JST)
        fetched=datetime(2026,10,28,7,30,tzinfo=JST)
        code="202610280101"
        title={"レースコード":code,"電話投票締切予定":"12:00"}
        good={"レースコード":code,**{f"艇{i}_全国勝率":str(4+i/10) for i in range(1,7)}}
        conflicting={**good,"艇1_全国勝率":"9.9"}
        def read(url):
            return ([title] if "/title/" in url else [good,conflicting],fetched,"a"*64)
        with tempfile.TemporaryDirectory() as temp:
            output=collect(root=Path(temp),now=now,read=read)
            self.assertEqual(output["new_saved"],[])
            self.assertEqual(output["excluded"].get("missing_race_card"),1)
            self.assertFalse((Path(temp)/"four_mode_forecasts"/(code+".json")).exists())

    def test_single_row_still_freezes(self):
        now=datetime(2026,10,28,8,0,tzinfo=JST)
        fetched=datetime(2026,10,28,7,30,tzinfo=JST)
        code="202610280101"
        title={"レースコード":code,"電話投票締切予定":"12:00"}
        card={"レースコード":code,**{f"艇{i}_全国勝率":str(4+i/10) for i in range(1,7)}}
        def read(url):
            return ([title] if "/title/" in url else [card],fetched,"a"*64)
        with tempfile.TemporaryDirectory() as temp:
            self.assertEqual(collect(root=Path(temp),now=now,read=read)["new_saved"],[code])

if __name__=="__main__": unittest.main()

"""Scheduled selector must never select races inside predeadline safety margin."""
import unittest
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from research_model import JST
from scripts.select_upcoming_research_race import choose

class SelectionContract(unittest.TestCase):
    def test_only_safe_upcoming_unsaved_race(self):
        now = datetime(2026,10,31,11,15,tzinfo=JST)
        date = "20261031"
        rows = [{"レースコード":date+"0101","電話投票締切予定":"11:35"},
                {"レースコード":date+"0102","電話投票締切予定":"12:40"},
                {"レースコード":date+"0103","電話投票締切予定":"13:10"}]
        with TemporaryDirectory() as temp:
            with patch("scripts.select_upcoming_research_race.read_rows",return_value=(rows,now,"hash")):
                self.assertEqual(choose(now,Path(temp)),(date,1,2))
                target=Path(temp)/"research_snapshots"
                target.mkdir()
                (target/(date+"0102.json")).write_text("{}")
                self.assertEqual(choose(now,Path(temp)),(date,1,3))

if __name__=="__main__":
    unittest.main()

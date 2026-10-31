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
        cards = []
        for row in rows:
            card = {"レースコード": row["レースコード"]}
            card.update({f"艇{i}_全国勝率": "6.0" for i in range(1, 7)})
            cards.append(card)
        with TemporaryDirectory() as temp:
            with patch("scripts.select_upcoming_research_race.read_rows",side_effect=[
                (rows,now,"title"),(cards,now,"cards"),
                (rows,now,"title"),(cards,now,"cards")
            ]):
                diagnostics = {}
                self.assertEqual(choose(now,Path(temp),diagnostics),(date,1,2))
                self.assertEqual(diagnostics["eligible"],2)
                self.assertEqual(diagnostics["too_close"],1)
                target=Path(temp)/"research_snapshots"
                target.mkdir()
                (target/(date+"0102.json")).write_text("{}")
                self.assertEqual(choose(now,Path(temp)),(date,1,3))

    def test_missing_primary_csv_uses_pre_race_alternate(self):
        now = datetime(2026,10,31,11,15,tzinfo=JST)
        day = "20261031"
        rows = [{"レースコード":day+"0104","電話投票締切予定":"13:10"}]
        cards = [{"レースコード":day+"0104",**{f"艇{i}_全国勝率":"6.0" for i in range(1,7)}}]
        from urllib.error import HTTPError
        with TemporaryDirectory() as temp, patch(
            "scripts.select_upcoming_research_race.read_rows",
            side_effect=HTTPError("primary",404,"Not Found",None,None)
        ), patch("clean_openapi_sources.load",return_value=(rows,cards,now,"digest",{})):
            stats = {}
            self.assertEqual(choose(now,Path(temp),stats),(day,1,4))
            self.assertEqual(stats["source"],"nonofficial_openapi_v1")

if __name__=="__main__":
    unittest.main()

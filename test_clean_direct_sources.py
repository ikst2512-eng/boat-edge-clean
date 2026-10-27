import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError
from clean_direct_sources import holding_rows,parse_card,direct_cards
from clean_four_mode_capture import collect
from research_model import JST


DAY="20261028"
NOW=datetime(2026,10,28,8,0,tzinfo=JST)
def holding_bytes():
    return json.dumps({"res_cd":0,"return_info":[{
        "RaceStudiumNo":"01","RaceTitleAll":["予選"],
        "DeadlineTimeAll":["15:50"],"CancelStatusAll":[""]}]}).encode()
def card_bytes():
    entries=[]
    for i in range(6):
        cols=[""]*25
        cols[0]=str(4101+i);cols[1]="選手";cols[5]="A1";cols[9]="0.15"
        cols[10]=str(5.5+i/10);cols[11]="40";cols[12]="60"
        cols[13]="5.0";cols[14]="35";cols[15]="50"
        cols[17]="12";cols[18]="30";cols[19]="45"
        cols[21]="15";cols[22]="28";cols[23]="42"
        entries.append("\t".join(cols))
    return ("data=\n1\t6\n"+"\n".join(entries)).encode()

class DirectSourceTests(unittest.TestCase):
    def test_direct_holding_and_card(self):
        holding,received,digest=holding_rows(DAY,fetch=lambda _:holding_bytes())
        self.assertEqual(holding[0]["レースコード"],DAY+"0101")
        self.assertEqual(holding[0]["電話投票締切予定"],"15:50")
        rows,_,_,hashes,failures=direct_cards(DAY,holding,now=NOW,fetch=lambda _:card_bytes())
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]["艇6_登録番号"],"4106")
        self.assertIn(DAY+"0101",hashes)
        self.assertEqual(failures,{})
    def test_no_result_backfill_after_cutoff(self):
        titles=[{"レースコード":DAY+"0101","電話投票締切予定":"08:05"}]
        called=[]
        cards,*_=direct_cards(DAY,titles,now=NOW,fetch=lambda url:called.append(url))
        self.assertEqual(cards,[])
        self.assertEqual(called,[])
    def test_daily_csv_404_falls_back_to_real_upstream_bytes(self):
        def missing(url):
            raise HTTPError(url,404,"Not Found",None,None)
        with tempfile.TemporaryDirectory() as temp:
            with patch("clean_direct_sources.holding_rows",side_effect=lambda day:holding_rows(day,fetch=lambda _:holding_bytes())),patch("clean_direct_sources.direct_cards",side_effect=lambda day,titles,existing,now=None:direct_cards(day,titles,existing,now=now,fetch=lambda _:card_bytes())):
                result=collect(root=Path(temp),now=NOW,read=missing)
            self.assertEqual(result["new_saved"],[DAY+"0101"])
            snapshot=json.loads((Path(temp)/"four_mode_forecasts"/(DAY+"0101.json")).read_text())
            self.assertEqual(set(snapshot["modes"]),{"hit","balance","hole","narrow"})
            self.assertTrue(snapshot["target_rates_not_proven"])
    def test_bad_card_rejected(self):
        with self.assertRaises(ValueError):parse_card(b"data=\n2\t6\n","202610280101")
if __name__=="__main__":unittest.main()

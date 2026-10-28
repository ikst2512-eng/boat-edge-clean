import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError
from clean_openapi_sources import load
from clean_four_mode_capture import collect
from research_model import JST

DAY="20261029"
NOW=datetime(2026,10,29,6,35,tzinfo=JST)
def raw(duplicate=False):
    racers={str(i):{"number":4100+i,"entry_number":i,"national_win_rate":4+i/10} for i in range(1,7)}
    if duplicate:racers["6"]["number"]=4101
    return json.dumps({"programs":{"stadiums":{"1":{"races":{"1":{"date":"2026-10-29","closed_at":"2026-10-29 11:00:00","racers":racers}}}}}}).encode()

class AlternatePreraceTests(unittest.TestCase):
    def test_valid_one_race(self):
        titles,cards,received,digest,meta=load(DAY,fetch=lambda _:raw(),now=NOW)
        self.assertEqual(len(titles),1)
        self.assertEqual(cards[0]["艇6_全国勝率"],"4.6")
        self.assertEqual(received,NOW)
        self.assertEqual(meta["valid"],1)
    def test_duplicate_racer_fail_closed(self):
        with self.assertRaisesRegex(ValueError,"no_valid_races"):
            load(DAY,fetch=lambda _:raw(True),now=NOW)
    def test_404_primary_and_403_direct_uses_verified_secondary(self):
        def missing(url):raise HTTPError(url,404,"Not Found",None,None)
        def denied(day):raise HTTPError("https://race.boatcast.jp/test",403,"Forbidden",None,None)
        def alternative(day,now=None):return load(day,fetch=lambda _:raw(),now=now)
        with tempfile.TemporaryDirectory() as tmp:
            with patch("clean_direct_sources.holding_rows",side_effect=denied),patch("clean_openapi_sources.load",side_effect=alternative):
                result=collect(root=Path(tmp),now=NOW,read=missing)
            self.assertEqual(result["new_saved"],[DAY+"0101"])
            self.assertEqual(result["source_probes"]["openapi_direct"]["status"],"available")
            record=json.loads((Path(tmp)/"four_mode_forecasts"/(DAY+"0101.json")).read_text())
            self.assertEqual(record["input_national_win_rates"],[4.1,4.2,4.3,4.4,4.5,4.6])
            self.assertTrue(record["target_rates_not_proven"])
            self.assertFalse(record["validated"])
    def test_alt_after_deadline_never_saved(self):
        def missing(url):raise HTTPError(url,404,"Not Found",None,None)
        def alternative(day,now=None):return load(day,fetch=lambda _:raw(),now=now)
        late=datetime(2026,10,29,10,45,tzinfo=JST)
        with tempfile.TemporaryDirectory() as tmp:
            with patch("clean_direct_sources.holding_rows",side_effect=lambda _:(_ for _ in ()).throw(ValueError("unavailable"))),patch("clean_openapi_sources.load",side_effect=alternative):
                out=collect(root=Path(tmp),now=late,read=missing)
            self.assertEqual(out["new_saved"],[])
if __name__=="__main__":unittest.main()

"""Exercise one independent six-boat input through a frozen forecast and verified-result report.

All sources, first-add proof and payout are test doubles: this is NOT a real historical win.
"""
import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from clean_direct_sources import parse_card
from clean_four_mode_capture import collect
from collect_four_mode_performance import run
from research_model import JST

class SourceToVerifiedReportTests(unittest.TestCase):
    def test_six_boat_source_freeze_then_confirmed_result(self):
        code="202610280101"
        now=datetime(2026,10,28,8,0,tzinfo=JST)
        fetched=datetime(2026,10,28,7,30,tzinfo=JST)
        lines=[]
        for i in range(6):
            c=[""]*25
            c[0]=str(4101+i)
            c[1]="選手"
            c[5]="A1"
            c[9]="0.15"
            c[10]=str(4.5+i/10)
            c[11]="40";c[12]="60";c[13]="5.0";c[14]="35";c[15]="50"
            c[17]="12";c[18]="30";c[19]="45";c[21]="15";c[22]="28";c[23]="42"
            lines.append("\t".join(c))
        raw=("data=\n1\t6\n"+"\n".join(lines)).encode()
        card=parse_card(raw,code)
        title={"レースコード":code,"電話投票締切予定":"12:00"}
        def read(url):
            return ([title] if "/title/" in url else [card],fetched,"a"*64)
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            captured=collect(root=root,now=now,read=read)
            self.assertEqual(captured["new_saved"],[code])
            file=root/"four_mode_forecasts"/(code+".json")
            original=file.read_bytes()
            archive=json.loads(original)
            self.assertEqual(archive["input_national_win_rates"],[4.5,4.6,4.7,4.8,4.9,5.0])
            self.assertEqual(set(archive["modes"]),{"hit","balance","hole","narrow"})
            self.assertEqual(collect(root=root,now=now,read=read)["new_saved"],[])
            self.assertEqual(file.read_bytes(),original)
            missing=run(root,5000,lambda *_:2400,lambda *_:"fixture-first-add",datetime(2026,10,28,13,0,tzinfo=JST))
            self.assertEqual(missing["counts"]["complete"],0)
            self.assertEqual(missing["counts"]["overdue_result"],1)
            winner=archive["modes"]["hit"]["tickets"][0]["combo"]
            result={"race_code":code,"status":"confirmed","finish_order":list(map(int,winner.split("-"))),
                    "source_url":"https://example.org/fixture-only",
                    "confirmed_at_jst":"2026-10-28T12:20:00+09:00"}
            (root/"confirmed_results").mkdir()
            (root/"confirmed_results"/(code+".json")).write_text(json.dumps(result))
            verified=run(root,5000,lambda *_:2400,lambda *_:"fixture-first-add",datetime(2026,10,28,13,0,tzinfo=JST))
            self.assertEqual(verified["counts"]["complete"],1)
            self.assertEqual(verified["modes"]["hit"]["hits"],1)
            self.assertEqual(verified["modes"]["hit"]["sample_races"],1)
            self.assertEqual(file.read_bytes(),original)
            detail=json.loads((root/"four_mode_performance"/"verified_races"/(code+".json")).read_text())
            self.assertTrue(detail["simulated_only"])
            self.assertEqual(detail["first_git_sha"],"fixture-first-add")
            self.assertEqual(detail["official_finish"],winner)

if __name__=="__main__":
    unittest.main()

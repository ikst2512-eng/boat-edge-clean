import json
import tempfile
import unittest
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1] / 'scripts'))
from scripts.collect_live_preview_evidence import paired_six_lane_coverage


class PairedPreviewCoverageTests(unittest.TestCase):
    def test_live_summary_reports_complete_vs_incomplete(self):
        import csv, io
        from datetime import datetime
        from research_model import JST
        from scripts.collect_live_preview_evidence import collect
        day="20261031"
        code="202610312311"
        fields=["レースコード","締切時刻","取得日時"]
        row={"レースコード":code,"締切時刻":"20:00",
             "取得日時":"2026-10-31T19:54:00+09:00"}
        def fetch(url):
            kind=url.split("/")[-4]
            current=dict(row)
            cols=list(fields)
            if kind=="tkz":
                for lane in range(1,7):
                    current[f"艇{lane}_展示タイム"]="6.7"
                    current[f"艇{lane}_チルト"]="0"
                    cols.extend((f"艇{lane}_展示タイム",f"艇{lane}_チルト"))
            elif kind=="stt":
                for lane in range(1,7):
                    current[f"艇{lane}_コース"]=str(lane)
                    current[f"艇{lane}_スタート展示"]="0.12"
                    cols.extend((f"艇{lane}_コース",f"艇{lane}_スタート展示"))
                current["艇6_スタート展示"]=""
            writer_buffer=io.StringIO()
            writer=csv.DictWriter(writer_buffer,fieldnames=cols)
            writer.writeheader()
            writer.writerow(current)
            return writer_buffer.getvalue().encode(),datetime(2026,10,31,19,55,tzinfo=JST)
        with tempfile.TemporaryDirectory() as tmp:
            result=collect(day,Path(tmp),fetch=fetch)
        self.assertEqual(result["kinds"]["tkz"]["six_lane_complete"],1)
        self.assertEqual(result["kinds"]["stt"]["six_lane_incomplete"],1)
        self.assertEqual(result["paired_six_lane_coverage"]["paired_complete"],0)

    def test_only_same_race_complete_pairs_count(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            day="20261031"
            for kind, entries in {"tkz":[("202610310101","complete"),("202610310102","complete")],
                                  "stt":[("202610310101","complete"),("202610310102","incomplete"),
                                         ("202610310103","complete")]}.items():
                folder=root/day/kind
                folder.mkdir(parents=True)
                for code,status in entries:
                    if kind=="tkz":
                        row={**{f"艇{i}_展示タイム":"6.75" for i in range(1,7)},
                             **{f"艇{i}_チルト":"0" for i in range(1,7)}}
                    else:
                        row={**{f"艇{i}_コース":str(i) for i in range(1,7)},
                             **{f"艇{i}_スタート展示":"0.12" for i in range(1,7)}}
                    (folder/(code+".json")).write_text(json.dumps({
                        "race_code":code,"kind":kind,"six_lane_validation":status,
                        "received_at_jst":"2026-10-31T19:55:00+09:00",
                        "source_observed_jst":"2026-10-31T19:54:00+09:00",
                        "source_row":dict(row, **{"レースコード":code,"締切時刻":"20:00","取得日時":"2026-10-31T19:54:00+09:00"}),
                        "status":"late_preview_unvalidated_not_research_forecast"}))
            result=paired_six_lane_coverage(day,root)
            self.assertEqual(result["tkz_complete"],2)
            self.assertEqual(result["stt_complete"],2)
            self.assertEqual(result["paired_complete"],1)
            self.assertEqual(result["paired_codes"],["202610310101"])
            # A stored "complete" label is not enough if the source row is corrupt.
            corrupt=root/day/"tkz"/"202610310101.json"
            record=json.loads(corrupt.read_text())
            record["source_row"]["艇6_展示タイム"]=""
            corrupt.write_text(json.dumps(record))
            rejected=paired_six_lane_coverage(day,root)
            self.assertEqual(rejected["paired_complete"],0)
            self.assertEqual(rejected["tkz_complete"],1)
            record["source_row"]["艇6_展示タイム"]="6.75"
            record["received_at_jst"]="2026-10-31T20:01:00+09:00"
            corrupt.write_text(json.dumps(record))
            self.assertEqual(paired_six_lane_coverage(day,root)["paired_complete"],0)


if __name__=="__main__":
    unittest.main()

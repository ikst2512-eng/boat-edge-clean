import csv
import io
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from research_model import JST
from late_preview_capture import save_preview
from scripts.late_preview_feature_pairs import build


class LateFeaturesTests(unittest.TestCase):
    def test_real_pair_keeps_boat_identity_and_course(self):
        day="20261031"
        code="202610312311"
        with tempfile.TemporaryDirectory() as folder:
            for kind in ("tkz","stt"):
                row={"レースコード":code,"締切時刻":"20:00",
                     "取得日時":"2026-10-31T19:54:00+09:00"}
                if kind=="tkz":
                    for i in range(1,7):
                        row[f"艇{i}_展示タイム"]="6.75"
                        row[f"艇{i}_チルト"]="0"
                else:
                    for i in range(1,7):
                        row[f"艇{i}_コース"]=str(7-i)
                        row[f"艇{i}_スタート展示"]="0.12"
                stream=io.StringIO()
                writer=csv.DictWriter(stream,fieldnames=list(row))
                writer.writeheader()
                writer.writerow(row)
                save_preview(stream.getvalue().encode(),kind,day,
                             datetime(2026,10,31,19,55,tzinfo=JST),folder)
            self.assertEqual(build(day,folder,require_t12=True)["ready_count"],0)
            result=build(day,folder)
            self.assertEqual(result["ready_count"],1)
            self.assertEqual(result["records"][0]["boats"][0]["boat"],1)
            self.assertEqual(result["records"][0]["boats"][0]["entry_course"],6)
            self.assertEqual(result["records"][0]["boats"][5]["entry_course"],1)
            self.assertEqual(result["records"][0]["status"],"verified_preview_features_not_prediction")
            self.assertEqual(result["records"][0]["both_sources_received_at_jst"],
                             "2026-10-31T19:55:00+09:00")


if __name__=="__main__":
    unittest.main()

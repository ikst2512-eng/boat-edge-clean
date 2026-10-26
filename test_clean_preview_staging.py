import unittest
from clean_preview_staging import stage_preview

CODE = "202610271201"
BASE = "https://boatracecsv.github.io/data/previews/"
HEAD = ["レースコード","レース日","レース場","レース回","締切時刻","取得日時"]
VALUES = [CODE,"2026-10-27","12","01R","15:20","2026-10-27T15:14:00+09:00"]

def fixture(kind):
    fields = (["コース","スタート展示"] if kind == "stt" else
              ["展示タイム","チルト"] if kind == "tkz" else
              ["風速(m)","風向","波の高さ(cm)","天候","気温(℃)","水温(℃)"])
    columns = HEAD + ([f"艇{i}_{f}" for i in range(1,7) for f in fields] if kind != "sui" else fields)
    tail = ([v for i in range(1,7) for v in ([str(i),".12"] if kind=="stt" else ["6.81","-0.5"])]
            if kind != "sui" else ["2","北","3","晴","23","20"])
    return ",".join(columns)+"\n"+",".join(VALUES+tail)+"\n"

def source(kind):
    return BASE+kind+"/2026/10/27.csv"

class PreviewStagingTest(unittest.TestCase):
    def test_all_preview_kinds_are_staged_not_published(self):
        for kind in ("stt","tkz","sui"):
            with self.subTest(kind=kind):
                result=stage_preview(fixture(kind),CODE,kind,source(kind))
                self.assertEqual(result["status"],"staged_unpublished")
                self.assertEqual(result["source_kind"],"third_party_csv_unverified")
    def test_duplicate_entry_is_rejected(self):
        with self.assertRaises(ValueError):
            stage_preview(fixture("stt").replace(",6,.12",",1,.12"),CODE,"stt",source("stt"))
    def test_other_race_is_rejected(self):
        with self.assertRaises(ValueError):
            stage_preview(fixture("stt").replace("01R","02R"),CODE,"stt",source("stt"))
    def test_missing_lane_field_is_rejected(self):
        with self.assertRaises(ValueError):
            stage_preview(fixture("tkz").replace("艇6_チルト","missing"),CODE,"tkz",source("tkz"))
    def test_timestamp_without_timezone_is_rejected(self):
        with self.assertRaises(ValueError):
            stage_preview(fixture("sui").replace("+09:00",""),CODE,"sui",source("sui"))
    def test_duplicate_race_row_is_rejected(self):
        x=fixture("stt")
        with self.assertRaises(ValueError):
            stage_preview(x+x.splitlines()[1]+"\n",CODE,"stt",source("stt"))

if __name__=="__main__":
    unittest.main()

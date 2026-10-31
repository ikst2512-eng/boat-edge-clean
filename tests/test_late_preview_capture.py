"""No retroactive write, no overwrite, no mixing with earlier research snapshots."""
import csv, io, json, tempfile, unittest
from datetime import datetime
from pathlib import Path
from research_model import JST
from late_preview_capture import save_preview, six_lane_status

def csv_bytes(rows):
    output=io.StringIO()
    writer=csv.DictWriter(output,fieldnames=["レースコード","締切時刻","取得日時","艇1_コース"])
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue().encode()

class LatePreviewCaptureTest(unittest.TestCase):
    def test_before_deadline_appends_in_isolated_directory_only(self):
        rows=[{"レースコード":"202610312311","締切時刻":"20:00",
               "取得日時":"2026-10-31T19:54:00+09:00","艇1_コース":"2"}]
        when=datetime(2026,10,31,19,55,tzinfo=JST)
        with tempfile.TemporaryDirectory() as root:
            saved=save_preview(csv_bytes(rows),"stt","20261031",when,root)
            self.assertEqual(saved,["202610312311"])
            path=Path(root)/"20261031"/"stt"/"202610312311.json"
            record=json.loads(path.read_text())
            self.assertEqual(record["source_row"]["艇1_コース"],"2")
            self.assertFalse((Path(root)/"research_snapshots").exists())
            original=path.read_bytes()
            with self.assertRaises(FileExistsError):
                save_preview(csv_bytes(rows),"stt","20261031",when,root)
            self.assertEqual(path.read_bytes(),original)

    def test_existing_later_race_rejects_whole_batch_without_partial_write(self):
        # If race B already exists, race A must not be written before the failure.
        first={"レースコード":"202610312310","締切時刻":"20:00",
               "取得日時":"2026-10-31T19:54:00+09:00","艇1_コース":"1"}
        second={"レースコード":"202610312311","締切時刻":"20:00",
                "取得日時":"2026-10-31T19:54:00+09:00","艇1_コース":"2"}
        receipt=datetime(2026,10,31,19,55,tzinfo=JST)
        with tempfile.TemporaryDirectory() as root:
            save_preview(csv_bytes([second]),"stt","20261031",receipt,root)
            existing=Path(root)/"20261031"/"stt"/"202610312311.json"
            unchanged=existing.read_bytes()
            with self.assertRaises(FileExistsError):
                save_preview(csv_bytes([first,second]),"stt","20261031",receipt,root)
            self.assertFalse((Path(root)/"20261031"/"stt"/"202610312310.json").exists())
            self.assertEqual(existing.read_bytes(),unchanged)

    def test_noncolliding_batch_saves_every_eligible_race(self):
        rows=[{"レースコード":f"2026103123{race:02d}","締切時刻":"20:00",
               "取得日時":"2026-10-31T19:54:00+09:00","艇1_コース":"1"}
              for race in (10,11)]
        with tempfile.TemporaryDirectory() as root:
            result=save_preview(csv_bytes(rows),"stt","20261031",
                                datetime(2026,10,31,19,55,tzinfo=JST),root)
            self.assertEqual(result,["202610312310","202610312311"])
            self.assertEqual(len(list(Path(root).rglob("*.json"))),2)

    def test_source_one_minute_before_deadline_is_rejected(self):
        row={"レースコード":"202610312311","締切時刻":"20:00",
             "取得日時":"2026-10-31T19:59:00+09:00","艇1_コース":"1"}
        with tempfile.TemporaryDirectory() as root:
            receipt=datetime(2026,10,31,19,57,tzinfo=JST)
            self.assertEqual(save_preview(csv_bytes([row]),"stt","20261031",receipt,root),[])
            self.assertEqual(list(Path(root).rglob("*.json")),[])

    def test_six_lane_exhibition_completeness_is_explicit(self):
        tkz={f"艇{i}_{key}": str(value) for i in range(1,7)
             for key,value in (("展示タイム",6.7),("チルト",0))}
        self.assertEqual(six_lane_status("tkz",tkz),"complete")
        tkz["艇6_展示タイム"]=""
        self.assertEqual(six_lane_status("tkz",tkz),"incomplete")
        stt={f"艇{i}_コース":str(i) for i in range(1,7)}
        stt.update({f"艇{i}_スタート展示":"0.12" for i in range(1,7)})
        self.assertEqual(six_lane_status("stt",stt),"complete")
        stt["艇6_コース"]="1"
        self.assertEqual(six_lane_status("stt",stt),"incomplete")
        self.assertEqual(six_lane_status("sui",{}),"not_applicable")

    def test_late_receipt_and_missing_source_time_never_saved(self):
        row={"レースコード":"202610312311","締切時刻":"20:00",
             "取得日時":"2026-10-31T19:54:00+09:00","艇1_コース":"1"}
        with tempfile.TemporaryDirectory() as root:
            self.assertEqual(save_preview(csv_bytes([row]),"stt","20261031",datetime(2026,10,31,19,59,tzinfo=JST),root),[])
            row["取得日時"]=""
            self.assertEqual(save_preview(csv_bytes([row]),"stt","20261031",datetime(2026,10,31,19,55,tzinfo=JST),root),[])

if __name__=="__main__":unittest.main()

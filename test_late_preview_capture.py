import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from late_preview_capture import save_preview
from research_model import JST


def csv_row(received="2026-10-31 11:00:00", deadline="11:20"):
    return ("レースコード,締切時刻,取得日時,展示タイム\n"
            f"202610310101,{deadline},{received},6.65\n").encode()


class LatePreviewEvidenceTests(unittest.TestCase):
    def test_ragged_csv_rows_fail_without_archiving(self):
        with tempfile.TemporaryDirectory() as directory:
            receipt=datetime(2026,10,31,11,2,tzinfo=JST)
            header="レースコード,締切時刻,取得日時,艇1_展示タイム"
            for values in (
                "202610310101,11:20,2026-10-31 11:00:00",
                "202610310101,11:20,2026-10-31 11:00:00,6.65,6.99",
            ):
                with self.subTest(values=values):
                    raw=(header+"\n"+values+"\n").encode()
                    with self.assertRaisesRegex(ValueError,"ragged preview CSV row"):
                        save_preview(raw,"tkz","20261031",receipt,directory)
            self.assertFalse(list(Path(directory).rglob("*.json")))

    def test_duplicate_csv_headers_fail_before_any_evidence_write(self):
        with tempfile.TemporaryDirectory() as directory:
            receipt=datetime(2026,10,31,11,2,tzinfo=JST)
            raw=("レースコード,締切時刻,取得日時,艇1_展示タイム,艇1_展示タイム\n"
                 "202610310101,11:20,2026-10-31 11:00:00,6.50,6.90\n").encode()
            with self.assertRaisesRegex(ValueError,"duplicate preview CSV headers"):
                save_preview(raw,"tkz","20261031",receipt,directory)
            self.assertFalse(list(Path(directory).rglob("*.json")))

    def test_six_lane_st_requires_plausible_start_values(self):
        from late_preview_capture import six_lane_status
        row={f"艇{i}_コース":str(i) for i in range(1,7)}
        row.update({f"艇{i}_スタート展示":"0.12" for i in range(1,7)})
        self.assertEqual(six_lane_status("stt",row),"complete")
        for invalid in ("999","-2.0","1.50","NaN","inf","F1.00","ST"):
            with self.subTest(invalid=invalid):
                row["艇6_スタート展示"]=invalid
                self.assertEqual(six_lane_status("stt",row),"incomplete")
        row["艇6_スタート展示"]="F.02"
        self.assertEqual(six_lane_status("stt",row),"complete")

    def test_predeadline_append_only_receipt_and_hash(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            receipt = datetime(2026, 10, 31, 11, 2, tzinfo=JST)
            raw = csv_row()
            saved = save_preview(raw, "tkz", "20261031", receipt, root)
            self.assertEqual(saved, ["202610310101"])
            path = root / "20261031/tkz/202610310101.json"
            record = json.loads(path.read_text())
            self.assertEqual(record["status"], "late_preview_unvalidated_not_research_forecast")
            self.assertEqual(record["race_code"], "202610310101")
            self.assertEqual(record["received_at_jst"], receipt.isoformat())
            self.assertEqual(record["cutoff_policy"], "before_deadline_minus_2min_buffer")
            self.assertEqual(len(record["source_csv_sha256"]), 64)
            with self.assertRaises(FileExistsError):
                save_preview(raw, "tkz", "20261031", receipt, root)
            self.assertEqual(json.loads(path.read_text()), record)

    def test_accepts_full_datetime_deadline_consistent_with_classifier(self):
        with tempfile.TemporaryDirectory() as directory:
            receipt=datetime(2026,10,31,11,2,tzinfo=JST)
            for deadline in ("2026-10-31 11:20:00", "2026-10-31T11:20:00+09:00"):
                with self.subTest(deadline=deadline):
                    root=Path(directory)/str(len(list(Path(directory).iterdir())))
                    saved=save_preview(csv_row(deadline=deadline),"tkz","20261031",receipt,root)
                    self.assertEqual(saved,["202610310101"])
                    self.assertTrue((root/"20261031/tkz/202610310101.json").exists())

    def test_rejects_late_receipt_and_future_source(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            late = datetime(2026, 10, 31, 11, 19, tzinfo=JST)
            early = datetime(2026, 10, 31, 11, 2, tzinfo=JST)
            self.assertEqual(save_preview(csv_row(), "tkz", "20261031", late, root), [])
            self.assertEqual(save_preview(csv_row(received="2026-10-31 11:03:00"), "tkz", "20261031", early, root), [])
            self.assertFalse(list(root.rglob("*.json")))

    def test_rejects_unsupported_dataset_or_unaware_receipt(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                save_preview(csv_row(), "unknown", "20261031", datetime(2026, 10, 31, 11, 2, tzinfo=JST), directory)
            with self.assertRaises(ValueError):
                save_preview(csv_row(), "tkz", "20261031", datetime(2026, 10, 31, 11, 2), directory)


if __name__ == "__main__":
    unittest.main()

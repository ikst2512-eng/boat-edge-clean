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

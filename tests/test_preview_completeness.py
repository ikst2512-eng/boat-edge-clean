"""Source-completeness checks for independently timestamped preview CSV."""
from datetime import datetime
from unittest import TestCase
from unittest.mock import patch

from clean_racecard import _fetch_preview


class PreviewCompletenessTests(TestCase):
    def test_blank_st_does_not_become_verified_preview(self):
        code = "202610300301"
        deadline = datetime.fromisoformat("2026-10-30T15:00:00+09:00")
        shared = {"レースコード": code, "締切時刻": "15:00",
                  "取得日時": "2026-10-30T14:50:00+09:00"}
        tkz = dict(shared)
        stt = dict(shared)
        for lane in range(1, 7):
            tkz[f"艇{lane}_展示タイム"] = "6.70"
            tkz[f"艇{lane}_チルト"] = "0.0"
            stt[f"艇{lane}_コース"] = str(lane)
            stt[f"艇{lane}_スタート展示"] = "0.12" if lane != 4 else ""
        rows = {"tkz": [tkz], "stt": [stt], "sui": []}
        def fake_rows(kind, path):
            return rows[kind], "a" * 64
        with patch("clean_racecard._preview_rows", side_effect=fake_rows):
            preview, audit = _fetch_preview(code, "2026/10/30.csv", deadline)
            self.assertIsNone(preview)
            self.assertEqual(audit["status"], "invalid_or_incomplete_exhibition")
            stt["艇4_スタート展示"] = "INVALID"
            preview, audit = _fetch_preview(code, "2026/10/30.csv", deadline)
            self.assertIsNone(preview)
            self.assertEqual(audit["status"], "invalid_or_incomplete_exhibition")
            stt["艇4_スタート展示"] = "F.01"
            preview, audit = _fetch_preview(code, "2026/10/30.csv", deadline)
            self.assertEqual(audit["status"], "ok")
            self.assertEqual(len(preview["start_exhibition"]), 6)


if __name__ == "__main__":
    import unittest
    unittest.main()

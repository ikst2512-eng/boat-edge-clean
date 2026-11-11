"""Source-completeness checks for independently timestamped preview CSV."""
from datetime import datetime
from unittest import TestCase
from unittest.mock import patch

from clean_racecard import _fetch_preview, _race_read_only, racecard


class PreviewCompletenessTests(TestCase):
    def test_same_day_after_cutoff_is_read_only(self):
        cutoff = datetime.fromisoformat("2026-11-03T22:20:00+09:00")
        self.assertFalse(_race_read_only(cutoff, datetime.fromisoformat("2026-11-03T22:19:59+09:00")))
        self.assertTrue(_race_read_only(cutoff, datetime.fromisoformat("2026-11-03T22:20:00+09:00")))
        self.assertTrue(_race_read_only(cutoff, datetime.fromisoformat("2026-11-03T23:24:00+09:00")))
        self.assertTrue(_race_read_only(cutoff, datetime.fromisoformat("2026-11-04T10:00:00+09:00")))
        with self.assertRaises(ValueError):
            _race_read_only(cutoff, datetime(2026, 11, 3, 23, 24))

    def test_racecard_uses_cutoff_not_calendar_for_read_only(self):
        from pathlib import Path
        source=(Path(__file__).resolve().parents[1] / "clean_racecard.py").read_text()
        self.assertIn("historical=_race_read_only(deadline)", source)
        self.assertNotIn('historical=datetime.strptime(hd,"%Y%m%d").date()<', source)
        self.assertIn('"phase":"HISTORICAL_READ_ONLY" if historical else "PRE_RESULT"', source)

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
            preview, audit = _fetch_preview(code, "2026/10/30.csv", deadline,
                                              clock=lambda: datetime.fromisoformat("2026-10-30T14:55:00+09:00"))
            self.assertIsNone(preview)
            self.assertEqual(audit["status"], "invalid_or_incomplete_exhibition")
            stt["艇4_スタート展示"] = "INVALID"
            preview, audit = _fetch_preview(code, "2026/10/30.csv", deadline,
                                              clock=lambda: datetime.fromisoformat("2026-10-30T14:55:00+09:00"))
            self.assertIsNone(preview)
            self.assertEqual(audit["status"], "invalid_or_incomplete_exhibition")
            stt["艇4_スタート展示"] = "F.01"
            preview, audit = _fetch_preview(code, "2026/10/30.csv", deadline,
                                              clock=lambda: datetime.fromisoformat("2026-10-30T14:55:00+09:00"))
            self.assertEqual(audit["status"], "ok")
            self.assertEqual(audit["source_status"], {"tkz": "ok", "stt": "ok", "sui": "race_not_published"})
            self.assertEqual(len(preview["start_exhibition"]), 6)


    def test_newer_partial_snapshot_does_not_hide_valid_six_lanes(self):
        code = "202610300301"
        deadline = datetime.fromisoformat("2026-10-30T15:00:00+09:00")
        base = {"レースコード": code, "締切時刻": "15:00",
                "取得日時": "2026-10-30T14:48:00+09:00"}
        tkz = dict(base)
        stt = dict(base)
        for lane in range(1, 7):
            tkz[f"艇{lane}_展示タイム"] = "6.72"
            tkz[f"艇{lane}_チルト"] = "0.0"
            stt[f"艇{lane}_コース"] = str(lane)
            stt[f"艇{lane}_スタート展示"] = "0.13"
        partial_tkz = dict(tkz, **{"取得日時": "2026-10-30T14:51:00+09:00",
                                     "艇6_展示タイム": ""})
        partial_stt = dict(stt, **{"取得日時": "2026-10-30T14:52:00+09:00",
                                     "艇2_スタート展示": ""})
        rows = {"tkz": [tkz, partial_tkz], "stt": [stt, partial_stt], "sui": []}
        with patch("clean_racecard._preview_rows",
                   side_effect=lambda kind, path: (rows[kind], "b" * 64)):
            preview, audit = _fetch_preview(code, "2026/10/30.csv", deadline,
                                              clock=lambda: datetime.fromisoformat("2026-10-30T14:55:00+09:00"))
        self.assertEqual(audit["status"], "ok")
        self.assertEqual(len(preview["racers"]), 6)
        self.assertEqual(len(preview["start_exhibition"]), 6)
        self.assertEqual(preview["racers"][5]["exhibition_time"], 6.72)
        self.assertEqual(preview["start_exhibition"][1]["st"], ".13")
        self.assertEqual(audit["fetched_at"], "2026-10-30T14:48:00+09:00")


    def test_snapshot_published_during_source_fetch_is_accepted(self):
        code="202611041911"
        deadline=datetime.fromisoformat("2026-11-04T18:00:00+09:00")
        shared={"レースコード":code,"締切時刻":"18:00",
                "取得日時":"2026-11-04T17:30:30+09:00"}
        tkz=dict(shared)
        stt=dict(shared)
        for lane in range(1,7):
            tkz[f"艇{lane}_展示タイム"]="6.73"
            tkz[f"艇{lane}_チルト"]="0.0"
            stt[f"艇{lane}_コース"]=str(lane)
            stt[f"艇{lane}_スタート展示"]="0.12"
        rows={"tkz":[tkz],"stt":[stt],"sui":[]}
        # Older start-of-request clock 17:30 would falsely reject a valid
        # 17:30:30 row. HTTP actually returned the complete data at 17:31.
        receipt=datetime.fromisoformat("2026-11-04T17:31:00+09:00")
        with patch("clean_racecard._preview_rows",
                   side_effect=lambda kind,path:(rows[kind],"c"*64)):
            preview,audit=_fetch_preview(code,"2026/11/04.csv",deadline,
                                         clock=lambda:receipt)
        self.assertEqual(audit["status"],"ok")
        self.assertEqual(len(preview["racers"]),6)
        self.assertEqual(len(preview["start_exhibition"]),6)
        self.assertEqual(audit["sources"]["tkz"]["received_at_jst"],receipt.isoformat())
        self.assertEqual(audit["sources"]["stt"]["received_at_jst"],receipt.isoformat())

    def test_source_delivery_at_cutoff_cannot_certify_predeadline(self):
        code="202611041911"
        deadline=datetime.fromisoformat("2026-11-04T18:00:00+09:00")
        matching={"レースコード":code,"締切時刻":"18:00",
                  "取得日時":"2026-11-04T17:20:00+09:00"}
        with patch("clean_racecard._preview_rows",
                   side_effect=lambda kind,path:([matching],"c"*64)):
            preview,audit=_fetch_preview(code,"2026/11/04.csv",deadline,
                                         clock=lambda:deadline)
        self.assertIsNone(preview)
        self.assertEqual(audit["status"],"not_published_or_unavailable")
        self.assertEqual(audit["source_status"]["tkz"],"deadline_or_receipt_unverified")

    def test_source_timestamp_after_http_receipt_is_rejected(self):
        code="202611041911"
        deadline=datetime.fromisoformat("2026-11-04T18:00:00+09:00")
        future={"レースコード":code,"締切時刻":"18:00",
                "取得日時":"2026-11-04T17:31:01+09:00"}
        with patch("clean_racecard._preview_rows",
                   side_effect=lambda kind,path:([future],"c"*64)):
            preview,audit=_fetch_preview(code,"2026/11/04.csv",deadline,
                   clock=lambda:datetime.fromisoformat("2026-11-04T17:31:00+09:00"))
        self.assertIsNone(preview)
        self.assertEqual(audit["source_status"]["tkz"],"deadline_or_timestamp_unverified")


if __name__ == "__main__":
    import unittest
    unittest.main()

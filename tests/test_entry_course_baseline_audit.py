import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from entry_course_baseline_audit import audit_daily_bases
from entry_course_collector import attempt

JST=timezone(timedelta(hours=9))
NOW=datetime(2026,11,3,20,22,tzinfo=JST)
def snapshot(code, deadline):
    return {"race_code":code,"status":"research","validated":False,
            "generated_at":"2026-11-03T12:00:00+09:00",
            "cutoff_jst":(deadline-timedelta(minutes=12)).isoformat(),
            "source_deadline_jst":deadline.isoformat()}

class AuditTests(unittest.TestCase):
    def test_no_today_snapshots_detected_without_network(self):
        with tempfile.TemporaryDirectory() as tmp:
            result=attempt(tmp,now=lambda:NOW,prefetch=lambda d:self.fail("download"))
            self.assertEqual(result["baseline_audit"]["status"],"missing_current_day_research_snapshots")
            self.assertEqual(result["baseline_audit"]["counts"]["eligible"],0)
            self.assertFalse(result["baseline_audit"]["forecast_record"])
    def test_past_future_and_valid_candidates_are_distinguished(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)/"research_snapshots"
            folder.mkdir()
            cases=[
              ("202611030101",datetime(2026,11,3,19,0,tzinfo=JST)),
              ("202611030102",datetime(2026,11,3,21,0,tzinfo=JST)),
              ("202611030103",datetime(2026,11,3,20,29,tzinfo=JST)),
            ]
            for code,dt in cases:
                (folder/(code+".json")).write_text(json.dumps(snapshot(code,dt)))
            out=audit_daily_bases(tmp,now=NOW)
            self.assertEqual(out["counts"]["snapshot_files_today"],3)
            self.assertEqual(out["counts"]["valid_frozen_research"],3)
            self.assertEqual(out["counts"]["past_t2"],1)
            self.assertEqual(out["counts"]["outside_window"],1)
            self.assertEqual(out["counts"]["eligible"],1)
            self.assertEqual(out["race_code_samples"]["eligible"],["202611030103"])
    def test_invalid_json_not_marked_as_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)/"research_snapshots"
            folder.mkdir()
            (folder/"202611030101.json").write_text("{")
            out=audit_daily_bases(tmp,now=NOW)
            self.assertEqual(out["status"],"invalid_current_day_research_snapshots")
            self.assertEqual(out["counts"]["invalid_snapshot"],1)
    def test_stale_same_day_file_cannot_qualify(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)/"research_snapshots"
            folder.mkdir()
            code="202611030101"
            row=snapshot(code,datetime(2026,11,3,21,0,tzinfo=JST))
            row["generated_at"]="2026-11-03T20:55:00+09:00"
            (folder/(code+".json")).write_text(json.dumps(row))
            out=audit_daily_bases(tmp,now=NOW)
            self.assertEqual(out["counts"]["invalid_snapshot"],1)
    def test_naive_clock_rejected(self):
        with self.assertRaisesRegex(ValueError,"timezone"):
            audit_daily_bases(".",now=datetime(2026,11,3,20,22))
if __name__=="__main__":unittest.main()

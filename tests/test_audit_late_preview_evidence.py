import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from scripts.audit_late_preview_evidence import audit

def record(code,kind,valid="complete",received="2026-10-31T19:55:00+09:00"):
    source={"レースコード":code,"締切時刻":"20:00","取得日時":"2026-10-31T19:54:00+09:00"}
    for i in range(1,7):
        if kind=="stt":
            source[f"艇{i}_コース"]=str(i)
            source[f"艇{i}_スタート展示"]="0.12"
        else:
            source[f"艇{i}_展示タイム"]="6.72"
            source[f"艇{i}_チルト"]="0"
    return {"race_code":code,"kind":kind,"received_at_jst":received,
        "source_row":source,
        "six_lane_validation":valid,
        "source_observed_jst":source["取得日時"],
        "source_csv_sha256":"a"*64,
        "cutoff_policy":"before_deadline_minus_2min_buffer",
        "status":"late_preview_unvalidated_not_research_forecast"}

class AuditLatePreview(unittest.TestCase):
    def test_summary_metadata_does_not_count_as_invalid_race(self):
        with tempfile.TemporaryDirectory() as folder:
            day=Path(folder)/"20261031"
            day.mkdir()
            (day/"collection_summary.json").write_text('{"day":"20261031"}')
            (Path(folder)/"late_preview_audit_report.json").write_text('{"records":0}')
            result=audit(folder)
            self.assertEqual(result["records"],0)
            self.assertEqual(result["invalid"],0)
            self.assertEqual(result["races"],0)

    def test_duplicate_kind_never_counts_as_complete_pair(self):
        with tempfile.TemporaryDirectory() as folder:
            code="202610310111"
            paths=[]
            for kind in ("stt","tkz"):
                path=Path(folder)/"20261031"/kind/(code+".json")
                path.parent.mkdir(parents=True)
                obj=record(code,kind,received="2026-10-31T19:45:00+09:00")
                obj["source_row"]["取得日時"]="2026-10-31T19:44:00+09:00"
                obj["source_observed_jst"]=obj["source_row"]["取得日時"]
                path.write_text(json.dumps(obj))
                paths.append(path)
            # Simulate duplicated discovery or merged artifact references.
            with patch("scripts.audit_late_preview_evidence.Path.rglob",return_value=[paths[0],paths[1],paths[0]]):
                result=audit(folder)
            self.assertEqual(result["invalid"],1)
            self.assertEqual(result["paired_complete_6boat_stt_tkz"],0)
            self.assertEqual(result["paired_complete_12min_observable"],0)

    def test_complete_pair_and_too_late_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            code="202610310111"
            for kind in ("stt","tkz"):
                path=Path(folder)/"20261031"/kind/(code+".json")
                path.parent.mkdir(parents=True)
                path.write_text(json.dumps(record(code,kind)))
            result=audit(folder)
            self.assertEqual(result["paired_complete_6boat_stt_tkz"],1)
            self.assertEqual(result["invalid"],0)
            self.assertEqual(result["paired_complete_12min_observable"],0)
            self.assertEqual(len(result["paired_complete_but_not_t12"]),1)
            self.assertEqual(result["paired_complete_but_not_t12"][0]["race_code"],code)
            self.assertEqual(result["paired_complete_but_not_t12"][0]["stt_t12"],"too_late")
            for kind in ("stt","tkz"):
                early_path=Path(folder)/"20261031"/kind/(code+".json")
                early_record=record(code,kind,received="2026-10-31T19:45:00+09:00")
                early_record["source_row"]["取得日時"]="2026-10-31T19:44:00+09:00"
                early_record["source_observed_jst"]="2026-10-31T19:44:00+09:00"
                early_path.write_text(json.dumps(early_record))
            early_audit=audit(folder)
            self.assertEqual(early_audit["paired_complete_12min_observable"],1)
            self.assertEqual(early_audit["t12_observable_race_codes"],[code])
            self.assertEqual(early_audit["t12_evidence_by_race"][0]["stt_received_at_jst"],"2026-10-31T19:45:00+09:00")
            for kind in ("stt","tkz"):
                early_path=Path(folder)/"20261031"/kind/(code+".json")
                early_path.write_text(json.dumps(record(code,kind)))
            obj=json.loads(path.read_text())
            obj["source_row"]["艇6_展示タイム"]=""
            path.write_text(json.dumps(obj))
            self.assertEqual(audit(folder)["paired_complete_6boat_stt_tkz"],0)
            path.write_text(json.dumps(record(code,"tkz")))
            self.assertEqual(audit(folder)["paired_complete_6boat_stt_tkz"],1)
            path=Path(folder)/"20261031"/"tkz"/(code+".json")
            path.write_text(json.dumps(record(code,"tkz",received="2026-10-31T19:59:00+09:00")))
            result=audit(folder)
            self.assertEqual(result["paired_complete_6boat_stt_tkz"],0)
            self.assertEqual(result["invalid"],1)
            self.assertEqual(result["incomplete_pair_reasons_by_race"][0]["race_code"],code)
            self.assertEqual(result["incomplete_pair_reasons_by_race"][0]["tkz"],"missing")
if __name__=="__main__":unittest.main()

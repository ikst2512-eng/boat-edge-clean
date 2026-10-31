import json
import tempfile
import unittest
from pathlib import Path
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
        "six_lane_validation":valid}

class AuditLatePreview(unittest.TestCase):
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
            for kind in ("stt","tkz"):
                early_path=Path(folder)/"20261031"/kind/(code+".json")
                early_record=record(code,kind,received="2026-10-31T19:45:00+09:00")
                early_record["source_row"]["取得日時"]="2026-10-31T19:44:00+09:00"
                early_path.write_text(json.dumps(early_record))
            self.assertEqual(audit(folder)["paired_complete_12min_observable"],1)
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
if __name__=="__main__":unittest.main()

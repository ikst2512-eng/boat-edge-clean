import json
import tempfile
import unittest
from pathlib import Path
from scripts.audit_late_preview_evidence import audit

def record(code,kind,valid="complete",received="2026-10-31T19:55:00+09:00"):
    return {"race_code":code,"kind":kind,"received_at_jst":received,
        "source_row":{"レースコード":code,"締切時刻":"20:00","取得日時":"2026-10-31T19:54:00+09:00"},
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
            path=Path(folder)/"20261031"/"tkz"/(code+".json")
            path.write_text(json.dumps(record(code,"tkz",received="2026-10-31T19:59:00+09:00")))
            result=audit(folder)
            self.assertEqual(result["paired_complete_6boat_stt_tkz"],0)
            self.assertEqual(result["invalid"],1)
if __name__=="__main__":unittest.main()

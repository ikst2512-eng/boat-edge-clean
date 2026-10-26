"""Synthetic fixtures only; these assertions MUST NOT be described as race accuracy."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from scripts.audit_research_outcomes import audit

class AuditTests(unittest.TestCase):
    def test_missing_evidence_fail_closed_and_verified_fixture(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"202610260101.json"
            snap={"race_code":"202610260101", "status":"research", "validated":False,
                  "predictions":["1-2-3","1-2-4","1-3-2","1-3-4","1-4-2",
                                 "1-4-3","2-1-3","2-1-4","2-3-1","2-3-4"],
                  "generated_at":"2026-10-26T09:00:00+09:00",
                  "cutoff_jst":"2026-10-26T10:00:00+09:00",
                  "source_title_received_jst":"2026-10-26T08:59:00+09:00",
                  "source_cards_received_jst":"2026-10-26T08:59:00+09:00"}
            p.write_text(json.dumps(snap))
            self.assertEqual(audit(d,[],[])["valid_count"],0)
            att={"race_code":snap["race_code"],"receipt_verified":True,"model_verified":True,
                 "inputs_verified":True,"result_verified":True,
                 "receipt_id":"test-only","model_git_sha":"a"*40,
                 "model_file_sha256":"b"*64,"input_sha256":"c"*64,
                 "snapshot_sha256":hashlib.sha256(p.read_bytes()).hexdigest(),
                 "first_seen_at":"2026-10-26T09:01:00+09:00",
                 "official_deadline_at":"2026-10-26T10:12:00+09:00"}
            outcome={"race_code":snap["race_code"],"verified":True,"trifecta":"1-2-3"}
            self.assertEqual(audit(d,[att],[outcome])["valid_count"],0)\n            digest=lambda: hashlib.sha256(json.dumps([att],ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()).hexdigest()\n            self.assertEqual(audit(d,[att],[outcome],digest())["metrics"]["top1"]["hits"],1)
            att["first_seen_at"]="2026-10-26T10:01:00+09:00"
            report=audit(d,[att],[outcome],digest())
            self.assertEqual(report["valid_count"],0)
            self.assertEqual(report["exclusion_reasons"]["receipt_after_cutoff"],1)
            att["first_seen_at"]="2026-10-26T09:01:00+09:00"
            p.write_text(p.read_text()+" ")
            self.assertEqual(audit(d,[att],[outcome],digest())["exclusion_reasons"]["snapshot_hash_mismatch"],1)

if __name__=="__main__":
    unittest.main()

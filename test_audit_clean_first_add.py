import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch
import audit_clean_first_add as audit

class FirstAddAuditTests(unittest.TestCase):
    def test_first_add_before_cutoff_only_not_formal(self):
        obj={"race_code":"202610281201","status":"prospective_candidate","formal":False,"scoring":False,
             "source_deadline_jst":"2026-10-28T14:00:00+09:00",
             "cutoff_jst":"2026-10-28T13:48:00+09:00",
             "generated_at":"2026-10-28T10:00:00+09:00",
             "source_title_received_jst":"2026-10-28T09:59:00+09:00",
             "source_cards_received_jst":"2026-10-28T09:59:01+09:00"}
        with patch.object(audit,"first_add",return_value=(json.dumps(obj).encode(),"a"*40,datetime.fromisoformat("2026-10-28T10:01:00+09:00"))):
            x=audit.inspect("prospective_predictions/202610281201.json")
        self.assertFalse(x["formal"])
        self.assertFalse(x["remote_first_seen_verified"])
    def test_late_commit_denied(self):
        obj={"race_code":"202610281201","status":"prospective_candidate","formal":False,"scoring":False,
             "source_deadline_jst":"2026-10-28T14:00:00+09:00",
             "cutoff_jst":"2026-10-28T13:48:00+09:00",
             "generated_at":"2026-10-28T10:00:00+09:00",
             "source_title_received_jst":"2026-10-28T09:59:00+09:00",
             "source_cards_received_jst":"2026-10-28T09:59:01+09:00"}
        with patch.object(audit,"first_add",return_value=(json.dumps(obj).encode(),"a"*40,datetime.fromisoformat("2026-10-28T13:50:00+09:00"))):
            with self.assertRaises(ValueError):
                audit.inspect("prospective_predictions/202610281201.json")
    def test_received_after_generated_rejected(self):
        obj={"race_code":"202610281201","status":"prospective_candidate","formal":False,"scoring":False,
             "source_deadline_jst":"2026-10-28T14:00:00+09:00",
             "cutoff_jst":"2026-10-28T13:48:00+09:00",
             "generated_at":"2026-10-28T10:00:00+09:00",
             "source_title_received_jst":"2026-10-28T10:00:01+09:00",
             "source_cards_received_jst":"2026-10-28T10:00:02+09:00"}
        with patch.object(audit,"first_add",return_value=(json.dumps(obj).encode(),"a"*40,datetime.fromisoformat("2026-10-28T10:01:00+09:00"))):
            with self.assertRaisesRegex(ValueError,"chronology"):
                audit.inspect("prospective_predictions/202610281201.json")

    def test_deadline_date_mismatch_rejected(self):
        obj={"race_code":"202610281201","status":"prospective_candidate","formal":False,"scoring":False,
             "source_deadline_jst":"2026-10-29T14:00:00+09:00",
             "cutoff_jst":"2026-10-29T13:48:00+09:00",
             "generated_at":"2026-10-28T10:00:00+09:00",
             "source_title_received_jst":"2026-10-28T09:59:00+09:00",
             "source_cards_received_jst":"2026-10-28T09:59:01+09:00"}
        with patch.object(audit,"first_add",return_value=(json.dumps(obj).encode(),"a"*40,datetime.fromisoformat("2026-10-28T10:01:00+09:00"))):
            with self.assertRaises(ValueError):
                audit.inspect("prospective_predictions/202610281201.json")
    def test_commit_preceding_generation_rejected(self):
        obj={"race_code":"202610281201","status":"prospective_candidate","formal":False,"scoring":False,
             "source_deadline_jst":"2026-10-28T14:00:00+09:00",
             "cutoff_jst":"2026-10-28T13:48:00+09:00",
             "generated_at":"2026-10-28T10:00:00+09:00",
             "source_title_received_jst":"2026-10-28T09:59:00+09:00",
             "source_cards_received_jst":"2026-10-28T09:59:01+09:00"}
        with patch.object(audit,"first_add",return_value=(json.dumps(obj).encode(),"a"*40,datetime.fromisoformat("2026-10-28T09:59:30+09:00"))):
            with self.assertRaises(ValueError):
                audit.inspect("prospective_predictions/202610281201.json")
    def test_untrusted_path(self):
        with self.assertRaises(ValueError):
            audit.first_add("../legacy/anything.json")
if __name__=="__main__":
    unittest.main()

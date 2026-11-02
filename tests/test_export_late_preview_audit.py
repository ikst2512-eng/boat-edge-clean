import tempfile
import unittest
from pathlib import Path
from scripts.export_late_preview_audit import report

class ExportLatePreviewAuditTests(unittest.TestCase):
    def test_missing_archive_is_not_mistaken_for_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            result=report(Path(tmp)/"missing")
            self.assertEqual(result["verification_status"],"evidence_root_missing")
            self.assertFalse(result["archived_records_found"])
            self.assertEqual(result["audit"]["paired_complete_12min_observable"],0)

    def test_empty_archive_has_distinct_status(self):
        with tempfile.TemporaryDirectory() as tmp:
            result=report(tmp)
            self.assertEqual(result["verification_status"],"no_archived_race_records")
            self.assertFalse(result["archived_records_found"])

if __name__=="__main__":
    unittest.main()

"""Case-audit invariants: without archived data, no invented win counts."""
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from hole_second_pair_case_audit import audit

class AuditTest(unittest.TestCase):
    def test_empty_archives_fail_closed(self):
        with TemporaryDirectory() as tmp:
            report = audit(Path(tmp))
            self.assertEqual(report["status"], "no_paired_archives")
            self.assertIs(report["formal"], False)
            self.assertNotIn("summary", report)

if __name__ == "__main__":
    unittest.main()

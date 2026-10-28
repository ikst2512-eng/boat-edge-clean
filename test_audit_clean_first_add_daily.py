import tempfile
import unittest
from pathlib import Path
from audit_clean_first_add_daily import audit

class FirstAddEvidenceTests(unittest.TestCase):
    def test_first_add_verified(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/"four_mode_forecasts";p.mkdir()
            (p/"202610290101.json").write_text('{"race_code":"202610290101","deadline_jst":"2026-10-29T12:00:00+09:00"}')
            x=audit("20261029",Path(tmp),checker=lambda path,deadline:"abc123")
            self.assertEqual(x["verified_first_add"],1)
            self.assertEqual(x["failures"],[])
            self.assertFalse(x["official_results_checked"])
    def test_missing_proof_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/"four_mode_forecasts";p.mkdir()
            (p/"202610290101.json").write_text('{"race_code":"202610290101","deadline_jst":"2026-10-29T12:00:00+09:00"}')
            def fail(path,deadline):raise ValueError("first_add_after_deadline")
            x=audit("20261029",Path(tmp),checker=fail)
            self.assertEqual(x["verified_first_add"],0)
            self.assertEqual(x["failures"][0]["issue"],"first_add_after_deadline")
if __name__=="__main__":unittest.main()

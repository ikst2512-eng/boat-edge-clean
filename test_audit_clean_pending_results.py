import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from audit_clean_pending_results import audit
from research_model import JST

class PendingResultCoverageTests(unittest.TestCase):
    def test_future_missing_result_is_not_overdue_or_miss(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/"four_mode_forecasts";p.mkdir()
            (p/"202610290101.json").write_text(json.dumps({"race_code":"202610290101","deadline_jst":"2026-10-29T14:00:00+09:00"}))
            report=audit(tmp,"20261029",datetime(2026,10,29,6,30,tzinfo=JST))
            self.assertEqual(report["before_deadline"],1)
            self.assertEqual(report["awaiting_result_overdue"],0)
            self.assertTrue(report["no_result_is_not_a_miss"])
            late=audit(tmp,"20261029",datetime(2026,10,29,14,30,tzinfo=JST))
            self.assertEqual(late["awaiting_result_overdue"],1)
            self.assertEqual(late["overdue_race_codes"],["202610290101"])
    def test_result_file_present_not_claimed_verified(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/"four_mode_forecasts";p.mkdir()
            (p/"202610290101.json").write_text(json.dumps({"race_code":"202610290101","deadline_jst":"2026-10-29T14:00:00+09:00"}))
            q=Path(tmp)/"confirmed_results";q.mkdir()
            (q/"202610290101.json").write_text("{}")
            report=audit(tmp,"20261029",datetime(2026,10,29,15,0,tzinfo=JST))
            self.assertEqual(report["confirmed_result_file_present"],1)
            self.assertFalse(report["official_results_validated"])
if __name__=="__main__":unittest.main()

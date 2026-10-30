import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch
import server


class ArchivedProspectiveTests(unittest.TestCase):
    def test_saved_candidate_is_research_not_validated(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "prospective_predictions").mkdir()
            record = {
                "race_code": "202610300101",
                "status": "prospective_candidate",
                "validated": False,
                "model_version": "research-test",
                "generated_at": "2026-10-30T10:00:00+09:00",
                "cutoff_jst": "2026-10-30T15:00:00+09:00",
                "predictions": ["1-2-3", "1-2-4", "1-3-2", "1-3-4", "1-4-2",
                                "1-4-3", "2-1-3", "2-1-4", "2-3-1", "2-3-4"]
            }
            p = root / "prospective_predictions" / "202610300101.json"
            p.write_text(json.dumps(record), encoding="utf-8")
            with patch.object(server, "ROOT", root):
                status, response = server.get_predictions({"hd": ["20261030"], "jcd": ["01"], "rno": ["1"]})
            self.assertEqual(status, 200)
            self.assertEqual(response["predictions"], record["predictions"])
            self.assertFalse(response["validated"])
            self.assertFalse(response["formal"])
            self.assertEqual(response["status"], "research")

    def test_unpadded_venue_is_invalid(self):
        status, response = server.get_predictions({"hd": ["20261030"], "jcd": ["1"], "rno": ["1"]})
        self.assertEqual(status, 400)
        self.assertFalse(response["ok"])

    def test_archive_generated_after_cutoff_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "prospective_predictions").mkdir()
            record = {
                "race_code": "202610300101", "status": "prospective_candidate",
                "validated": False, "model_version": "research-test",
                "generated_at": "2026-10-30T16:00:00+09:00",
                "cutoff_jst": "2026-10-30T15:00:00+09:00",
                "predictions": ["1-2-3", "1-2-4", "1-3-2", "1-3-4", "1-4-2",
                                "1-4-3", "2-1-3", "2-1-4", "2-3-1", "2-3-4"]
            }
            (root / "prospective_predictions" / "202610300101.json").write_text(json.dumps(record))
            with patch.object(server, "ROOT", root):
                status, response = server.get_predictions({"hd": ["20261030"], "jcd": ["01"], "rno": ["1"]})
            self.assertEqual(status, 503)
            self.assertEqual(response["predictions"], [])


if __name__ == "__main__":
    unittest.main()

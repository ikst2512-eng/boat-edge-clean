"""Candidate diagnostic smoke tests, synthetic inputs only."""
import json
import tempfile
import unittest
from pathlib import Path
from research_candidate_diagnostic import inspect, diagnostic

class DiagnosticTests(unittest.TestCase):
    def row(self):
        return {"race_code": "202610271201", "national_win_rates": [6] * 6,
                "entry": [2, 1, 3, 4, 5, 6], "entry_status": "pre_cutoff_verified"}

    def test_verified_entry(self):
        item = inspect(self.row())
        self.assertFalse(item["entry_assumed"])
        self.assertEqual(len(item["candidate_top10"]), 10)
        self.assertFalse(item["actual_scored"])

    def test_missing_entry_marked(self):
        row = self.row()
        row.pop("entry")
        row["entry_status"] = "missing"
        item = inspect(row)
        self.assertTrue(item["entry_assumed"])
        self.assertIn("motor", item["missing_features"])

    def test_false_verified_entry_rejected(self):
        row = self.row()
        row.pop("entry")
        with self.assertRaises(ValueError):
            inspect(row)

    def test_duplicate_races_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "data.jsonl"
            line = json.dumps(self.row())
            path.write_text(line + "\n" + line + "\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "duplicate race"):
                diagnostic(path)

if __name__ == "__main__":
    unittest.main()

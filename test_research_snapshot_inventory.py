import json
import tempfile
import unittest
from pathlib import Path
from research_snapshot_inventory import inventory

class InventoryTests(unittest.TestCase):
    def test_actual_saved_forecast_not_misclassified_as_scoreable(self):
        report = inventory(Path(__file__).parent / "research_snapshots")
        self.assertGreater(report["counts"].get("files", 0), 0)
        self.assertGreater(report["counts"].get("structurally_valid_top10", 0), 0)
        self.assertEqual(report["formally_scoreable_from_snapshot_alone"], 0)
        self.assertEqual(report["status"], "INVENTORY_ONLY_NOT_RESULT_SCORING")

    def test_missing_provenance_is_explicit(self):
        with tempfile.TemporaryDirectory() as folder:
            obj = {"race_code":"202610270101", "status":"research",
                   "validated":False, "model_version":"legacy-research",
                   "predictions":[f"1-2-{i}" for i in range(10)]}
            Path(folder, "202610270101.json").write_text(json.dumps(obj), encoding="utf-8")
            report = inventory(folder)
            self.assertEqual(report["counts"]["structurally_valid_top10"], 1)
            self.assertEqual(report["reasons"]["missing_provenance_fields"], 1)

if __name__ == "__main__":
    unittest.main()

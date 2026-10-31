"""Audit separates archived forecasts with real stored mass from older records."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from scripts import research_topn_batch_audit as audit


class MassCohortAudit(unittest.TestCase):
    def test_independent_legacy_and_new_cohorts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "research_snapshots").mkdir()
            (root / "confirmed_results").mkdir()
            for i, mass in [(1, None), (2, {"3": 18, "5": 26, "10": 43})]:
                code = f"2026103101{i:02d}"
                forecast = {"race_code": code, "status": "research", "validated": False,
                            "model_version": "test", "predictions": ["1-2-3", "1-3-2", "2-1-3",
                            "2-3-1", "3-1-2", "3-2-1", "1-2-4", "1-4-2", "4-1-2", "4-2-1"]}
                if mass is not None:
                    forecast.update(topn_model_mass_pct=mass, confidence_calibrated=False)
                (root / "research_snapshots" / (code + ".json")).write_text(json.dumps(forecast))
                (root / "confirmed_results" / (code + ".json")).write_text(json.dumps({
                    "race_code": code, "status": "confirmed", "finish_order": [1, 2, 3]
                }))
            with patch.object(audit, "ROOT", root):
                result = audit.run()
            self.assertEqual(result["counts"]["matched"], 2)
            self.assertEqual(result["by_mass_cohort"]["with_topn_mass"]["matched"], 1)
            self.assertEqual(result["by_mass_cohort"]["without_topn_mass"]["matched"], 1)
            self.assertEqual(result["by_mass_cohort"]["with_topn_mass"]["top3"], 1)


if __name__ == "__main__":
    unittest.main()

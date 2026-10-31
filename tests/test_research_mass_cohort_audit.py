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
                            "model_version": "test", "generated_at": "2026-10-31T10:00:00+09:00",
                            "cutoff_jst": "2026-10-31T10:30:00+09:00",
                            "source_deadline_jst": "2026-10-31T10:42:00+09:00", "predictions": ["1-2-3", "1-3-2", "2-1-3",
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
            self.assertEqual(result["by_day"]["20261031"]["matched"], 2)
            self.assertEqual(result["by_day"]["20261031"]["saved_forecasts"], 2)
            self.assertEqual(result["by_day"]["20261031"]["result_coverage_pct"], 100.0)
            self.assertEqual(result["by_day"]["20261031"]["sample_status"], "insufficient_sample")
            self.assertEqual(result["by_day"]["20261031"]["top3_rate_pct"], 100.0)
            self.assertEqual(result["by_mass_cohort"]["with_topn_mass"]["matched"], 1)
            self.assertEqual(result["by_mass_cohort"]["without_topn_mass"]["matched"], 1)
            self.assertEqual(result["by_mass_cohort"]["with_topn_mass"]["top3"], 1)

    def test_unmatched_forecast_day_is_not_hidden(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "research_snapshots").mkdir()
            (root / "confirmed_results").mkdir()
            code = "202610310101"
            (root / "research_snapshots" / (code + ".json")).write_text(json.dumps({
                "race_code": code, "status": "research", "validated": False,
                "predictions": ["1-2-3"],
            }))
            with patch.object(audit, "ROOT", root):
                result = audit.run()
            day = result["by_day"]["20261031"]
            self.assertEqual(day["matched"], 0)
            self.assertEqual(day["saved_forecasts"], 1)
            self.assertEqual(day["saved_results"], 0)
            self.assertEqual(day["forecast_without_result"], 1)
            self.assertEqual(day["result_coverage_pct"], 0.0)
            self.assertEqual(day["sample_status"], "insufficient_sample")
            self.assertIsNone(day["top10_rate_pct"])

    def test_invalid_finishes_and_tickets_are_rejected(self):
        valid_tickets = ["1-2-3", "1-3-2", "2-1-3", "2-3-1", "3-1-2",
                         "3-2-1", "1-2-4", "1-4-2", "4-1-2", "4-2-1"]
        cases = [
            ([1, 1, 2], valid_tickets),
            ([1, 2, 7], valid_tickets),
            ([True, 2, 3], valid_tickets),
            (["1", 2, 3], valid_tickets),
            ([1, 2, 3], valid_tickets[:-1] + ["1-2-7"]),
        ]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "research_snapshots").mkdir()
            (root / "confirmed_results").mkdir()
            for i, (finish, tickets) in enumerate(cases, start=1):
                code = f"2026103101{i:02d}"
                (root / "research_snapshots" / (code + ".json")).write_text(json.dumps({
                    "race_code": code, "status": "research", "validated": False,
                    "predictions": tickets,
                }))
                (root / "confirmed_results" / (code + ".json")).write_text(json.dumps({
                    "race_code": code, "status": "confirmed", "finish_order": finish,
                }))
            with patch.object(audit, "ROOT", root):
                result = audit.run()
            self.assertEqual(result["counts"]["matched"], 0)
            self.assertEqual(result["counts"]["rejected"], len(cases))
            self.assertIsNone(result["counts"]["top10_rate_pct"])



if __name__ == "__main__":
    unittest.main()

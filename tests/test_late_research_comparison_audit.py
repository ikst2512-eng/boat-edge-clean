import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from scripts.late_research_comparison_audit import audit


class ComparisonReadinessTests(unittest.TestCase):
    def test_only_same_race_valid_early_forecast_and_finish_are_counted(self):
        code="202610310708"
        pair={"race_code":code,
              "both_sources_received_at_jst":"2026-10-31T17:00:00+09:00"}
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            (root/"research_snapshots").mkdir()
            (root/"confirmed_results").mkdir()
            (root/"research_snapshots"/(code+".json")).write_text(json.dumps({
                "race_code":code,"status":"research",
                "generated_at":"2026-10-31T16:30:00+09:00"}))
            (root/"confirmed_results"/(code+".json")).write_text(json.dumps({
                "race_code":code,"status":"confirmed","finish_order":[1,3,2]}))
            with patch("scripts.late_research_comparison_audit.build",
                       return_value={"ready_count":1,"records":[pair]}):
                value=audit("20261031",root,root)
                self.assertEqual(value["complete_comparison_cohort"],1)
                self.assertEqual(value["rows"][0]["preview_relative_to_early_forecast"],"after")
                self.assertEqual(value["late_model_forecasts"],0)
                # Invalid confirmed results may never count as usable comparisons.
                (root/"confirmed_results"/(code+".json")).write_text(json.dumps({
                    "race_code":code,"status":"confirmed","finish_order":[1,1,2]}))
                invalid=audit("20261031",root,root)
                self.assertEqual(invalid["complete_comparison_cohort"],0)
                self.assertEqual(invalid["confirmed_result_matches"],0)


if __name__=="__main__":
    unittest.main()

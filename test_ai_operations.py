import unittest
from unittest.mock import patch

import ai_operations


class OperationsGateTests(unittest.TestCase):
    def test_unavailable_samples_block_promotion(self):
        result = ai_operations.assess({"status": "insufficient_split", "train": 1})
        self.assertEqual(result["decision"], "insufficient_evidence")
        self.assertFalse(result["production_change_allowed"])

    def test_candidate_improvement_still_requires_audit(self):
        result = ai_operations.assess({
            "status": "research_backtest_only",
            "holdout_baseline_beta_0_4": {"top3": 0.1, "top5": 0.2, "top10": 0.3},
            "holdout_selected": {"top3": 0.2, "top5": 0.3, "top10": 0.4},
        })
        self.assertEqual(result["decision"], "research_candidate_only")
        self.assertFalse(result["production_change_allowed"])

    def test_regression_blocks_promotion(self):
        result = ai_operations.assess({
            "status": "research_backtest_only",
            "holdout_baseline_beta_0_4": {"top3": 0.2, "top5": 0.3, "top10": 0.4},
            "holdout_selected": {"top3": 0.1, "top5": 0.3, "top10": 0.4},
        })
        self.assertEqual(result["decision"], "research_candidate_regressed")
        self.assertIn("Top3", result["reason"])

    def test_report_never_promotes(self):
        with patch.object(ai_operations, "report", return_value={"status": "insufficient_chronological_days"}):
            result = ai_operations.build_report(rows=[])
        self.assertFalse(result["automatic_model_promotion"])
        self.assertFalse(result["automatic_production_code_change"])
        self.assertFalse(result["gate"]["production_change_allowed"])


if __name__ == "__main__":
    unittest.main()

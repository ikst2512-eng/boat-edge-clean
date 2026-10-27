"""Leakage-resistant chronological research calibration checks."""
import unittest
from research_chronological_calibration import metrics, report

class CalibrationTests(unittest.TestCase):
    def test_no_lookahead_without_second_date(self):
        rows=[("202610260101",[6.0]*6,(1,2,3))]
        self.assertEqual(report(rows,1,1)["status"],"insufficient_chronological_days")

    def test_holdout_is_latest_day_only(self):
        rows=[(f"20261026{v:02d}01",[6.0]*6,(1,2,3)) for v in range(1,4)]
        rows += [(f"20261027{v:02d}01",[6.0]*6,(2,1,3)) for v in range(1,3)]
        result=report(rows,3,2)
        self.assertEqual(result["status"],"research_backtest_only")
        self.assertEqual(result["train_races"],3)
        self.assertEqual(result["holdout_races"],2)
        self.assertEqual(result["holdout_date"],"20261027")
        self.assertEqual(result["holdout_baseline_beta_0_4"]["races"],2)

    def test_metrics_no_records(self):
        self.assertIsNone(metrics([],0.4))

if __name__=="__main__":
    unittest.main()

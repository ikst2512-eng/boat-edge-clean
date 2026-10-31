"""Leakage-resistant chronological research calibration checks."""
import unittest
import json
import tempfile
from pathlib import Path
from research_chronological_calibration import load_pairs
from research_chronological_calibration import metrics, report
from research_model import probabilities

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

    def test_late_input_is_not_used_for_holdout(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "research_snapshots").mkdir()
            (root / "confirmed_results").mkdir()
            code = "202610300101"
            record = {
                "race_code": code, "status": "research", "validated": False,
                "generated_at": "2026-10-30T11:47:30+09:00",
                "cutoff_jst": "2026-10-30T11:48:00+09:00",
                "source_deadline_jst": "2026-10-30T12:00:00+09:00",
                "source_title_received_jst": "2026-10-30T10:00:00+09:00",
                "source_cards_received_jst": "2026-10-30T11:49:00+09:00",
                "national_win_rates": [5.0] * 6,
                "predictions": ["-".join(map(str, t)) for t, _ in probabilities([5.0] * 6, 0.4)[:10]],
            }
            result = {
                "race_code": code, "status": "confirmed",
                "confirmed_at_jst": "2026-10-30T12:20:00+09:00",
                "finish_order": [1, 2, 3],
            }
            (root / "research_snapshots" / (code + ".json")).write_text(json.dumps(record))
            (root / "confirmed_results" / (code + ".json")).write_text(json.dumps(result))
            self.assertEqual(load_pairs(root), [])
            record["source_cards_received_jst"] = "2026-10-30T11:47:00+09:00"
            (root / "research_snapshots" / (code + ".json")).write_text(json.dumps(record))
            self.assertEqual(len(load_pairs(root)), 1)
            record["predictions"] = list(reversed(record["predictions"]))
            (root / "research_snapshots" / (code + ".json")).write_text(json.dumps(record))
            self.assertEqual(load_pairs(root), [])
            record["predictions"] = ["-".join(map(str, t)) for t, _ in probabilities([5.0] * 6, 0.4)[:10]]
            record["generated_at"] = "2026-10-30T10:00:00+09:00"
            (root / "research_snapshots" / (code + ".json")).write_text(json.dumps(record))
            self.assertEqual(load_pairs(root), [])
            record["generated_at"] = "2026-10-30T11:47:30+09:00"
            record["source_deadline_jst"] = "2026-10-30T12:01:00+09:00"
            (root / "research_snapshots" / (code + ".json")).write_text(json.dumps(record))
            self.assertEqual(load_pairs(root), [])

    def test_metrics_no_records(self):
        self.assertIsNone(metrics([],0.4))

if __name__=="__main__":
    unittest.main()

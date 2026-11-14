"""Contract tests for result-blind T12 theoretical timing feasibility."""
from datetime import datetime
import json
from pathlib import Path
import tempfile
import unittest

from clean_four_modes import rank_modes
from research_model import probabilities
from position_sensitive_t12_window_audit import audit_window

RATES = [5.01,5.89,6.28,2.64,6.09,6.15]


def record():
    return {
        "schema":"CLEAN_FOUR_MODES_PREDEADLINE_V1",
        "race_code":"202611080101",
        "model_version":"CLEAN_FOUR_MODES_V2_PROVISIONAL_UNCALIBRATED",
        "validated":False,
        "target_rates_not_proven":True,
        "generated_at_jst":"2026-11-08T10:00:00+09:00",
        "deadline_jst":"2026-11-08T12:40:00+09:00",
        "source_title_received_jst":"2026-11-08T09:58:00+09:00",
        "source_cards_received_jst":"2026-11-08T09:59:00+09:00",
        "input_national_win_rates":RATES,
        "modes":rank_modes(probabilities(RATES)),
    }


class WindowTests(unittest.TestCase):
    def test_positive_window_is_only_local_theory(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            (root/"four_mode_forecasts").mkdir()
            (root/"confirmed_results").mkdir()
            bad_result=root/"confirmed_results"/"202611080101.json"
            bad_result.write_text("INTENTIONALLY_BAD_JSON")
            file=root/"four_mode_forecasts"/"202611080101.json"
            original=json.dumps(record(),sort_keys=True)
            file.write_text(original)
            outcome=audit_window("20261108",root)
            self.assertEqual(outcome["compared"],1)
            self.assertEqual(outcome["excluded"],0)
            self.assertEqual(outcome["theoretical_window_seconds"]["median"],8880.0)
            self.assertEqual(outcome["greater_than_90s_local_window"],1)
            self.assertFalse(outcome["independent_remote_candidate_receipts_verified"])
            self.assertEqual(outcome["actual_candidate_publications"],0)
            self.assertFalse(outcome["formal"])
            self.assertEqual(file.read_text(),original)
            self.assertEqual(bad_result.read_text(),"INTENTIONALLY_BAD_JSON")

    def test_candidate_window_closed_is_not_falsely_positive(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            (root/"four_mode_forecasts").mkdir()
            data=record()
            data["generated_at_jst"]="2026-11-08T12:29:00+09:00"
            data["source_title_received_jst"]="2026-11-08T12:27:00+09:00"
            data["source_cards_received_jst"]="2026-11-08T12:28:00+09:00"
            (root/"four_mode_forecasts"/"202611080101.json").write_text(json.dumps(data))
            o=audit_window("20261108",root)
            self.assertEqual(o["compared"],1)
            self.assertEqual(o["original_generated_at_or_after_T12"],1)
            self.assertEqual(o["greater_than_90s_local_window"],0)
            self.assertFalse(o["promotion_allowed"])

    def test_corrupt_board_excluded_and_original_left_unchanged(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            (root/"four_mode_forecasts").mkdir()
            data=record()
            data["modes"]["hit"]["tickets"][0]["p"]=-100
            original=json.dumps(data)
            f=root/"four_mode_forecasts"/"202611080101.json"
            f.write_text(original)
            o=audit_window("20261108",root)
            self.assertEqual(o["excluded"],1)
            self.assertEqual(o["compared"],0)
            self.assertEqual(o["exclusions"]["original_board_drift"],1)
            self.assertEqual(f.read_text(),original)

    def test_empty_and_bad_day_no_false_publication(self):
        with tempfile.TemporaryDirectory() as td:
            o=audit_window("20261108",td)
            self.assertIsNone(o["theoretical_window_seconds"]["min"])
            self.assertFalse(o["formal"])
            self.assertEqual(o["actual_candidate_publications"],0)
        for day in ("../result","2026-11-08","2026118"):
            with self.assertRaises(ValueError):
                audit_window(day)


if __name__=="__main__":
    unittest.main()

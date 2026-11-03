import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from clean_four_modes import rank_modes
from research_model import probabilities
from four_mode_v2_head_calibration import assess, VERSION

RATES = [6.2, 5.1, 4.5, 5.4, 3.8, 4.9]


def saved(root, code, tamper=False):
    directory = root / "four_mode_forecasts"
    directory.mkdir(exist_ok=True)
    modes = rank_modes(probabilities(RATES))
    if tamper:
        modes["hit"]["tickets"][0]["p"] += 0.01
    record = {
        "schema": "CLEAN_FOUR_MODES_PREDEADLINE_V1",
        "race_code": code, "model_version": VERSION,
        "generated_at_jst": "2026-11-03T09:00:00+09:00",
        "deadline_jst": "2026-11-03T11:00:00+09:00",
        "input_national_win_rates": RATES, "modes": modes,
    }
    (directory / (code + ".json")).write_text(json.dumps(record))


class HeadCalibrationTests(unittest.TestCase):
    def test_two_confirmed_one_missing_kept_separate(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            for code in ("202611030101", "202611030102", "202611030103"):
                saved(root, code)
            def compared(code, root):
                if code.endswith("03"):
                    return {"status": "result_unavailable"}
                return {"status": "historical_comparison_only",
                        "winning_ticket": "1-2-3" if code.endswith("01") else "2-1-3"}
            with patch("four_mode_v2_head_calibration.compare_race", side_effect=compared):
                report = assess(root)
            p1 = sum(p for combo, p in probabilities(RATES) if combo[0] == 1)
            self.assertEqual(report["matched_valid_finish"], 2)
            self.assertEqual(report["missing_finish"], 1)
            self.assertEqual(report["observed_boat1_wins"], 1)
            self.assertAlmostEqual(report["mean_predicted_boat1"], p1, places=6)
            self.assertAlmostEqual(report["boat1_brier_score"],
                                   ((p1-1)**2 + p1**2)/2, places=6)
            self.assertEqual(report["constant_0_5_brier_on_same_cohort"], 0.25)
            self.assertEqual(report["sample_by_day"]["20261103"]["n"], 2)
            self.assertFalse(report["formal"])

    def test_invalid_result_not_counted_as_loss(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            saved(root, "202611030101")
            with patch("four_mode_v2_head_calibration.compare_race",
                       return_value={"status": "invalid_result_or_timing"}):
                report = assess(root)
            self.assertEqual(report["invalid_or_untrusted_finish"], 1)
            self.assertEqual(report["matched_valid_finish"], 0)
            self.assertIsNone(report["boat1_brier_score"])
            self.assertIsNone(report["observed_boat1_rate"])

    def test_nonreproducible_archive_excluded_from_calibration(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            saved(root, "202611030101", tamper=True)
            with patch("four_mode_v2_head_calibration.compare_race") as compared:
                report = assess(root)
            compared.assert_not_called()
            self.assertEqual(report["not_reproduced"], 1)
            self.assertEqual(report["matched_valid_finish"], 0)

    def test_no_archive_is_not_zero_calibration(self):
        with tempfile.TemporaryDirectory() as td:
            report = assess(td)
            self.assertEqual(report["status"], "no_forecast_directory")
            self.assertIsNone(report["boat1_brier_score"])


if __name__ == "__main__":
    unittest.main()

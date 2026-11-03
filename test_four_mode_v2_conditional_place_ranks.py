import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from clean_four_modes import rank_modes
from research_model import probabilities
from four_mode_v2_conditional_place_ranks import (
    VERSION, audit, conditional_ranks,
)

RATES = [5.1, 6.3, 4.5, 5.7, 3.7, 4.3]


def fixture(root, code="202611030101", tamper=False):
    directory = root / "four_mode_forecasts"
    directory.mkdir(exist_ok=True)
    modes = rank_modes(probabilities(RATES))
    if tamper:
        modes["hit"]["tickets"][0]["p"] += 0.01
    record = {
        "schema": "CLEAN_FOUR_MODES_PREDEADLINE_V1",
        "race_code": code,
        "model_version": VERSION,
        "generated_at_jst": "2026-11-03T08:00:00+09:00",
        "deadline_jst": "2026-11-03T12:00:00+09:00",
        "input_national_win_rates": RATES,
        "modes": modes,
    }
    (directory / (code + ".json")).write_text(json.dumps(record), encoding="utf-8")


class ConditionalRankTests(unittest.TestCase):
    def test_second_and_third_rank_are_explicit_oracle_conditions(self):
        board = probabilities(RATES)
        second, third = conditional_ranks(board, "2-1-3")
        self.assertTrue(1 <= second["rank"] <= 5)
        self.assertTrue(1 <= third["rank"] <= 4)
        self.assertTrue(0 < second["probability"] < 1)
        self.assertTrue(0 < third["probability"] < 1)
        self.assertEqual(second["rank"] == 1, second["top_candidate"] == 1)
        self.assertEqual(third["rank"] == 1, third["top_candidate"] == 3)

    def test_rejects_invalid_finish_and_short_board(self):
        board = probabilities(RATES)
        for finish in ("1-1-2", "7-1-2", "1-2", "1-2-3-4"):
            with self.assertRaises(ValueError):
                conditional_ranks(board, finish)
        with self.assertRaises(ValueError):
            conditional_ranks(board[:20], "1-2-3")

    def test_matched_vs_missing_do_not_leak_into_prediction(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            fixture(root, "202611030101")
            fixture(root, "202611030102")
            def compared(code, root):
                if code.endswith("02"):
                    return {"status": "result_unavailable"}
                return {"status": "historical_comparison_only",
                        "winning_ticket": "2-1-3"}
            with patch("four_mode_v2_conditional_place_ranks.compare_race",
                       side_effect=compared):
                out = audit(root)
            self.assertEqual(out["cohort"]["saved_v2"], 2)
            self.assertEqual(out["cohort"]["paired"], 1)
            self.assertEqual(out["cohort"]["missing_result"], 1)
            self.assertEqual(sum(out["second_given_actual_first"]["rank_counts"].values()), 1)
            self.assertEqual(sum(out["third_given_actual_first_second"]["rank_counts"].values()), 1)
            self.assertEqual(out["by_winner_head"]["2"]["n"], 1)
            self.assertFalse(out["formal"])
            self.assertTrue(out["uses_actual_winner_for_oracle_condition"])

    def test_nonreproducible_archive_not_scored(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            fixture(root, tamper=True)
            with patch("four_mode_v2_conditional_place_ranks.compare_race") as compared:
                out = audit(root)
            compared.assert_not_called()
            self.assertEqual(out["cohort"]["mismatch"], 1)
            self.assertEqual(out["cohort"]["paired"], 0)
            self.assertIsNone(out["second_given_actual_first"]["mean_assigned_probability"])

    def test_no_archives_yields_null_mean_not_zero_rate(self):
        with tempfile.TemporaryDirectory() as td:
            out = audit(td)
            self.assertEqual(out["status"], "no_forecast_directory")
            self.assertIsNone(out["third_given_actual_first_second"]["mean_assigned_probability"])


if __name__ == "__main__":
    unittest.main()

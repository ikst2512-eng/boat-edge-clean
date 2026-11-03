import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from clean_four_modes import rank_modes
from research_model import probabilities
from four_mode_v2_national_head_shadow import audit, candidate, VERSION

RATES = [4.1, 6.5, 5.9, 3.9, 4.2, 5.7]


def save(root, code, tamper=False):
    folder = root / "four_mode_forecasts"
    folder.mkdir(exist_ok=True)
    modes = rank_modes(probabilities(RATES))
    if tamper:
        modes["hit"]["tickets"][0]["p"] += 0.02
    record = {
        "schema": "CLEAN_FOUR_MODES_PREDEADLINE_V1",
        "race_code": code,
        "generated_at_jst": "2026-11-03T08:00:00+09:00",
        "deadline_jst": "2026-11-03T12:00:00+09:00",
        "model_version": VERSION,
        "input_national_win_rates": RATES,
        "modes": modes,
    }
    (folder / (code + ".json")).write_text(json.dumps(record))


class NationalHeadShadowTests(unittest.TestCase):
    def test_candidates_use_only_frozen_rates_and_scores(self):
        board = probabilities(RATES)
        baseline = [row["combo"] for row in rank_modes(board)["hit"]["tickets"]]
        altered, heads, inserted = candidate(baseline, RATES, board)
        self.assertEqual(heads, [2, 3])
        self.assertEqual(len(altered), 10)
        self.assertEqual(len(set(altered)), 10)
        self.assertEqual(len(inserted), len(set(inserted)))
        self.assertEqual(set(altered) - set(baseline), set(inserted))
        for head in heads:
            self.assertTrue(any(int(ticket[0]) == head for ticket in altered))

    def test_full_match_and_missing_are_separate(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            save(root, "202611030101")
            save(root, "202611030102")
            def compared(code, root):
                return ({"status": "result_unavailable"} if code.endswith("02")
                        else {"status": "historical_comparison_only",
                              "winning_ticket": "2-1-3"})
            with patch("four_mode_v2_national_head_shadow.compare_race",
                       side_effect=compared):
                out = audit(root)
            self.assertEqual(out["valid_forecasts"], 2)
            self.assertEqual(out["reproduced_forecasts"], 2)
            self.assertEqual(out["paired_results"], 1)
            self.assertEqual(out["missing_results"], 1)
            self.assertEqual(out["by_date"]["20261103"]["paired"], 1)
            for n in (3, 5, 10):
                score = out["topn"][f"top{n}"]
                self.assertEqual(score["candidate"] - score["baseline"],
                                 score["gained"] - score["lost"])
            self.assertFalse(out["formal"])
            self.assertFalse(out["independent_holdout_verified"])

    def test_invalid_or_unreproducible_not_scored(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            save(root, "202611030101", tamper=True)
            with patch("four_mode_v2_national_head_shadow.compare_race") as compared:
                out = audit(root)
            compared.assert_not_called()
            self.assertEqual(out["nonreproduced"], 1)
            self.assertEqual(out["paired_results"], 0)

    def test_reject_bad_rates_and_baseline(self):
        board = probabilities(RATES)
        baseline = [row["combo"] for row in rank_modes(board)["hit"]["tickets"]]
        with self.assertRaises(ValueError):
            candidate(baseline, [6.1, 5.5], board)
        with self.assertRaises(ValueError):
            candidate(baseline[:9] + [baseline[0]], RATES, board)

    def test_no_directory_returns_no_accuracy(self):
        with tempfile.TemporaryDirectory() as td:
            report = audit(td)
            self.assertEqual(report["status"], "no_forecast_directory")
            self.assertEqual(report["paired_results"], 0)


if __name__ == "__main__":
    unittest.main()

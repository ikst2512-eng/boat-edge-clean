import json
import math
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from clean_four_modes import rank_modes
from research_model import probabilities
from four_mode_v2_third_rate_shadow import VERSION, audit, candidate

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


class ThirdRateShadowTests(unittest.TestCase):
    def test_candidate_deterministic_and_count_unchanged(self):
        board = probabilities(RATES)
        base = [x["combo"] for x in rank_modes(board)["hit"]["tickets"]]
        first, diversity = candidate(base, RATES, board)
        second, _ = candidate(base, RATES, board)
        self.assertEqual(first, second)
        self.assertEqual(len(first), 10)
        self.assertEqual(len(set(first)), 10)
        self.assertGreaterEqual(diversity, 1)
        self.assertTrue(set(first).issubset({"-".join(map(str, t)) for t, _ in board}))

    def test_flat_rates_do_not_change_any_ranking(self):
        rates = [5.0] * 6
        board = probabilities(rates)
        baseline = [x["combo"] for x in rank_modes(board)["hit"]["tickets"]]
        shadow, _ = candidate(baseline, rates, board)
        self.assertEqual(shadow, baseline)

    def test_same_race_paired_and_missing_separate(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            save(root, "202611030101")
            save(root, "202611030102")
            def compared(code, root):
                if code.endswith("02"):
                    return {"status": "result_unavailable"}
                return {"status": "historical_comparison_only",
                        "winning_ticket": "2-1-3"}
            with patch("four_mode_v2_third_rate_shadow.compare_race", side_effect=compared):
                result = audit(root)
            self.assertEqual(result["reproduced_forecasts"], 2)
            self.assertEqual(result["paired_results"], 1)
            self.assertEqual(result["missing_results"], 1)
            for top in (3, 5, 10):
                score = result["topn"][f"top{top}"]
                self.assertEqual(score["candidate"] - score["baseline"],
                                 score["gained"] - score["lost"])
            self.assertFalse(result["formal"])
            self.assertFalse(result["independent_holdout_verified"])

    def test_nonreproducible_archive_never_scored(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            save(root, "202611030101", tamper=True)
            with patch("four_mode_v2_third_rate_shadow.compare_race") as compare:
                output = audit(root)
            compare.assert_not_called()
            self.assertEqual(output["nonreproduced"], 1)
            self.assertEqual(output["paired_results"], 0)

    def test_reject_bad_model_inputs(self):
        board = probabilities(RATES)
        baseline = [x["combo"] for x in rank_modes(board)["hit"]["tickets"]]
        with self.assertRaises(ValueError):
            candidate(baseline, RATES[:3], board)
        with self.assertRaises(ValueError):
            candidate(baseline[:9] + [baseline[0]], RATES, board)
        with self.assertRaises(ValueError):
            candidate(baseline, RATES, board[:20])

    def test_no_results_cannot_claim_accuracy(self):
        with tempfile.TemporaryDirectory() as td:
            output = audit(td)
            self.assertEqual(output["status"], "no_forecast_directory")
            self.assertEqual(output["paired_results"], 0)


if __name__ == "__main__":
    unittest.main()

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from clean_four_modes import rank_modes
from research_model import probabilities
from four_mode_v2_protected_pair_shadow import audit, candidate, VERSION

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


class ProtectedPairShadowTests(unittest.TestCase):
    def test_top5_invariant_and_new_second_pairs_only_from_model(self):
        board = probabilities(RATES)
        baseline = [row["combo"] for row in rank_modes(board)["hit"]["tickets"]]
        alt, delta = candidate(baseline, board)
        self.assertEqual(alt[:5], baseline[:5])
        self.assertEqual(len(alt), 10)
        self.assertEqual(len(set(alt)), 10)
        self.assertGreaterEqual(delta, 0)
        self.assertTrue(set(alt).issubset({"-".join(map(str, boats)) for boats, _ in board}))

    def test_paired_and_missing_are_separate(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            save(root, "202611030101")
            save(root, "202611030102")
            def compared(code, root):
                return ({"status": "result_unavailable"} if code.endswith("02")
                        else {"status": "historical_comparison_only",
                              "winning_ticket": "2-1-3"})
            with patch("four_mode_v2_protected_pair_shadow.compare_race",
                       side_effect=compared):
                out = audit(root)
            self.assertEqual(out["reproduced_forecasts"], 2)
            self.assertEqual(out["paired_results"], 1)
            self.assertEqual(out["missing_results"], 1)
            self.assertEqual(out["by_date"]["20261103"]["paired"], 1)
            for n in (3, 5, 10):
                v = out["topn"][f"top{n}"]
                self.assertEqual(v["candidate"] - v["baseline"],
                                 v["gained"] - v["lost"])
            self.assertEqual(out["topn"]["top3"]["baseline"],
                             out["topn"]["top3"]["candidate"])
            self.assertEqual(out["topn"]["top5"]["baseline"],
                             out["topn"]["top5"]["candidate"])
            self.assertFalse(out["independent_holdout_verified"])

    def test_invalid_or_unreproducible_not_scored(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            save(root, "202611030101", tamper=True)
            with patch("four_mode_v2_protected_pair_shadow.compare_race") as compared:
                out = audit(root)
            compared.assert_not_called()
            self.assertEqual(out["nonreproduced"], 1)
            self.assertEqual(out["paired_results"], 0)

    def test_reject_bad_baseline_and_probabilities(self):
        board = probabilities(RATES)
        baseline = [row["combo"] for row in rank_modes(board)["hit"]["tickets"]]
        with self.assertRaises(ValueError):
            candidate(baseline[:9] + [baseline[0]], board)
        with self.assertRaises(ValueError):
            candidate(baseline, board[:30])

    def test_no_archive_does_not_claim_hit_rate(self):
        with tempfile.TemporaryDirectory() as td:
            output = audit(td)
            self.assertEqual(output["status"], "no_forecast_directory")
            self.assertEqual(output["paired_results"], 0)


if __name__ == "__main__":
    unittest.main()

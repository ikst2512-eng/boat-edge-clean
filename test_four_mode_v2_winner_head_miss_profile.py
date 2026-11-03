import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from clean_four_modes import rank_modes
from research_model import probabilities
from four_mode_v2_winner_head_miss_profile import audit, VERSION

RATES = [3.8, 6.4, 5.3, 4.8, 5.2, 5.5]


def save(root, code, rates=RATES, tamper=False):
    folder = root / "four_mode_forecasts"
    folder.mkdir(exist_ok=True)
    modes = rank_modes(probabilities(rates))
    if tamper:
        modes["hit"]["tickets"][0]["p"] += 0.1
    record = {
        "schema": "CLEAN_FOUR_MODES_PREDEADLINE_V1",
        "race_code": code,
        "model_version": VERSION,
        "input_national_win_rates": rates,
        "generated_at_jst": "2026-11-03T08:00:00+09:00",
        "deadline_jst": "2026-11-03T12:00:00+09:00",
        "modes": modes,
    }
    (folder / (code + ".json")).write_text(json.dumps(record))


class WinnerHeadMissProfileTests(unittest.TestCase):
    def test_all_six_heads_reconcile_to_valid_same_race_results(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            for n in range(1, 7):
                save(root, f"2026110301{n:02d}")
            def result(code, root):
                head = int(code[-2:])
                rest = [str(x) for x in range(1, 7) if x != head]
                return {"status": "historical_comparison_only",
                        "winning_ticket": f"{head}-{rest[0]}-{rest[1]}"}
            with patch("four_mode_v2_winner_head_miss_profile.compare_race",
                       side_effect=result):
                out = audit(root)
            self.assertEqual(out["matched_confirmed"], 6)
            for row in out["by_mode"].values():
                self.assertEqual(row["matched"], 6)
                self.assertEqual(row["head_absent"] + row["head_present"], 6)
                self.assertEqual(sum(row["head_absent_winner_rate_rank"].values()),
                                 row["head_absent"])
                self.assertEqual(sum(row["head_absent_winner_model_rank"].values()),
                                 row["head_absent"])
                self.assertEqual(sum(row["head_absent_winner_boat"].values()),
                                 row["head_absent"])
            self.assertFalse(out["formal"])
            self.assertFalse(out["independent_first_publication_verified"])

    def test_missing_untrusted_and_nonreproducible_not_scored(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            save(root, "202611030101")
            save(root, "202611030102")
            save(root, "202611030103", tamper=True)
            def result(code, root):
                if code.endswith("01"):
                    return {"status": "result_unavailable"}
                return {"status": "invalid_result_or_timing"}
            with patch("four_mode_v2_winner_head_miss_profile.compare_race",
                       side_effect=result) as compared:
                out = audit(root)
            self.assertEqual(out["matched_confirmed"], 0)
            self.assertEqual(out["missing"], 1)
            self.assertEqual(out["nonreproduced"], 1)
            self.assertEqual(out["invalid"], 1)
            self.assertEqual(compared.call_count, 2)
            self.assertIsNone(out["by_mode"]["hit"]["head_absent_winner_probability_mean"])

    def test_actual_head_absence_and_balance_rescue_not_inferred(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            save(root, "202611030101", rates=[5.0, 7.5, 6.1, 3.0, 4.5, 5.2])
            with patch("four_mode_v2_winner_head_miss_profile.compare_race",
                       return_value={"status": "historical_comparison_only",
                                     "winning_ticket": "3-1-2"}):
                out = audit(root)
            hit = out["by_mode"]["hit"]
            self.assertEqual(hit["matched"], 1)
            self.assertEqual(hit["head_absent"] + hit["head_present"], 1)
            if hit["head_absent"]:
                self.assertEqual(sum(hit["head_absent_winner_rate_rank"].values()), 1)
            self.assertLessEqual(out["hit_head_absent_balance_full_ticket_hit"],
                                 out["hit_head_absent_balance_head_present"])

    def test_empty_folder_is_not_zero_percent_accuracy(self):
        with tempfile.TemporaryDirectory() as td:
            out = audit(td)
            self.assertEqual(out["status"], "no_forecast_directory")
            self.assertEqual(out["matched_confirmed"], 0)
            self.assertIsNone(out["by_mode"]["hit"]["head_absent_winner_probability_mean"])


if __name__ == "__main__":
    unittest.main()

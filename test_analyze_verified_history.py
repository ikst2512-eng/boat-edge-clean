import json
import tempfile
import unittest
from pathlib import Path
from analyze_verified_history import diagnose

class DiagnosticsTests(unittest.TestCase):
    def test_verified_rank_miss_and_payout_bands(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            folder = root / "four_mode_forecasts"
            folder.mkdir()
            modes = ("hit", "balance", "hole", "narrow")
            examples = [
                ("202610280101", "1-2-3", ["1-2-3", "1-3-2"], 900, True, 4500),
                ("202610280102", "1-2-4", ["1-2-3", "1-3-2"], 2000, False, 0),
                ("202610280103", "2-3-4", ["1-2-3", "1-3-2"], 12000, False, 0),
            ]
            races = []
            for code, finish, tickets, payout, hit, returned in examples:
                archive = {"race_code": code, "modes": {m: {"tickets": tickets} for m in modes}}
                (folder / (code + ".json")).write_text(json.dumps(archive), encoding="utf-8")
                races.append({"race_code": code, "finish": finish,
                              "payout_per_100_yen": payout,
                              "modes": {m: {"hit": hit, "return_yen": returned,
                                             "invested_yen": 5000} for m in modes}})
            report = diagnose({"schema": "CLEAN_VERIFIED_FOUR_MODE_HISTORY_V1",
                               "budget_yen": 5000, "races": races}, root)
            one = report["modes"]["hit"]
            self.assertEqual(one["hit_rank_counts"], {"1": 1})
            self.assertEqual(one["miss_types"], {"third_only_missing": 1, "first_missing": 1})
            self.assertEqual(one["third_only_missing_boats"], {"4": 1})
            self.assertEqual(one["missed_winner_first_boats"], {"1": 1, "2": 1})
            self.assertEqual(one["miss_examples"]["third_only_missing"][0]["actual_finish"], "1-2-4")
            self.assertEqual(one["payout_bands"]["under_1000"]["roi_pct"], 90)
            self.assertEqual(one["top_three_return_share_pct"], 100)
            races[0]["modes"]["hit"]["hit"] = False
            with self.assertRaisesRegex(ValueError, "history_and_archive_disagree"):
                diagnose({"schema": "CLEAN_VERIFIED_FOUR_MODE_HISTORY_V1",
                          "budget_yen": 5000, "races": races}, root)

if __name__ == "__main__":
    unittest.main()

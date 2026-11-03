import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from four_mode_top3_disagreement_cases import cases

class DisagreementTests(unittest.TestCase):
    def test_only_actual_disagreement_and_no_prospective_claim(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            folder = root / "four_mode_forecasts"
            folder.mkdir()
            code = "202610280101"
            (folder / (code + ".json")).write_text(json.dumps({
                "race_code": code, "model_version": "CLEAN_FOUR_MODES_V1_UNCALIBRATED",
                "input_national_win_rates": [5.0]*6,
                "modes": {"hit": {"tickets": [{"combo": "1-2-3"}]*3},
                          "balance": {"tickets": [{"combo": "2-1-3"}]*3}}
            }), encoding="utf-8")
            def compare(code, root):
                return {"status":"historical_comparison_only","winning_ticket":"2-1-3",
                        "modes":{"hit":{"top3":False,"winning_rank":None},
                                 "balance":{"top3":True,"winning_rank":1}}}
            with patch("four_mode_top3_disagreement_cases.compare_race", side_effect=compare):
                report = cases(root)
            self.assertEqual(report["by_day"]["20261028"]["balance"], 1)
            self.assertEqual(len(report["disagreement_cases"]), 1)
            self.assertFalse(report["formal"])
            self.assertFalse(report["independent_holdout"])

if __name__ == "__main__":
    unittest.main()

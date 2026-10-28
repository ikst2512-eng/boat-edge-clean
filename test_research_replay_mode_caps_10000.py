import json
import tempfile
import unittest
from pathlib import Path
from research_model import probabilities
from research_four_mode_roles import research_modes
from research_replay_mode_caps_10000 import replay

class HistoricalCapReplayTests(unittest.TestCase):
    def test_verified_sample_and_hole_exclusion(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            (root/"four_mode_forecasts").mkdir()
            code="202610280101"
            rates=[6.2,5.1,4.2,4.5,3.1,2.9]
            winner="-".join(map(str,probabilities(rates)[0][0]))
            original={"hit","balance","hole","narrow"}
            original_modes={m:{"tickets":[{"combo":winner}]} for m in original}
            (root/"four_mode_forecasts"/(code+".json")).write_text(json.dumps({
                "race_code":code,"schema":"CLEAN_FOUR_MODES_PREDEADLINE_V1",
                "input_national_win_rates":rates,"modes":original_modes}),encoding="utf-8")
            record={"race_code":code,"finish":winner,"payout_per_100_yen":1200,
                    "modes":{m:{"hit":True,"return_yen":120000} for m in original}}
            history={"schema":"CLEAN_VERIFIED_FOUR_MODE_HISTORY_V1","budget_yen":10000,"races":[record]}
            result=replay(history,root)
            self.assertEqual(result["modes"]["hit"]["hits"],1)
            self.assertEqual(result["modes"]["hit"]["return_yen"],12000)
            self.assertEqual(result["modes"]["balance"]["invested_yen"],10000)
            self.assertIsNone(result["modes"]["hole"]["hits"])
            self.assertFalse(result["prospectively_validated"])
            history["races"][0]["modes"]["hit"]["return_yen"]=0
            with self.assertRaisesRegex(ValueError,"baseline_reconciliation_failed"):
                replay(history,root)
            history["races"][0]["modes"]["hit"]["return_yen"]=120000
            history["races"].append(record)
            with self.assertRaisesRegex(ValueError,"duplicate_races"):
                replay(history,root)

if __name__=="__main__": unittest.main()

import json
import tempfile
import unittest
from pathlib import Path
from research_model import probabilities
from research_compare_hit12_branches import candidates, replay

class BranchHitTests(unittest.TestCase):
    def test_no_future_information_and_twelve_unique_picks(self):
        rates=[6.2,5.1,4.2,4.5,3.1,2.9]
        selections={p:candidates(rates,p) for p in ("probability","branch_diversity","third_diversity")}
        for picks in selections.values():
            self.assertEqual(len(picks),12)
            self.assertEqual(len(set(picks)),12)
        self.assertEqual(selections["probability"][0],"-".join(map(str,probabilities(rates)[0][0])))
        with self.assertRaises(ValueError):candidates(rates,"oracle")
    def test_verified_reconciliation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            (root/"four_mode_forecasts").mkdir()
            code="202610280101"
            rates=[6.2,5.1,4.2,4.5,3.1,2.9]
            winner=candidates(rates)[0]
            original={"race_code":code,"schema":"CLEAN_FOUR_MODES_PREDEADLINE_V1",
                      "input_national_win_rates":rates,"modes":{"hit":{"tickets":[{"combo":winner}]}}}
            (root/"four_mode_forecasts"/(code+".json")).write_text(json.dumps(original),encoding="utf-8")
            race={"race_code":code,"finish":winner,"payout_per_100_yen":1200,
                  "modes":{"hit":{"hit":True,"return_yen":120000}}}
            history={"schema":"CLEAN_VERIFIED_FOUR_MODE_HISTORY_V1","budget_yen":10000,"races":[race]}
            result=replay(history,root)
            self.assertEqual(result["policies"]["probability"]["hits"],1)
            self.assertFalse(result["prospectively_validated"])
            race["modes"]["hit"]["return_yen"]=0
            with self.assertRaisesRegex(ValueError,"original_settlement_mismatch"):
                replay(history,root)

if __name__=="__main__":unittest.main()

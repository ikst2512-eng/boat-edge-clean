import json
import tempfile
import unittest
from pathlib import Path
from research_selective_hole20 import confidence,compare,THRESHOLDS
from research_compare_hole20_heads_odds_free import tickets_under_heads

class SelectiveTests(unittest.TestCase):
    def test_predeclared_thresholds_and_probability_score(self):
        rates=[6.2,5.1,4.2,4.5,3.1,2.9]
        self.assertEqual(THRESHOLDS,(0.30,0.40,0.50,0.60,0.70))
        self.assertGreater(confidence(rates),0)
        self.assertLess(confidence(rates),1)
    def test_no_bet_has_no_fake_roi_and_original_archive_guard(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            folder=root/"four_mode_forecasts"
            folder.mkdir()
            code="202610280101"
            rates=[6.2,5.1,4.2,4.5,3.1,2.9]
            winner=tickets_under_heads(rates,2)[0]
            (folder/(code+".json")).write_text(json.dumps({
                "schema":"CLEAN_FOUR_MODES_PREDEADLINE_V1",
                "race_code":code,"input_national_win_rates":rates,
                "modes":{"hole":{"tickets":[{"combo":winner}]}}}),encoding="utf-8")
            record={"race_code":code,"finish":winner,"payout_per_100_yen":1200,
                    "modes":{"hole":{"hit":True,"return_yen":120000}}}
            history={"schema":"CLEAN_VERIFIED_FOUR_MODE_HISTORY_V1",
                     "budget_yen":10000,"races":[record]}
            result=compare(history,root)
            self.assertEqual(result["all_races"]["hits"],1)
            self.assertEqual(result["all_races"]["spent_yen"],10000)
            self.assertEqual(result["all_races"]["returned_yen"],6000)
            for stat in result["thresholds"].values():
                if stat["purchased"]==0:
                    self.assertIsNone(stat["roi_pct"])
                    self.assertEqual(stat["spent_yen"],0)
            record["modes"]["hole"]["return_yen"]=0
            with self.assertRaisesRegex(ValueError,"official_archive_reconciliation_failed"):
                compare(history,root)
            record["modes"]["hole"]["return_yen"]=120000
            history["races"].append(record)
            with self.assertRaisesRegex(ValueError,"duplicate_race"):
                compare(history,root)

if __name__=="__main__":unittest.main()

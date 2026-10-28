import json
import tempfile
import unittest
from pathlib import Path
from research_compare_hole20_heads_odds_free import tickets_under_heads,compare

class Hole20SensitivityTests(unittest.TestCase):
    def test_exactly_twenty_unique_tickets_and_head_limit(self):
        rates=[6.2,5.1,4.2,4.5,3.1,2.9]
        for n in (1,2,3):
            picks=tickets_under_heads(rates,n)
            self.assertEqual(len(picks),20)
            self.assertEqual(len(set(picks)),20)
            self.assertLessEqual(len({c[0] for c in picks}),n)
            if n==1:
                head=picks[0][0]
                self.assertEqual({c for c in picks},
                                 {f"{head}-{second}-{third}" for second in "123456" for third in "123456"
                                  if len({head,second,third})==3})
        with self.assertRaises(ValueError):
            tickets_under_heads(rates,4)
    def test_verified_settlement_guard(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            folder=root/"four_mode_forecasts"
            folder.mkdir()
            code="202610280101"
            rates=[6.2,5.1,4.2,4.5,3.1,2.9]
            winner=tickets_under_heads(rates,3)[0]
            archive={"schema":"CLEAN_FOUR_MODES_PREDEADLINE_V1","race_code":code,
                     "input_national_win_rates":rates,
                     "modes":{"hole":{"tickets":[{"combo":winner}]}}}
            (folder/(code+".json")).write_text(json.dumps(archive))
            race={"race_code":code,"finish":winner,"payout_per_100_yen":1200,
                  "modes":{"hole":{"hit":True,"return_yen":120000}}}
            history={"schema":"CLEAN_VERIFIED_FOUR_MODE_HISTORY_V1",
                     "budget_yen":10000,"races":[race]}
            result=compare(history,root)
            self.assertFalse(result["odds_based_hole_evaluated"])
            self.assertEqual(result["head_variants"]["3"]["hits"],1)
            self.assertEqual(result["head_variants"]["1"]["hits"],result["head_variants"]["1"]["head_captured"])
            race["modes"]["hole"]["return_yen"]=0
            with self.assertRaisesRegex(ValueError,"original_hole_settlement_mismatch"):
                compare(history,root)

if __name__=="__main__":unittest.main()

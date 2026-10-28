import unittest
import json
import tempfile
from pathlib import Path
from research_compare_hit12_stakes import weights,compare
from four_mode_performance import allocate
class StakeTests(unittest.TestCase):
    def test_fixed_budget_all_tickets_covered(self):
        tickets=[{"combo":c} for c in ("1-2-3","1-2-4","1-2-5","1-2-6","1-3-2","1-3-4","1-3-5","1-3-6","1-4-2","1-4-3","1-4-5","1-4-6")]
        for n in (3,5):
            w=weights(tickets,n)
            self.assertEqual(sum(w.values()),10000)
            self.assertEqual(len(w),12)
            self.assertTrue(all(x>=100 and x%100==0 for x in w.values()))
            self.assertGreater(w["1-2-3"],w["1-4-6"])
        self.assertEqual(sum(allocate(tickets,10000).values()),10000)
    def test_history_reconciliation(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            folder=root/"four_mode_forecasts"
            folder.mkdir()
            code="202610280101"
            picks=[{"combo":"1-2-3"},{"combo":"1-2-4"}]
            (folder/(code+".json")).write_text(json.dumps({"race_code":code,"schema":"CLEAN_FOUR_MODES_PREDEADLINE_V1","modes":{"hit":{"tickets":picks}}}))
            row={"race_code":code,"finish":"1-2-3","payout_per_100_yen":1200,"modes":{"hit":{"hit":True,"return_yen":60000}}}
            history={"schema":"CLEAN_VERIFIED_FOUR_MODE_HISTORY_V1","budget_yen":10000,"races":[row]}
            result=compare(history,root)
            self.assertEqual(result["policies"]["equal"]["return_yen"],60000)
            self.assertEqual(result["policies"]["top3_double"]["hits"],1)
            row["modes"]["hit"]["return_yen"]=100
            with self.assertRaisesRegex(ValueError,"original_settlement_mismatch"):
                compare(history,root)
if __name__=="__main__":unittest.main()

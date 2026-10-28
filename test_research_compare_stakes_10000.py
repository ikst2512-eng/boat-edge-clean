import json
import tempfile
import unittest
from pathlib import Path
from research_compare_stakes_10000 import weighted_stakes, compare
from four_mode_performance import allocate

class CompareStakesTests(unittest.TestCase):
    def test_fixed_budget_and_coverage(self):
        tickets = [{"combo": f"1-2-{x}"} for x in (3,4,5,6)]
        for n in (3,5):
            stakes = weighted_stakes(tickets,n,2)
            self.assertEqual(sum(stakes.values()),10000)
            self.assertEqual(len(stakes),4)
            self.assertTrue(all(v >= 100 and v % 100 == 0 for v in stakes.values()))
            self.assertGreater(stakes["1-2-3"], stakes["1-2-6"] if n == 3 else 0)
    def test_verified_baseline_and_mismatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root/"four_mode_forecasts").mkdir()
            code = "202610280101"
            tickets = [{"combo":"1-2-3"},{"combo":"1-3-2"},{"combo":"2-1-3"},{"combo":"3-1-2"}]
            archive={"race_code":code,"modes":{"hit":{"tickets":tickets}}}
            (root/"four_mode_forecasts"/(code+".json")).write_text(json.dumps(archive))
            base=allocate(tickets,10000)
            history={"schema":"CLEAN_VERIFIED_FOUR_MODE_HISTORY_V1","budget_yen":10000,
                     "races":[{"race_code":code,"finish":"1-2-3","payout_per_100_yen":1000,
                               "modes":{"hit":{"hit":True,"return_yen":base["1-2-3"]*10}}}]}
            out=compare(history,root)
            self.assertEqual(out["policies"]["baseline"]["return_yen"],25000)
            self.assertEqual(out["policies"]["baseline"]["hits"],1)
            self.assertFalse(out["prospectively_validated"])
            history["races"][0]["modes"]["hit"]["return_yen"]=0
            with self.assertRaisesRegex(ValueError,"history_payout_mismatch"): compare(history,root)

if __name__=="__main__":
    unittest.main()

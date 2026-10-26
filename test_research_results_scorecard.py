import unittest
from research_results_scorecard import _actual, score

class ScorecardTests(unittest.TestCase):
    def test_result_ticket(self):
        row={"1着_艇番":"2","2着_艇番":"1","3着_艇番":"5"}
        self.assertEqual(_actual(row),"2-1-5")
        row["3着_艇番"]="2"
        self.assertIsNone(_actual(row))
    def test_retrospective_baseline_only(self):
        snapshot={"race_code":"202610231201","predictions":["2-1-5","1-2-3","1-2-4","1-2-5",
                       "1-2-6","1-3-2","1-3-4","1-3-5","1-3-6","1-4-2"]}
        actual={"ticket":"2-1-5","method":"まくり",
                "entry":["2","1","3","4","5","6"]}
        r=score([snapshot],{"20261023":{"202610231201":actual}})
        self.assertEqual(r["counts"]["top1_hits"],1)
        self.assertEqual(r["counts"]["postrace_entry_changed"],1)
        self.assertEqual(r["candidate_scored"],0)
        self.assertEqual(r["prospective_verified"],0)
    def test_missing_is_not_loss(self):
        r=score([{"race_code":"202610231201","predictions":["1-2-3"]*10}],{})
        self.assertEqual(r["counts"]["missing_result"],1)
        self.assertIsNone(r["top_rates"]["1"])
if __name__=="__main__":
    unittest.main()

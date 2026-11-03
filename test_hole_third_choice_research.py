import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from hole_third_choice_research import variants,compare,national_rates

CODE="202611030101"
def archive():
    base=["1-2-3","1-3-4","1-2-4","1-3-5","1-4-2",
          "1-4-3","1-4-5","1-2-5","1-3-2","1-2-6"]
    return {"modes":{
        "hole":{"tickets":[{"combo":t,"p":1} for t in base]},
        "hit":{"tickets":[{"combo":t,"p":p} for t,p in [
            ("1-5-2",1),("1-5-3",6),("1-6-2",1),("1-6-3",5)]]},
        "balance":{"tickets":[{"combo":"1-5-4","p":2}]}}}
class ThirdChoiceTest(unittest.TestCase):
    def setUp(self):
        self.t=tempfile.TemporaryDirectory();self.addCleanup(self.t.cleanup)
        self.root=Path(self.t.name)
        (self.root/"four_mode_forecasts").mkdir()
        (self.root/"four_mode_forecasts"/(CODE+".json")).write_text(
          json.dumps({"input_national_win_rates":[5,3,8,7,6,1]}))
    def test_score_choice_uses_same_two_pairs_and_keeps_top5(self):
        v=variants(archive(),[5,3,8,7,6,1])
        self.assertEqual(v["donor_order"][5:7],["1-5-2","1-6-2"])
        self.assertEqual(v["max_ticket_score"][5:7],["1-5-3","1-6-3"])
        self.assertEqual(v["third_national_rate"][5:7],["1-5-3","1-6-3"])
        for t in v.values():
            self.assertEqual(t[:5],v["baseline"][:5])
            self.assertEqual(len(t),10)
            self.assertEqual(len(set(t)),10)
    def test_wrong_third_can_be_corrected_and_counted(self):
        with patch("hole_third_choice_research.archived_four_modes",return_value=(200,archive())),patch(
             "hole_third_choice_research.compare_race",
             return_value={"status":"historical_comparison_only","winning_ticket":"1-6-3"}):
            result=compare([CODE],self.root)
        self.assertEqual(result["third_choice_diagnostic"]["selected_correct_pair"],1)
        self.assertEqual(result["third_choice_diagnostic"]["correct_pair_wrong_third"],1)
        self.assertEqual(result["third_choice_diagnostic"]["correct_third_available_in_donors"],1)
        self.assertEqual(result["topn"]["max_ticket_score"]["top10"]["gained"],1)
        self.assertEqual(result["topn"]["donor_order"]["top10"]["gained"],0)
    def test_missing_rates_not_fabricated(self):
        (self.root/"four_mode_forecasts"/(CODE+".json")).write_text("{}")
        self.assertIsNone(national_rates(CODE,self.root))
        self.assertEqual(variants(archive(),None)["third_national_rate"],
                         variants(archive(),None)["max_ticket_score"])
    def test_invalid_rates_rejected(self):
        (self.root/"four_mode_forecasts"/(CODE+".json")).write_text(
          json.dumps({"input_national_win_rates":[1,2]}))
        with self.assertRaises(ValueError):national_rates(CODE,self.root)
if __name__=="__main__":unittest.main()

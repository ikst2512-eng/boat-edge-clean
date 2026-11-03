import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from hole_second_pair_evidence_research import extract_features,classify,audit_codes

CODE="202611030101"

def make_archive():
    base=["1-2-3","1-3-4","1-2-4","1-3-5","1-4-2",
          "1-4-3","1-4-5","1-2-5","1-3-2","1-2-6"]
    return {"modes":{
        "hole":{"tickets":[{"combo":t,"p":1.0} for t in base]},
        "hit":{"tickets":[{"combo":"1-5-2","p":2.0},
                          {"combo":"1-5-3","p":1.8}]},
        "balance":{"tickets":[{"combo":"1-5-2","p":2.0},
                              {"combo":"1-5-4","p":1.5}]}}}

class PairEvidenceTest(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        (self.root/"four_mode_forecasts").mkdir()
        self.path=self.root/"four_mode_forecasts"/(CODE+".json")
        self.path.write_text(json.dumps({"input_national_win_rates":[4,5,6,7,8,9]}))
        self.archive=make_archive()

    def test_distinguishes_pair_present_but_wrong_third(self):
        f=extract_features(CODE,self.root,self.archive)
        result=classify(f,"1-5-4")
        self.assertEqual(result["miss_class"],"winner_second_pair_absent")
        self.assertEqual(result["pair_state"],"correct_pair_in_hit_and_balance")
        self.assertTrue(result["selected_pair_matches_winner"])
        self.assertEqual(result["winning_pair_rank_in_hit"],1)
        self.assertEqual(result["winning_second_national_win_rate"],8)

    def test_absent_from_donor(self):
        f=extract_features(CODE,self.root,self.archive)
        result=classify(f,"1-6-3")
        self.assertEqual(result["pair_state"],"correct_pair_not_in_donors")
        self.assertFalse(result["selected_pair_matches_winner"])

    def test_no_outcome_or_result_leakage_from_features(self):
        with patch("hole_second_pair_evidence_research.compare_race",
                   side_effect=AssertionError("outcome must not be read")):
            f=extract_features(CODE,self.root,self.archive)
        self.assertEqual(len(f["national_rates"]),6)
        self.assertTrue(f["top5_preserved"])

    def test_unsupported_rates_fail(self):
        self.path.write_text(json.dumps({"input_national_win_rates":[4,5,6]}))
        with self.assertRaises(ValueError):
            extract_features(CODE,self.root,self.archive)

    def test_aggregate_missing_results_explicitly(self):
        with patch("hole_second_pair_evidence_research.archived_four_modes",
                   return_value=(200,self.archive)),patch(
                   "hole_second_pair_evidence_research.compare_race",
                   return_value={"status":"result_unavailable"}):
            output=audit_codes([CODE],self.root)
        self.assertEqual(output["compared"],0)
        self.assertEqual(output["missing_by_reason"]["result_unavailable"],1)

if __name__=="__main__":
    unittest.main()

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import evaluate_clean_prospective as ev

class ProspectiveEvaluationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        (self.root/"prospective_predictions").mkdir()
        self.code="202610281201"
        self.tickets=["1-2-3","1-2-4","1-3-2","1-3-4","1-4-2",
                      "1-4-3","2-1-3","2-1-4","2-3-1","2-3-4"]
        (self.root/"prospective_predictions"/(self.code+".json")).write_text(json.dumps({"predictions":self.tickets}),encoding="utf-8")
    def test_verified_result_and_cutoff_evidence_only(self):
        with patch.object(ev,"inspect",return_value={"first_add_sha":"a"*40}) as verify, patch.object(ev,"read_result",return_value=(200,{"race_code":self.code,"status":"confirmed","finish_order":[1,4,2]})):
            result=ev.evaluate(self.code,self.root)
        self.assertTrue(result["top5"])
        self.assertFalse(result["top3"])
        self.assertTrue(result["top10"])
        self.assertFalse(result["formal"])
        verify.assert_called_once()
    def test_missing_result_is_not_a_miss(self):
        with patch.object(ev,"inspect",return_value={"first_add_sha":"a"*40}),patch.object(ev,"read_result",return_value=(404,{"status":"not_confirmed"})):
            result=ev.evaluate(self.code,self.root)
        self.assertEqual(result["status"],"result_unavailable")
        self.assertNotIn("top3",result)
    def test_unaudited_candidate_never_scores(self):
        with patch.object(ev,"inspect",side_effect=ValueError("late commit")):
            with self.assertRaises(ValueError):
                ev.evaluate(self.code,self.root)
if __name__=="__main__":
    unittest.main()

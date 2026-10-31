import json
import tempfile
import unittest
from pathlib import Path
from audit_payout_coverage import coverage

class Tests(unittest.TestCase):
 def test_gap_is_not_fake_zero_roi(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);folder=root/"confirmed_results";folder.mkdir()
   code="202610310101"
   (folder/(code+".json")).write_text(json.dumps({"race_code":code,"status":"confirmed","finish_order":[1,2,3]}))
   report=coverage("20261031",root)
   self.assertEqual((report["payout_verified"],report["payout_missing_or_mismatched"]),(0,1))
   self.assertFalse(report["roi_ready"])
 def test_matches_verified_payout_with_correct_finish(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);folder=root/"confirmed_results";folder.mkdir()
   code="202610310101"
   (folder/(code+".json")).write_text(json.dumps({"race_code":code,"status":"confirmed","finish_order":[1,2,3]}))
   proof=root/"four_mode_performance"/"verified_races";proof.mkdir(parents=True)
   (proof/(code+".json")).write_text(json.dumps({"race_code":code,"schema":"CLEAN_VERIFIED_FOUR_MODE_RACE_V1","verified":True,"simulated_only":True,"official_finish":"1-2-3","official_payout_yen_per_100":1400}))
   self.assertEqual(coverage("20261031",root)["payout_verified"],1)
 def test_invalid_file_not_marked_missing_payout(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);folder=root/"confirmed_results";folder.mkdir()
   (folder/"202610310101.json").write_text(json.dumps({"race_code":"202610310102","status":"confirmed","finish_order":[1,2,3]}))
   x=coverage("20261031",root)
   self.assertEqual(x["invalid_result_files"],1)
   self.assertEqual(x["payout_missing_or_mismatched"],0)
if __name__=="__main__":unittest.main()

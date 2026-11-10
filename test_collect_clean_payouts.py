import json
import tempfile
import unittest
from pathlib import Path
from collect_clean_payouts import parse

class Tests(unittest.TestCase):
 def test_matches_confirmed_result_only(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);(root/"confirmed_results").mkdir()
   code="202610310101"
   (root/"confirmed_results"/(code+".json")).write_text(json.dumps({"race_code":code,"status":"confirmed","finish_order":[1,2,3],"source_sha256":"abc"}))
   data=("レースコード,3連単_組番,3連単_払戻金\n"+code+",1-2-3,\"1,250\"\n"+"202610310102,3-2-1,1000\n").encode()
   rows=parse("20261031",data,root)
   self.assertEqual(set(rows),{code})
   self.assertEqual(rows[code]["payout_yen_per_100"],1250)
   self.assertTrue(rows[code]["verified_against_confirmed_finish"])
 def test_mismatch_does_not_create_evidence(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);(root/"confirmed_results").mkdir()
   code="202610310101"
   (root/"confirmed_results"/(code+".json")).write_text(json.dumps({"race_code":code,"status":"confirmed","finish_order":[1,2,3]}))
   self.assertEqual(parse("20261031",("レースコード,3連単_組番,3連単_払戻金\n"+code+",2-1-3,800\n").encode(),root),{})
 def test_duplicate_source_rejected(self):
  with tempfile.TemporaryDirectory() as tmp:
   code="202610310101"
   data=("レースコード,3連単_組番,3連単_払戻金\n"+code+",1-2-3,500\n"+code+",1-2-3,500\n").encode()
   with self.assertRaises(ValueError):parse("20261031",data,tmp)
if __name__=="__main__":unittest.main()

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
 def test_payout_rescue_reuses_only_trusted_main_result_collector(self):
  # Static workflow contract. Exact-head Actions must additionally validate
  # YAML parsing and the real job; this does NOT claim live payout ingestion.
  config=(Path(__file__).resolve().parent/".github/workflows/collect-clean-payouts.yml").read_text(encoding="utf-8")
  self.assertEqual(config.count("  workflow_run:"),1)
  self.assertIn("workflows: ['CLEAN independent confirmed result collection']",config)
  self.assertIn("types: [completed]",config)
  self.assertIn("github.event.workflow_run.head_branch == 'main'",config)
  self.assertIn("github.event.workflow_run.head_repository.full_name == github.repository",config)
  self.assertIn('["schedule","workflow_dispatch","push","workflow_run"]',config)
  self.assertIn("github.event_name != 'workflow_run'",config)
  self.assertEqual(config.count("- cron:"),1)
  self.assertIn("group: clean-payout-evidence-writer",config)
  self.assertIn("git diff --cached --name-only --diff-filter=CDMRTUX",config)
  self.assertIn("git rebase origin/main",config)
  self.assertIn("github.event_name != 'pull_request'",config)

if __name__=="__main__":unittest.main()

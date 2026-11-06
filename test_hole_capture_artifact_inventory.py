import io
import json
import unittest
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace
import zipfile
from hole_capture_artifact_inventory import inspect_capture,zip_shadow,gh_shadow
class CaptureInventoryTests(unittest.TestCase):
 def test_frozen_bundle_count(self):
  x={"records":[{"status":"shadow_frozen_unverified","shadow_bundle2":["1-2-3"]},
                {"status":"past_deadline"},{"status":"shadow_frozen_unverified"}]}
  self.assertEqual(inspect_capture(x)["bundle2"],1)
  self.assertEqual(inspect_capture(x)["frozen"],2)
 def test_zip_shadow(self):
  buf=io.BytesIO()
  with zipfile.ZipFile(buf,"w") as f:
   f.writestr("four-mode-evidence/hole-shadow.json",
      json.dumps({"status":"research_only_after_confirmed_push","records":[
       {"status":"shadow_frozen_unverified","shadow_bundle2":["1-2-3"]}]}))
  self.assertEqual(zip_shadow(buf.getvalue())["bundle2"],1)
 def test_missing_does_not_look_successful(self):
  buf=io.BytesIO()
  with zipfile.ZipFile(buf,"w") as f:f.writestr("foo.txt","none")
  self.assertEqual(zip_shadow(buf.getvalue())["status"],"no_hole_shadow_in_artifact")
 def test_future_locked_declared_not_verified(self):
  payload={"records":[{"status":"shadow_frozen_unverified",
      "future_locked_candidates":{p:["1-2-3"] for p in
      ("baseline","donor_order","max_ticket_score","third_national_rate")}},
      {"status":"past_deadline","future_locked_candidates":{}}]}
  self.assertEqual(inspect_capture(payload)["future_locked_declared"],1)
 def test_stage_failure_reason_from_real_extracted_artifact(self):
  def emulate_download(args,**kwargs):
   dest=Path(args[args.index("--dir")+1])/"four-mode-evidence"
   dest.mkdir(parents=True)
   (dest/"stages.json").write_text(json.dumps({"receipt_staging":"failure"}))
   (dest/"publication.json").write_text(json.dumps({"outcome":"failed","stage":"push_main"}))
   return SimpleNamespace(returncode=0)
  with patch("hole_capture_artifact_inventory.subprocess.run",side_effect=emulate_download):
   result=gh_shadow(123,"a/b","fake-token")
  self.assertEqual(result["stage_diagnosis"],"publication_pipeline_failed")
  self.assertEqual(result["status"],"no_hole_shadow_in_artifact")
  self.assertEqual(result["publication_outcome"],"failed")
 def test_valid_future_shadow_stage(self):
  def emulate_download(args,**kwargs):
   dest=Path(args[args.index("--dir")+1])/"four-mode-evidence"
   dest.mkdir(parents=True)
   (dest/"stages.json").write_text(json.dumps({"receipt_staging":"success"}))
   (dest/"publication.json").write_text(json.dumps({"outcome":"pushed_to_main"}))
   data={"status":"research_only_after_confirmed_push",
         "records":[{"status":"shadow_frozen_unverified",
         "race_code":"202611060101",
         "future_locked_candidates":{p:["1-2-3"] for p in
          ("baseline","donor_order","max_ticket_score","third_national_rate")}}]}
   (dest/"hole-shadow.json").write_text(json.dumps(data))
   return SimpleNamespace(returncode=0)
  with patch("hole_capture_artifact_inventory.subprocess.run",side_effect=emulate_download):
   result=gh_shadow(123,"a/b","fake-token")
  self.assertEqual(result["future_locked_declared"],1)
  self.assertEqual(result["stage_diagnosis"],"research_shadow_available_unverified")
  self.assertEqual(result["publication_outcome"],"pushed_to_main")
if __name__=="__main__":unittest.main()

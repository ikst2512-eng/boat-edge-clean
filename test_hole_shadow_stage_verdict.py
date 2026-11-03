import json
import tempfile
import unittest
from pathlib import Path
from hole_shadow_stage_verdict import classify,audit_directory
class VerdictTests(unittest.TestCase):
 def test_failed_staging_precedes_shadow(self):
  self.assertEqual(classify({"receipt_staging":"failure"},{"outcome":"failed"},None),"publication_pipeline_failed")
 def test_no_eligible(self):
  self.assertEqual(classify({"receipt_staging":"success"},{"outcome":"no_eligible_candidates"},None),"no_eligible_forecasts_published")
 def test_published_shadow_missing(self):
  self.assertEqual(classify({"receipt_staging":"success"},{"outcome":"pushed_to_main"},None),"missing_shadow_evidence")
 def test_shadow_unverified(self):
  self.assertEqual(classify({"receipt_staging":"success"},{"outcome":"pushed_to_main"},
      {"status":"research_only_after_confirmed_push","records":[{"race_code":"202611040101","status":"shadow_frozen_unverified"}]}),
      "research_shadow_available_unverified")
 def test_published_label_cannot_override_skipped_stage(self):
  shadow={"status":"research_only_after_confirmed_push",
          "records":[{"race_code":"202611040101","status":"shadow_frozen_unverified"}]}
  for stage in ("skipped","cancelled","unknown",None):
   with self.subTest(stage=stage):
    self.assertEqual(classify({"receipt_staging":stage},
                     {"outcome":"pushed_to_main"},shadow),
                     "publication_stage_not_successful")
 def test_bad_shadow_records_never_count_as_research_available(self):
  for records in ([None],[123],[{"status":"shadow_frozen_unverified"}],
                  [{"race_code":"202611040101","status":"wrong"}]):
   with self.subTest(records=records):
    self.assertEqual(classify({"receipt_staging":"success"},
                     {"outcome":"pushed_to_main"},
                     {"status":"research_only_after_confirmed_push",
                      "records":records}),"malformed_shadow_records")
 def test_successful_no_eligible_requires_successful_staging(self):
  self.assertEqual(classify({"receipt_staging":"skipped"},
                    {"outcome":"no_eligible_candidates"},None),
                    "publication_stage_not_successful")
  self.assertEqual(classify({"receipt_staging":"success"},
                    {"outcome":"no_eligible_candidates"},None),
                    "no_eligible_forecasts_published")
 def test_directory_failure(self):
  with tempfile.TemporaryDirectory() as x:
   p=Path(x)/"four-mode-evidence";p.mkdir()
   (p/"stages.json").write_text(json.dumps({"receipt_staging":"failure","source_capture":"success"}))
   (p/"publication.json").write_text(json.dumps({"outcome":"failed"}))
   r=audit_directory(x)
   self.assertEqual(r["status"],"publication_pipeline_failed")
   self.assertFalse(r["formal"])
if __name__=="__main__":unittest.main()

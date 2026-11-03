import json
import tempfile
import unittest
from pathlib import Path
from datetime import datetime,timezone,timedelta
from unittest.mock import patch
from hole_future_artifact_batch import aggregate,discover_full_days,collect_recent

CODE1="202611040101"
CODE2="202611040102"

class FutureBatchTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory()
  self.addCleanup(self.tmp.cleanup)
  self.root=Path(self.tmp.name)
  self.folder=self.root/"artifacts";self.folder.mkdir()
 def artifact(self,name,code):
  dest=self.folder/name/"four-mode-evidence"
  dest.mkdir(parents=True)
  path=dest/"hole-shadow.json"
  path.write_text(json.dumps({"status":"research_only_after_confirmed_push",
    "records":[{"race_code":code,"status":"shadow_frozen_unverified"}]}))
  return path
 def scored(self,code,baseline,improved):
  flags={"baseline":{"top3":False,"top5":False,"top10":baseline},
         "donor_order":{"top3":False,"top5":False,"top10":improved},
         "max_ticket_score":{"top3":False,"top5":False,"top10":improved},
         "third_national_rate":{"top3":False,"top5":False,"top10":improved}}
  return {"rows":[{"race_code":code,"flags":flags}],"excluded_by_reason":{}}
 def test_unique_future_shadows_only_and_delta(self):
  a=self.artifact("run1",CODE1)
  b=self.artifact("run2",CODE2)
  def scorer(root,path):
   return self.scored(CODE1,False,True) if path==a else self.scored(CODE2,True,False)
  with patch("hole_future_artifact_batch.audit",side_effect=scorer):
   output=aggregate(self.root,self.folder)
  self.assertEqual(output["comparable"],2)
  self.assertEqual(output["shadow_status_counts"],{"research_only_after_confirmed_push":2})
  self.assertEqual(output["hits"]["baseline"]["top10"],1)
  self.assertEqual(output["hits"]["third_national_rate"]["top10"],1)
  self.assertEqual(output["delta"]["third_national_rate"]["top10"],{"gained":1,"lost":1,"net":0})
  self.assertFalse(output["formal"])
  self.assertFalse(output["independent_first_receipt_verified"])
 def test_duplicate_code_quarantined(self):
  self.artifact("run1",CODE1)
  self.artifact("run2",CODE1)
  with patch("hole_future_artifact_batch.audit",return_value=self.scored(CODE1,False,True)):
   output=aggregate(self.root,self.folder)
  self.assertEqual(output["comparable"],0)
  self.assertEqual(output["duplicate_codes_quarantined"],[CODE1])
 def test_no_artifacts_does_not_invent_results(self):
  output=aggregate(self.root,self.folder)
  self.assertEqual(output["comparable"],0)
  self.assertEqual(output["status"],"no_verified_local_shadows_with_results")
 def test_invalid_shadow_separate_from_hits(self):
  path=self.folder/"run1"/"four-mode-evidence"
  path.mkdir(parents=True)
  (path/"hole-shadow.json").write_text("bad json")
  result=aggregate(self.root,self.folder)
  self.assertEqual(result["comparable"],0)
  self.assertEqual(result["invalid_artifacts"]["JSONDecodeError"],1)
 def test_no_publish_shadow_reported_separately(self):
  dest=self.folder/"run1"/"four-mode-evidence";dest.mkdir(parents=True)
  (dest/"hole-shadow.json").write_text(json.dumps({"status":"not_published","records":[]}))
  with patch("hole_future_artifact_batch.audit",return_value={"rows":[],"excluded_by_reason":{}}):
   result=aggregate(self.root,self.folder)
  self.assertEqual(result["shadow_status_counts"],{"not_published":1})
  self.assertEqual(result["comparable"],0)
 def test_prior_date_not_scored(self):
  self.artifact("run1","202611030101")
  with patch("hole_future_artifact_batch.audit",return_value={"rows":[],"excluded_by_reason":{"not_future_eligible":1}}):
   result=aggregate(self.root,self.folder)
  self.assertEqual(result["comparable"],0)
  self.assertEqual(result["excluded_by_reason"]["not_future_eligible"],1)

class FullDayListingTests(unittest.TestCase):
 def test_paginates_beyond_twenty_and_handles_jst_midnight(self):
  # 2026-11-02 15:30 UTC is already Nov 3 in Japan.
  first=[{"id":i,"event":"schedule","created_at":"2026-11-02T15:30:00Z"}
         for i in range(1,101)]
  second=[{"id":101,"event":"schedule","created_at":"2026-11-01T18:00:00Z"},
          {"id":102,"event":"schedule","created_at":"2026-10-30T01:00:00Z"},
          {"id":103,"event":"pull_request","created_at":"2026-11-02T18:00:00Z"}]
  with patch("hole_future_artifact_batch.api",side_effect=[
      json.dumps({"workflow_runs":first}).encode(),
      json.dumps({"workflow_runs":second}).encode()]) as api:
   found=discover_full_days("a/b","token",days=2,
          as_of_jst=datetime(2026,11,4,1,40,tzinfo=timezone(timedelta(hours=9))))
  self.assertEqual(len(found["candidates"]),101)
  self.assertTrue(found["listing_complete"])
  self.assertEqual(found["pages_fetched"],2)
  self.assertEqual(found["window_start_jst"],"2026-11-02")
  self.assertEqual(found["window_end_exclusive_jst"],"2026-11-04")
  self.assertIn("page=2",api.call_args_list[-1].args[0])
 def test_current_jst_day_is_not_complete(self):
  pages=[{"id":1,"event":"schedule","created_at":"2026-11-03T01:00:00Z"},
         {"id":2,"event":"schedule","created_at":"2026-11-02T16:00:00Z"}]
  with patch("hole_future_artifact_batch.api",
       return_value=json.dumps({"workflow_runs":pages}).encode()):
   found=discover_full_days("a/b","token",days=2,
     as_of_jst=datetime(2026,11,3,15,0,tzinfo=timezone(timedelta(hours=9))))
  self.assertEqual([r["id"] for r in found["candidates"]],[2])
 def test_duplicate_run_in_paginated_listing_fails(self):
  page=[{"id":1,"event":"schedule","created_at":"2026-11-02T16:00:00Z"}]
  a=page*100
  with patch("hole_future_artifact_batch.api",return_value=json.dumps({"workflow_runs":a}).encode()):
   with self.assertRaisesRegex(ValueError,"duplicate_run"):
    discover_full_days("a/b","token",days=2,
      as_of_jst=datetime(2026,11,4,tzinfo=timezone(timedelta(hours=9))))
 def test_days_limit(self):
  with self.assertRaises(ValueError):
   discover_full_days("a/b","token",days=4)
if __name__=="__main__":
 unittest.main()

import json
import tempfile
import unittest
from pathlib import Path
from datetime import datetime,timezone,timedelta
from unittest.mock import patch
from hole_future_artifact_batch import aggregate,discover_full_days,collect_recent,summarize_downloaded_runs,late_window_as_of

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
 def test_outside_day_in_same_capture_never_counts_as_hit(self):
  self.artifact("run1",CODE1)
  code_other_day="202611050101"
  def audit_result(root,path):
   return {"rows":[self.scored(CODE1,False,True)["rows"][0],
                   self.scored(code_other_day,True,False)["rows"][0]],
           "excluded_by_reason":{}}
  with patch("hole_future_artifact_batch.audit",side_effect=audit_result):
   result=aggregate(self.root,self.folder,"2026-11-04","2026-11-05")
  self.assertEqual(result["comparable"],1)
  self.assertEqual(result["race_codes"],[CODE1])
  self.assertEqual(result["hits"]["baseline"]["top10"],0)
  self.assertEqual(result["hits"]["third_national_rate"]["top10"],1)
  self.assertEqual(result["excluded_outside_race_day_window"],1)
  self.assertNotIn(code_other_day,result["observed_future_codes"])
 def test_next_day_record_must_not_corrupt_duplicate_quarantine(self):
  self.artifact("run1","202611050101")
  self.artifact("run2",CODE1)
  with patch("hole_future_artifact_batch.audit") as scorer:
   scorer.side_effect=[self.scored("202611050101",False,True),
                       self.scored(CODE1,False,True)]
   result=aggregate(self.root,self.folder,"2026-11-04","2026-11-05")
  self.assertEqual(result["comparable"],1)
  self.assertEqual(result["duplicate_codes_quarantined"],[])
  self.assertEqual(result["race_codes"],[CODE1])
 def test_invalid_or_incomplete_window_rejected(self):
  with self.assertRaisesRegex(ValueError,"incomplete_race_day_window"):
   aggregate(self.root,self.folder,"2026-11-04")
  with self.assertRaisesRegex(ValueError,"invalid_race_day_window"):
   aggregate(self.root,self.folder,"2026-11-05","2026-11-05")
 def test_boundary_day_exclusive_not_included(self):
  self.artifact("run1","202611050101")
  with patch("hole_future_artifact_batch.audit",return_value=self.scored("202611050101",False,True)):
   result=aggregate(self.root,self.folder,"2026-11-04","2026-11-05")
  self.assertEqual(result["comparable"],0)
  self.assertEqual(result["outside_race_day_codes"],["202611050101"])
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

def self_fake_flags():
 return {m:{"top3":False,"top5":False,"top10":m=="third_national_rate"}
         for m in ("baseline","donor_order","max_ticket_score","third_national_rate")}

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
         {"id":2,"event":"schedule","created_at":"2026-11-01T16:00:00Z"}]
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
 def test_empty_historical_capture_window_is_not_complete(self):
  with tempfile.TemporaryDirectory() as directory:
   discovery={"candidates":[],"listing_complete":True,"pages_fetched":1,
              "window_start_jst":"2026-10-12",
              "window_end_exclusive_jst":"2026-10-13"}
   with patch("hole_future_artifact_batch.discover_full_days",return_value=discovery):
    result=collect_recent(directory,"a/b","token",days=1)
  self.assertEqual(result["runs_inspected"],0)
  self.assertFalse(result["capture_window_complete"])
  self.assertEqual(result["repository_result_coverage"]["status"],"no_eligible_complete_days")
 def test_capture_lookback_recovers_nov3_run_for_nov4_race(self):
  now=datetime(2026,11,11,1,40,tzinfo=timezone(timedelta(hours=9)))
  target=late_window_as_of(now,7)
  page=[{"id":10,"event":"schedule","created_at":"2026-11-04T04:30:00Z"},
        {"id":11,"event":"schedule","created_at":"2026-11-03T06:30:00Z"},
        {"id":12,"event":"schedule","created_at":"2026-11-02T06:30:00Z"}]
  with patch("hole_future_artifact_batch.api",
             return_value=json.dumps({"workflow_runs":page}).encode()):
   found=discover_full_days("a/b","token",days=1,as_of_jst=target,
                            capture_lookback_days=1)
  self.assertEqual(found["window_start_jst"],"2026-11-04")
  self.assertEqual(found["window_end_exclusive_jst"],"2026-11-05")
  self.assertEqual(found["capture_window_start_jst"],"2026-11-03")
  self.assertEqual([r["id"] for r in found["candidates"]],[10,11])
 def test_capture_lookback_does_not_expand_scoring_window(self):
  with tempfile.TemporaryDirectory() as tmp:
   directory=Path(tmp)
   evidence=directory/"11"/"four-mode-evidence"
   evidence.mkdir(parents=True)
   (evidence/"hole-shadow.json").write_text(json.dumps({
     "status":"research_only_after_confirmed_push",
     "records":[{"race_code":CODE1,"status":"shadow_frozen_unverified"},
                {"race_code":"202611030101","status":"shadow_frozen_unverified"}]}))
   with patch("hole_future_artifact_batch.audit",return_value={
     "rows":[{"race_code":CODE1,"flags":self_fake_flags()},
             {"race_code":"202611030101","flags":self_fake_flags()}],
     "excluded_by_reason":{}}):
    scored=aggregate(tmp,directory,"2026-11-04","2026-11-05")
   self.assertEqual(scored["race_codes"],[CODE1])
   self.assertEqual(scored["comparable"],1)
 def test_invalid_capture_lookback_rejected(self):
  with self.assertRaisesRegex(ValueError,"invalid_capture_lookback"):
   discover_full_days("a/b","token",days=1,capture_lookback_days=2)
 def test_days_limit(self):
  with self.assertRaises(ValueError):
   discover_full_days("a/b","token",days=4)
class LateWindowBoundaryTests(unittest.TestCase):
 def test_seven_days_later_checks_original_race_day(self):
  now=datetime(2026,11,11,1,40,tzinfo=timezone(timedelta(hours=9)))
  shifted=late_window_as_of(now,7)
  self.assertEqual(shifted.date().isoformat(),"2026-11-05")
  self.assertEqual((shifted.date()-timedelta(days=1)).isoformat(),"2026-11-04")
 def test_twenty_one_days_later_checks_original_race_day(self):
  now=datetime(2026,11,25,1,40,tzinfo=timezone(timedelta(hours=9)))
  shifted=late_window_as_of(now,21)
  self.assertEqual(shifted.date().isoformat(),"2026-11-05")
  self.assertEqual((shifted.date()-timedelta(days=1)).isoformat(),"2026-11-04")
 def test_default_daily_window_remains_previous_two_completed_days(self):
  now=datetime(2026,11,11,1,40,tzinfo=timezone(timedelta(hours=9)))
  self.assertEqual(late_window_as_of(now,0,2),now)
 def test_no_naive_timestamp_or_invalid_lag(self):
  with self.assertRaises(ValueError):
   late_window_as_of(datetime(2026,11,11),7)
  with self.assertRaises(ValueError):
   late_window_as_of(datetime(2026,11,11,tzinfo=timezone.utc),7)
  with self.assertRaises(ValueError):
   late_window_as_of(datetime(2026,11,11,tzinfo=timezone(timedelta(hours=9))),29)
 def test_seven_day_window_from_real_discovery(self):
  now=datetime(2026,11,11,1,40,tzinfo=timezone(timedelta(hours=9)))
  ts=late_window_as_of(now,7)
  page=[{"id":42,"event":"schedule","created_at":"2026-11-04T04:30:00Z"}]
  with patch("hole_future_artifact_batch.api",
             return_value=json.dumps({"workflow_runs":page}).encode()):
   found=discover_full_days("a/b","token",days=1,as_of_jst=ts)
  self.assertEqual(found["window_start_jst"],"2026-11-04")
  self.assertEqual(found["window_end_exclusive_jst"],"2026-11-05")
  self.assertEqual([r["id"] for r in found["candidates"]],[42])

class DownloadedRunEvidenceTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory()
  self.addCleanup(self.tmp.cleanup)
  self.root=Path(self.tmp.name)
 def put(self,run_id,pub=None,stages=None,shadow=None):
  folder=self.root/str(run_id)/"four-mode-evidence";folder.mkdir(parents=True)
  for name,record in (("publication.json",pub),("stages.json",stages),
                      ("hole-shadow.json",shadow)):
   if record is not None:
    (folder/name).write_text(json.dumps(record))
 def test_no_eligible_not_a_missing_artifact_error(self):
  self.put(1,{"outcome":"no_eligible_candidates"},{"receipt_staging":"success"},
           {"status":"not_published","records":[]})
  x=summarize_downloaded_runs(self.root,[1])
  self.assertEqual(x[0]["stage"],"no_eligible_forecasts_published")
  self.assertTrue(x[0]["has_hole_shadow"])
  self.assertEqual(x[0]["shadow_records"],0)
 def test_publication_failed_before_shadow(self):
  self.put(2,{"outcome":"failed"},{"receipt_staging":"failure"})
  x=summarize_downloaded_runs(self.root,[2])
  self.assertEqual(x[0]["stage"],"publication_pipeline_failed")
  self.assertFalse(x[0]["has_hole_shadow"])
 def test_published_but_missing_hole_shadow_is_visible(self):
  self.put(3,{"outcome":"pushed_to_main"},{"receipt_staging":"success"})
  x=summarize_downloaded_runs(self.root,[3])
  self.assertEqual(x[0]["stage"],"missing_shadow_evidence")
  self.assertFalse(x[0]["has_hole_shadow"])
 def test_missing_stage_not_success(self):
  self.put(4,{"outcome":"pushed_to_main"})
  x=summarize_downloaded_runs(self.root,[4])
  self.assertEqual(x[0]["stage"],"missing_stage_evidence")
 def test_multiple_evidence_files_not_silently_accepted(self):
  self.put(5,{"outcome":"pushed_to_main"},{"receipt_staging":"success"})
  folder=self.root/"5"/"duplicate";folder.mkdir()
  (folder/"publication.json").write_text("{}")
  x=summarize_downloaded_runs(self.root,[5])
  self.assertEqual(x[0]["stage"],"ambiguous_multiple_evidence_files")
if __name__=="__main__":
 unittest.main()

import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock
from scripts.capture_joint_preview_batch import candidates, collect

NOW=datetime.fromisoformat('2026-11-04T20:00:00+09:00')
CODE='202611040112'
ROW={'race_code':CODE,'venue_code':'01','race_no':12,'deadline_jst':'2026-11-04T20:31:00+09:00'}
SCHEDULE={'ok':True,'date':'20261104','races':[ROW]}

def before(code,root,identifier):
 return {'status':'official_json_observed_not_t12_certified','race_code':code,
         'deadline_display':'20:31','received_at_jst':NOW.isoformat()}
def odds(*args):return {'status':'official_odds_observed_research_only'}
def audit(*args):return {'both_complete_before_t12':True,'forecast_usable':False,'full_t12_source_certified':False}

class JointBatchTests(unittest.TestCase):
 def run_collect(self,root,**kwargs):
  opts={'clock':lambda:NOW,'schedule_fetch':lambda day:(200,SCHEDULE),'before':before,'odds':odds,'auditor':audit,'event':'pull_request'};opts.update(kwargs)
  return collect(root,'test1',**opts)
 def test_current_unique_bounded_candidates_and_conflicting_schedule_rejection(self):
  self.assertEqual(candidates(SCHEDULE,NOW),[CODE])
  data={**SCHEDULE,'races':[ROW,{**ROW,'deadline_jst':'2026-11-04T20:32:00+09:00'}]}
  self.assertEqual(candidates(data,NOW),[])
  data={**SCHEDULE,'races':[{**ROW,'deadline_jst':'2026-11-04T20:12:39+09:00'}]}
  self.assertEqual(candidates(data,NOW),[])
  with self.assertRaises(ValueError):candidates({**SCHEDULE,'date':'20261103'},NOW)
 def test_same_run_positive_pair_and_publication_never_promote_forecast(self):
  with tempfile.TemporaryDirectory() as root:
   report=self.run_collect(root)
   self.assertEqual(report['complete_pairs_before_t12'],1)
   self.assertEqual(report['beforeinfo_originals_saved'],1)
   self.assertEqual(report['official_odds_originals_saved'],1)
   self.assertFalse(report['forecast_usable']);self.assertFalse(report['formal'])
   saved=(Path(root)/'batch_report.json').read_bytes()
   with self.assertRaises(FileExistsError):self.run_collect(root)
   self.assertEqual((Path(root)/'batch_report.json').read_bytes(),saved)
 def test_not_ready_original_pair_is_not_counted_as_success(self):
  with tempfile.TemporaryDirectory() as root:
   report=self.run_collect(root,auditor=lambda *args:{'both_complete_before_t12':False,'missing_components':['start_exhibition_six']})
   self.assertEqual(report['status'],'sources_saved_pair_not_ready')
   self.assertEqual(report['complete_pairs_before_t12'],0)
   self.assertEqual(report['observations'][0]['joint_audit']['missing_components'],['start_exhibition_six'])
 def test_beforeinfo_failure_never_fetches_odds_and_is_not_green_source(self):
  fetch=Mock()
  with tempfile.TemporaryDirectory() as root:
   report=self.run_collect(root,before=lambda *args:{'status':'official_json_probe_failed'},odds=fetch)
   fetch.assert_not_called();self.assertEqual(report['status'],'source_capture_failed')
 def test_source_cutoff_crossed_during_before_fetch_prevents_odds(self):
  fetch=Mock()
  def late(*args):return {**before(*args),'deadline_display':'20:13','received_at_jst':'2026-11-04T20:01:01+09:00'}
  with tempfile.TemporaryDirectory() as root:
   report=self.run_collect(root,before=late,odds=fetch)
   fetch.assert_not_called();self.assertEqual(report['observations'][0]['status'],'beforeinfo_after_t12')
 def test_odds_exception_keeps_beforeinfo_report_and_missing_pair(self):
  with tempfile.TemporaryDirectory() as root:
   report=self.run_collect(root,odds=Mock(side_effect=OSError('unavailable')))
   self.assertEqual(report['beforeinfo_originals_saved'],1)
   self.assertEqual(report['complete_pairs_before_t12'],0)
   self.assertEqual(report['observations'][0]['status'],'capture_or_audit_failed')
   self.assertTrue((Path(root)/'batch_report.json').is_file())

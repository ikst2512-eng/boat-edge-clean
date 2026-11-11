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
   self.assertEqual(report['status'],'source_capture_failed')
   self.assertTrue((Path(root)/'batch_report.json').is_file())

 def test_one_failed_odds_fetch_cannot_be_masked_by_another_complete_pair(self):
  second={**ROW,'race_code':'202611040111','race_no':11,
          'deadline_jst':'2026-11-04T20:32:00+09:00'}
  requested=[]
  def partial_odds(code,*args):
   requested.append(code)
   if len(requested)==2:raise OSError('source unavailable')
   return odds(code,*args)
  with tempfile.TemporaryDirectory() as root:
   report=self.run_collect(root,
       schedule_fetch=lambda day:(200,{**SCHEDULE,'races':[ROW,second]}),
       odds=partial_odds)
   self.assertEqual(report['eligible_candidates'],2)
   self.assertEqual(report['beforeinfo_originals_saved'],2)
   self.assertEqual(report['official_odds_originals_saved'],1)
   self.assertEqual(report['complete_pairs_before_t12'],1)
   self.assertEqual(report['status'],'source_capture_failed')
   self.assertEqual(sum(x['status']=='capture_or_audit_failed' for x in report['observations']),1)
   self.assertFalse(report['forecast_usable'])

 def test_workflow_preserves_csv_work_before_failing_official_outage(self):
  text=Path('.github/workflows/research-live-preview-evidence.yml').read_text()
  official=text.index('      - name: Preserve official preview and odds originals')
  csv=text.index('      - name: Capture eligible predeadline preview rows')
  final=text.index('      - name: Fail official capture only after preserving independent CSV work')
  upload=text.index('      - name: Archive separately from research predictions')
  self.assertIn('continue-on-error: true',text[official:csv])
  self.assertIn("steps.official_pair_capture.outcome == 'failure'",text[final:upload])
  self.assertLess(official,csv);self.assertLess(csv,final);self.assertLess(final,upload)

 def test_same_run_three_original_research_followup_keeps_two_source_pair(self):
  with tempfile.TemporaryDirectory() as root:
   seen=[]
   def card(code, out, ident):
    seen.append((code, ident))
    return {'status':'official_racelist_html_observed_research_only','forecast_usable':False}
   def three(card_dir, before_dir, odds_dir):
    self.assertEqual(card_dir.name, CODE)
    self.assertIn('racelist_',str(card_dir))
    self.assertIn('before_',str(before_dir))
    self.assertIn('odds_',str(odds_dir))
    return {'race_code':CODE, 'cutoff_jst':'2026-11-04T20:19:00+09:00',
            't12_receipt_margin_seconds':120.0,
            'component_checks':{key:True for key in (
              'racecard_original_hash_verified','racecard_six_registrations',
              'racer_registration_ids_match','racecard_received_by_t12',
              'beforeinfo_received_by_t12','beforeinfo_six_unique_boats',
              'exhibition_six_courses','exhibition_times_six','tilt_six',
              'start_exhibition_six','odds_120','odds_received_by_t12')},
            'missing_components':[],
            'all_research_components_observed_by_t12':True,
            'three_originals_hash_verified':True,
            'final_race_entry_verified':False,'full_t12_source_certified':False,
            'forecast_usable':False,'t12_eligible':False}
   report=self.run_collect(root,capture_racelist_original=True,
      racelist=card,three_auditor=three,
      auditor=lambda *a:{**audit(*a),'cutoff_jst':'2026-11-04T20:19:00+09:00'})
   self.assertEqual(report['complete_pairs_before_t12'],1)
   self.assertEqual(report['racelist_originals_saved'],1)
   self.assertEqual(report['three_originals_complete_before_t12'],1)
   self.assertEqual(report['status'],'complete_pairs_observed')
   self.assertEqual(seen,[(CODE,'racelist_test1')])
   self.assertEqual(report['observations'][0]['racecard_followup'],'three_originals_research_complete')
   self.assertFalse(report['formal']);self.assertFalse(report['forecast_usable'])

 def test_forged_three_source_summary_cannot_increment_completed_count(self):
  base={'race_code':CODE,'cutoff_jst':'2026-11-04T20:19:00+09:00',
        't12_receipt_margin_seconds':120.0,
        'component_checks':{key:True for key in (
          'racecard_original_hash_verified','racecard_six_registrations',
          'racer_registration_ids_match','racecard_received_by_t12',
          'beforeinfo_received_by_t12','beforeinfo_six_unique_boats',
          'exhibition_six_courses','exhibition_times_six','tilt_six',
          'start_exhibition_six','odds_120','odds_received_by_t12')},
        'missing_components':[],
        'all_research_components_observed_by_t12':True,
        'three_originals_hash_verified':True,
        'final_race_entry_verified':False,
        'full_t12_source_certified':False,
        't12_eligible':False,'forecast_usable':False}
  problems={
    'other_race':{'race_code':'202611040111'},
    'other_cutoff':{'cutoff_jst':'2026-11-04T20:20:00+09:00'},
    'at_cutoff':{'t12_receipt_margin_seconds':0.0},
    'false_component':{'component_checks':{**base['component_checks'],'odds_120':False}},
    'missing_component':{'component_checks':{'odds_120':True}},
    'hidden_missing':{'missing_components':['exhibition_times_six']},
    'bool_margin':{'t12_receipt_margin_seconds':True},
  }
  for name,change in problems.items():
   with self.subTest(forgery=name),tempfile.TemporaryDirectory() as root:
    bad={**base,**change}
    report=self.run_collect(root,capture_racelist_original=True,
       racelist=lambda *a:{'status':'official_racelist_html_observed_research_only'},
       three_auditor=lambda *a:bad,
       auditor=lambda *a:{**audit(*a),'cutoff_jst':base['cutoff_jst']})
    self.assertEqual(report['complete_pairs_before_t12'],1)
    self.assertEqual(report['racelist_originals_saved'],1)
    self.assertEqual(report['three_originals_complete_before_t12'],0)
    self.assertEqual(report['observations'][0]['racecard_followup'],
                     'three_originals_unverified')
    self.assertFalse(report['formal'])
    self.assertFalse(report['forecast_usable'])

 def test_racelist_failure_must_not_downgrade_valid_pair(self):
  with tempfile.TemporaryDirectory() as root:
   report=self.run_collect(root,capture_racelist_original=True,
      racelist=lambda *a:{'status':'official_racelist_probe_failed','error':'TimeoutError'},
      auditor=lambda *a:{**audit(*a),'cutoff_jst':'2026-11-04T20:19:00+09:00'})
   self.assertEqual(report['status'],'complete_pairs_observed')
   self.assertEqual(report['complete_pairs_before_t12'],1)
   self.assertEqual(report['racelist_originals_saved'],0)
   self.assertEqual(report['three_originals_complete_before_t12'],0)
   self.assertEqual(report['observations'][0]['racecard_followup'],'source_unavailable')

 def test_missing_t12_margin_skips_racelist_network(self):
  near=datetime.fromisoformat('2026-11-04T20:18:50+09:00')
  stamps=iter([NOW,NOW,near])
  card=Mock()
  with tempfile.TemporaryDirectory() as root:
   report=self.run_collect(root,capture_racelist_original=True,
      clock=lambda:next(stamps),racelist=card,
      auditor=lambda *a:{**audit(*a),'cutoff_jst':'2026-11-04T20:19:00+09:00'})
   card.assert_not_called()
   self.assertEqual(report['observations'][0]['racecard_followup'],'skipped_t12_margin')
   self.assertEqual(report['complete_pairs_before_t12'],1)
   self.assertEqual(report['three_originals_complete_before_t12'],0)

 def test_unverified_racelist_audit_cannot_promote_three_source_count(self):
  with tempfile.TemporaryDirectory() as root:
   report=self.run_collect(root,capture_racelist_original=True,
      racelist=lambda *a:{'status':'official_racelist_html_observed_research_only'},
      three_auditor=lambda *a:{'all_research_components_observed_by_t12':True,
        'three_originals_hash_verified':True,'final_race_entry_verified':True,
        'full_t12_source_certified':False,'t12_eligible':False,'forecast_usable':False},
      auditor=lambda *a:{**audit(*a),'cutoff_jst':'2026-11-04T20:19:00+09:00'})
   self.assertEqual(report['complete_pairs_before_t12'],1)
   self.assertEqual(report['racelist_originals_saved'],1)
   self.assertEqual(report['three_originals_complete_before_t12'],0)
   self.assertEqual(report['observations'][0]['racecard_followup'],'three_originals_unverified')

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
def card_audit(*args):
 return {'race_code':CODE,'original_hash_verified':True,'six_racers_verified':True,
         'racer_registration_identities_agree':True,'received_by_t12':True,
         'beforeinfo_received_by_t12':True,'full_t12_source_certified':False,
         'forecast_usable':False}

class JointBatchTests(unittest.TestCase):
 def run_collect(self,root,**kwargs):
  opts={'clock':lambda:NOW,'schedule_fetch':lambda day:(200,SCHEDULE),'before':before,'odds':odds,'auditor':audit,'event':'pull_request','racelist_auditor':card_audit};opts.update(kwargs)
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

 def test_three_original_research_success_does_not_promote_forecast(self):
  with tempfile.TemporaryDirectory() as root:
   card=Mock(return_value={
     'status':'official_racelist_html_observed_research_only',
     'received_at_jst':'2026-11-04T20:00:10+09:00'})
   joined=Mock(return_value={
     'race_code':CODE,'three_originals_hash_verified':True,
     'all_research_components_observed_by_t12':True,
     'final_race_entry_verified':False,
     'full_t12_source_certified':False,'forecast_usable':False})
   report=self.run_collect(root,include_racelist=True,card=card,
                           triple_auditor=joined)
   self.assertEqual(report['status'],'complete_pairs_observed')
   self.assertEqual(report['complete_pairs_before_t12'],1)
   self.assertEqual(report['official_racelist_originals_saved'],1)
   self.assertEqual(report['complete_three_originals_before_t12'],1)
   self.assertTrue(report['three_originals_not_forecast_certification'])
   self.assertEqual(report['observations'][0]['three_source_status'],
                    'three_originals_research_complete')
   self.assertFalse(report['formal'])
   self.assertFalse(report['forecast_usable'])
   self.assertFalse(report['full_t12_source_certified'])
   card.assert_called_once()
   joined.assert_called_once()

 def test_optional_racelist_does_not_change_original_pair_when_disabled(self):
  with tempfile.TemporaryDirectory() as root:
   card=Mock()
   joined=Mock()
   report=self.run_collect(root,card=card,triple_auditor=joined)
   self.assertEqual(report['complete_pairs_before_t12'],1)
   self.assertEqual(report['complete_three_originals_before_t12'],0)
   card.assert_not_called()
   joined.assert_not_called()

 def test_incomplete_pair_can_preserve_early_racelist_but_not_join(self):
  with tempfile.TemporaryDirectory() as root:
   card=Mock(return_value={
     'status':'official_racelist_html_observed_research_only',
     'received_at_jst':'2026-11-04T20:00:10+09:00'})
   joined=Mock()
   report=self.run_collect(
     root,include_racelist=True,card=card,triple_auditor=joined,
     auditor=lambda *args:{'both_complete_before_t12':False})
   self.assertEqual(report['observations'][0]['three_source_status'],
                    'racelist_verified_pair_incomplete')
   self.assertEqual(report['official_racelist_originals_saved'],1)
   self.assertEqual(report['verified_racelist_six_registration_matches'],1)
   self.assertEqual(report['complete_pairs_before_t12'],0)
   card.assert_called_once()
   joined.assert_not_called()
   self.assertEqual(report['complete_three_originals_before_t12'],0)
   self.assertFalse(report['forecast_usable'])

 def test_failed_racelist_preserves_original_good_pair_and_reason(self):
  with tempfile.TemporaryDirectory() as root:
   joined=Mock()
   report=self.run_collect(
     root,include_racelist=True,
     card=lambda *args:{'status':'official_racelist_probe_failed'},
     triple_auditor=joined)
   self.assertEqual(report['complete_pairs_before_t12'],1)
   self.assertEqual(report['complete_three_originals_before_t12'],0)
   self.assertEqual(report['observations'][0]['three_source_status'],
                    'racelist_capture_failed')
   joined.assert_not_called()
   self.assertFalse(report['forecast_usable'])

 def test_racelist_after_t12_is_not_forgiven_by_valid_pair(self):
  with tempfile.TemporaryDirectory() as root:
   joined=Mock()
   report=self.run_collect(
     root,include_racelist=True,
     card=lambda *args:{
       'status':'official_racelist_html_observed_research_only',
       'received_at_jst':'2026-11-04T20:19:01+09:00'},
     triple_auditor=joined)
   self.assertEqual(report['complete_pairs_before_t12'],1)
   self.assertEqual(report['official_racelist_originals_saved'],1)
   self.assertEqual(report['complete_three_originals_before_t12'],0)
   self.assertEqual(report['observations'][0]['three_source_status'],
                    'racelist_after_t12')
   joined.assert_not_called()

 def test_racelist_preflight_too_late_skips_third_request(self):
  with tempfile.TemporaryDirectory() as root:
   card=Mock()
   joined=Mock()
   clocks=iter((NOW,NOW,
                datetime.fromisoformat('2026-11-04T20:18:40+09:00')))
   report=self.run_collect(
     root,include_racelist=True,clock=lambda:next(clocks),
     card=card,triple_auditor=joined)
   self.assertEqual(report['complete_pairs_before_t12'],1)
   self.assertEqual(report['observations'][0]['three_source_status'],
                    'racelist_preflight_too_late')
   card.assert_not_called();joined.assert_not_called()

 def test_mismatched_or_forged_three_source_audit_never_promotes(self):
  for patch in (
      {'race_code':'202611040111'},
      {'full_t12_source_certified':True},
      {'forecast_usable':True},
      {'final_race_entry_verified':True},
      {'three_originals_hash_verified':False},
      {'all_research_components_observed_by_t12':False}):
   with self.subTest(patch=patch),tempfile.TemporaryDirectory() as root:
    joined={'race_code':CODE,'three_originals_hash_verified':True,
            'all_research_components_observed_by_t12':True,
            'final_race_entry_verified':False,
            'full_t12_source_certified':False,'forecast_usable':False}
    joined.update(patch)
    report=self.run_collect(
      root,include_racelist=True,
      card=lambda *args:{
        'status':'official_racelist_html_observed_research_only',
        'received_at_jst':'2026-11-04T20:00:10+09:00'},
      triple_auditor=lambda *args:joined)
    self.assertEqual(report['complete_pairs_before_t12'],1)
    self.assertEqual(report['complete_three_originals_before_t12'],0)
    self.assertEqual(report['observations'][0]['three_source_status'],
                     'three_originals_incomplete')
    self.assertFalse(report['forecast_usable'])

 def test_wrong_race_or_registration_mismatch_rejects_racelist_evidence(self):
  for patch in (
      {'race_code':'202611040111'},
      {'racer_registration_identities_agree':False},
      {'original_hash_verified':False},
      {'six_racers_verified':False},
      {'beforeinfo_received_by_t12':False},
      {'received_by_t12':False},
      {'forecast_usable':True}):
   with self.subTest(patch=patch),tempfile.TemporaryDirectory() as root:
    check=card_audit()
    check.update(patch)
    third=Mock()
    report=self.run_collect(
       root,include_racelist=True,
       card=lambda *args:{
         'status':'official_racelist_html_observed_research_only',
         'received_at_jst':'2026-11-04T20:00:10+09:00'},
       racelist_auditor=lambda *args:check,triple_auditor=third)
    self.assertEqual(report['complete_pairs_before_t12'],1)
    self.assertEqual(report['official_racelist_originals_saved'],1)
    self.assertEqual(report['verified_racelist_six_registration_matches'],0)
    self.assertEqual(report['complete_three_originals_before_t12'],0)
    self.assertEqual(report['observations'][0]['three_source_status'],
                     'racelist_identity_incomplete')
    self.assertFalse(report['observations'][0]['racelist_six_registration_match_verified'])
    third.assert_not_called()

 def test_racelist_join_exception_preserves_pair_and_diagnostic(self):
  with tempfile.TemporaryDirectory() as root:
   report=self.run_collect(
     root,include_racelist=True,
     card=lambda *args:{
       'status':'official_racelist_html_observed_research_only',
       'received_at_jst':'2026-11-04T20:00:10+09:00'},
     triple_auditor=Mock(side_effect=ValueError('broken raw evidence')))
   self.assertEqual(report['complete_pairs_before_t12'],1)
   self.assertEqual(report['complete_three_originals_before_t12'],0)
   self.assertEqual(report['observations'][0]['three_source_status'],
                    'racelist_or_join_failed')
   self.assertEqual(report['observations'][0]['three_source_error_type'],
                    'ValueError')
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

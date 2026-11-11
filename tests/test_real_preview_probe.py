import unittest
from datetime import datetime
from scripts.verify_real_beforeinfo_source import verify_current_adapter

NOW=datetime.fromisoformat('2026-11-04T19:39:00+09:00')
RACE={'race_code':'202611040111','venue_code':'01','race_no':11,'deadline_jst':'2026-11-04T20:03:00+09:00'}

def card(*args):
 return {'race_key':'20261104-01-11','beforeinfo':{'racers':[{'lane':i,'exhibition_time':6.7,'tilt':0} for i in range(1,7)],'start_exhibition':[{'lane':i,'course':i,'st':'.08'} for i in range(1,7)]},'source_audit':{'beforeinfo':{'status':'ok','fetched_at':NOW.isoformat()}}}

class RealPreviewProbeTests(unittest.TestCase):
 def test_current_complete_source_counts_but_historical_does_not(self):
  kwargs={'now':NOW,'schedule_fetch':lambda day:(200,{'races':[RACE]}),'card_fetch':card}
  self.assertEqual(len(verify_current_adapter('2026/11/04.csv',**kwargs)),1)
  self.assertEqual(verify_current_adapter('2026/11/03.csv',**kwargs),[])
 def test_start_exhibition_requires_inspector_compatible_st(self):
  kwargs={'now':NOW,'schedule_fetch':lambda day:(200,{'races':[RACE]})}
  for value in ('F.01','L.02','.08','0.08'):
   def valid_card(*args):
    data=card()
    data['beforeinfo']['start_exhibition'][0]['st']=value
    return data
   with self.subTest(valid_st=value):
    self.assertEqual(len(verify_current_adapter('2026/11/04.csv',card_fetch=valid_card,**kwargs)),1)
  for value in ('F01','L02','F.01x','6.999'):
   def invalid_card(*args):
    data=card()
    data['beforeinfo']['start_exhibition'][0]['st']=value
    return data
   with self.subTest(invalid_st=value):
    self.assertEqual(verify_current_adapter('2026/11/04.csv',card_fetch=invalid_card,**kwargs),[])

 def test_live_official_artifact_path_and_failure_gate(self):
  # Historical contract is only a fixture. Live runs must create and upload
  # a per-run evidence ledger, including failures, with a non-hidden path.
  from pathlib import Path
  import re
  root=Path(__file__).resolve().parent.parent
  workflow=(root/'.github/workflows/verify-real-beforeinfo.yml').read_text()
  generated=re.findall(r"const proofPath='([^']+)'",workflow)
  uploaded=re.findall(r"^\s+path: ([^\n]+-evidence\.ndjson)$",workflow,re.M)
  self.assertEqual(generated,['clean-live-official-pages-evidence.ndjson'])
  self.assertEqual(uploaded,generated)
  self.assertIn("if(!isHistorical)fs.writeFileSync(proofPath",workflow)
  # The existing verifier must also diagnose backend preview edits on main,
  # not merely edits to its own workflow definition.
  self.assertIn("      - clean_racecard.py", workflow.split("  pull_request:")[0])
  self.assertIn("      - .github/workflows/verify-real-beforeinfo.yml",workflow.split("  pull_request:")[0])
  self.assertIn("kind==='LIVE_OFFICIAL_PAGES_E2E_EVIDENCE'",workflow)
  self.assertIn("kind==='LIVE_OFFICIAL_PAGES_E2E_UNVERIFIED'",workflow)
  self.assertIn('if-no-files-found: error',workflow)
  self.assertIn("cron: '35 10 * * *'",workflow)
  self.assertEqual(workflow.count('- cron:'),1)
  self.assertIn("github.event_name == 'pull_request' || github.event_name == 'push'",workflow)

 def test_missing_preview_and_late_receipt_are_not_success(self):
  def missing(*args):return {'race_key':'20261104-01-11'}
  def late(*args):
   d=card();d['source_audit']['beforeinfo']['fetched_at']=RACE['deadline_jst'];return d
  for fetch in (missing,late):
   self.assertEqual(verify_current_adapter('2026/11/04.csv',now=NOW,schedule_fetch=lambda day:(200,{'races':[RACE]}),card_fetch=fetch),[])

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
 def test_missing_preview_and_late_receipt_are_not_success(self):
  def missing(*args):return {'race_key':'20261104-01-11'}
  def late(*args):
   d=card();d['source_audit']['beforeinfo']['fetched_at']=RACE['deadline_jst'];return d
  for fetch in (missing,late):
   self.assertEqual(verify_current_adapter('2026/11/04.csv',now=NOW,schedule_fetch=lambda day:(200,{'races':[RACE]}),card_fetch=fetch),[])

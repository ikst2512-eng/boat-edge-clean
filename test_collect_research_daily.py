"""Daily collector smoke tests, all network reads mocked."""
import json, tempfile, unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch
import collect_research_daily as collector
from research_model import JST
class CollectorTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory()
  self.addCleanup(self.tmp.cleanup)
  self.store=Path(self.tmp.name)
  self.day=(datetime.now(JST)+timedelta(days=1)).strftime("%Y%m%d")
  self.code=self.day+"1201"
  self.title={"レースコード":self.code,"電話投票締切予定":"23:59"}
  self.card={"レースコード":self.code,**{f"艇{i}_全国勝率":"6.0" for i in range(1,7)}}
 def test_save_and_reuse(self):
  start=datetime.strptime(self.day+"23:59","%Y%m%d%H:%M").replace(tzinfo=JST)-timedelta(hours=3)
  with patch.object(collector,"STORE",self.store),patch("research_model.STORE",self.store),patch.object(collector,"read_rows",side_effect=[([self.title],start),([self.card],start)]):
   self.assertEqual(collector.collect(self.day)["saved"],1)
  saved=list(self.store.glob("*.json"))
  self.assertEqual(len(saved),1)
  self.assertEqual(len(json.loads(saved[0].read_text())["predictions"]),10)
  with patch.object(collector,"STORE",self.store),patch("research_model.STORE",self.store),patch.object(collector,"read_rows",side_effect=[([self.title],start),([self.card],start)]):
   self.assertEqual(collector.collect(self.day)["already_saved"],1)
 def test_missing_card(self):
  start=datetime.now(JST)
  with patch.object(collector,"STORE",self.store),patch.object(collector,"read_rows",side_effect=[([self.title],start),([],start)]):
   with self.assertRaisesRegex(ValueError,"race card source is empty"):\n    collector.collect(self.day)
   self.assertFalse(list(self.store.glob("*.json")))
 def test_empty_titles_rejected(self):
  with patch.object(collector,"STORE",self.store),patch.object(collector,"read_rows",side_effect=[([],datetime.now(JST)),([self.card],datetime.now(JST))]):
   with self.assertRaisesRegex(ValueError,"no valid race titles"):
    collector.collect(self.day)
 def test_all_invalid_rejected(self):
  broken=dict(self.card,艇1_全国勝率="NaN")
  start=datetime.strptime(self.day+"23:59","%Y%m%d%H:%M").replace(tzinfo=JST)-timedelta(hours=3)
  with patch.object(collector,"STORE",self.store),patch("research_model.STORE",self.store),patch.object(collector,"read_rows",side_effect=[([self.title],start),([broken],start)]):
   counts=collector.collect(self.day)
   self.assertEqual(counts["invalid"],1)
   with self.assertRaisesRegex(ValueError,"no valid or cutoff-eligible"):
    collector.validate_run_counts(counts)
if __name__=="__main__":unittest.main()

"""Daily collector smoke tests, all network reads mocked."""
import json, tempfile, unittest, hashlib
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
  with patch.object(collector,"model_provenance",return_value={"model_git_sha":"a"*40,"model_source_sha256":"b"*64}),patch.object(collector,"STORE",self.store),patch("research_model.STORE",self.store),patch.object(collector,"read_rows",side_effect=[([self.title],start,"a"*64),([self.card],start,"b"*64)]):
   self.assertEqual(collector.collect(self.day)["saved"],1)
  saved=list(self.store.glob("*.json"))
  self.assertEqual(len(saved),1)
  record=json.loads(saved[0].read_text())
  self.assertEqual(len(record["predictions"]),10)
  self.assertEqual(record["source_title_sha256"],"a"*64)
  self.assertEqual(record["source_cards_sha256"],"b"*64)
  self.assertEqual(record["input_sha256"],hashlib.sha256(("a"*64+":"+"b"*64).encode("ascii")).hexdigest())
  self.assertEqual(record["model_git_sha"],"a"*40)
  self.assertEqual(record["source_deadline_jst"],datetime.strptime(self.day+"23:59","%Y%m%d%H:%M").replace(tzinfo=JST).isoformat())
  self.assertEqual(datetime.fromisoformat(record["source_deadline_jst"])-datetime.fromisoformat(record["cutoff_jst"]),timedelta(minutes=12))
  with patch.object(collector,"STORE",self.store),patch("research_model.STORE",self.store),patch.object(collector,"read_rows",side_effect=[([self.title],start,"a"*64),([self.card],start,"b"*64)]):
   self.assertEqual(collector.collect(self.day)["already_saved"],1)
 def test_model_provenance_read_once_for_multiple_new_races(self):
  second=self.day+"1202"
  second_title=dict(self.title, レースコード=second)
  second_card=dict(self.card, レースコード=second)
  start=datetime.strptime(self.day+"23:59","%Y%m%d%H:%M").replace(tzinfo=JST)-timedelta(hours=3)
  with patch.object(collector,"model_provenance",return_value={"model_git_sha":"a"*40,"model_source_sha256":"b"*64}) as proof,patch.object(collector,"STORE",self.store),patch("research_model.STORE",self.store),patch.object(collector,"read_rows",side_effect=[([self.title,second_title],start,"a"*64),([self.card,second_card],start,"b"*64)]):
   self.assertEqual(collector.collect(self.day)["saved"],2)
   proof.assert_called_once_with()
  for path in self.store.glob("*.json"):
   self.assertEqual(json.loads(path.read_text())["model_git_sha"],"a"*40)
 def test_missing_card(self):
  start=datetime.now(JST)
  with patch.object(collector,"STORE",self.store),patch.object(collector,"read_rows",side_effect=[([self.title],start,"a"*64),([],start,"b"*64)]):
   with self.assertRaisesRegex(ValueError,"race card source is empty"):
    collector.collect(self.day)
   self.assertFalse(list(self.store.glob("*.json")))
 def test_empty_titles_rejected(self):
  with patch.object(collector,"STORE",self.store),patch.object(collector,"read_rows",side_effect=[([],datetime.now(JST),"a"*64),([self.card],datetime.now(JST),"b"*64)]):
   with self.assertRaisesRegex(ValueError,"no valid race titles"):
    collector.collect(self.day)
 def test_all_invalid_rejected(self):
  broken=dict(self.card,艇1_全国勝率="NaN")
  start=datetime.strptime(self.day+"23:59","%Y%m%d%H:%M").replace(tzinfo=JST)-timedelta(hours=3)
  with patch.object(collector,"STORE",self.store),patch("research_model.STORE",self.store),patch.object(collector,"read_rows",side_effect=[([self.title],start,"a"*64),([broken],start,"b"*64)]):
   counts=collector.collect(self.day)
   self.assertEqual(counts["invalid"],1)
   with self.assertRaisesRegex(ValueError,"no valid or cutoff-eligible"):
    collector.validate_run_counts(counts)
if __name__=="__main__":unittest.main()

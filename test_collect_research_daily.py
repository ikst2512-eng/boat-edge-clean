"""Daily collector smoke tests, all network reads mocked."""
import hashlib, json, tempfile, unittest
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
  with patch.object(collector,"model_provenance",return_value={"model_git_sha":"c"*40,"model_source_sha256":"d"*64}),patch.object(collector,"STORE",self.store),patch("research_model.STORE",self.store),patch.object(collector,"read_rows",side_effect=[([self.title],start,"a"*64),([self.card],start,"b"*64)]):
   self.assertEqual(collector.collect(self.day)["saved"],1)
  saved=list(self.store.glob("*.json"))
  self.assertEqual(len(saved),1)
  self.assertEqual(len(json.loads(saved[0].read_text())["predictions"]),10)
  record=json.loads(saved[0].read_text())
  self.assertEqual(record["source_title_sha256"],"a"*64)
  self.assertEqual(record["source_cards_sha256"],"b"*64)
  self.assertIn("source_deadline_jst",record)
  self.assertIn("model_source_sha256",record)
  self.assertEqual(record["input_sha256"],hashlib.sha256(("a"*64+":"+"b"*64).encode("ascii")).hexdigest())
  self.assertEqual(record["source_deadline_jst"],self.day[:4]+"-"+self.day[4:6]+"-"+self.day[6:8]+"T23:59:00+09:00")
  with patch.object(collector,"STORE",self.store),patch("research_model.STORE",self.store),patch.object(collector,"read_rows",side_effect=[([self.title],start,"a"*64),([self.card],start,"b"*64)]):
   self.assertEqual(collector.collect(self.day)["already_saved"],1)
 def test_missing_model_provenance_never_writes_snapshot(self):
  start=datetime.strptime(self.day+"23:59","%Y%m%d%H:%M").replace(tzinfo=JST)-timedelta(hours=3)
  with patch.object(collector,"STORE",self.store),patch("research_model.STORE",self.store),patch.object(collector,"read_rows",side_effect=[([self.title],start,"a"*64),([self.card],start,"b"*64)]),patch.object(collector,"model_provenance",side_effect=ValueError("no frozen model")):
   report=collector.collect(self.day)
  self.assertEqual(report["invalid"],1)
  self.assertEqual(report["saved"],0)
  self.assertFalse(list(self.store.glob("*.json")))
 def test_duplicate_source_rows_are_rejected_without_saving(self):
  start=datetime.strptime(self.day+"23:59","%Y%m%d%H:%M").replace(tzinfo=JST)-timedelta(hours=3)
  for titles,cards in (([self.title,self.title],[self.card]),
                       ([self.title],[self.card,self.card])):
   with self.subTest(titles=len(titles),cards=len(cards)):
    with patch.object(collector,"STORE",self.store),patch.object(collector,"read_rows",side_effect=[(titles,start,"a"*64),(cards,start,"b"*64)]):
     result=collector.collect(self.day)
    self.assertEqual(result["saved"],0)
    self.assertGreaterEqual(result["invalid"],1)
    self.assertEqual(list(self.store.glob("*.json")),[])
 def test_missing_card(self):
  start=datetime.now(JST)
  with patch.object(collector,"STORE",self.store),patch.object(collector,"read_rows",side_effect=[([self.title],start,"a"*64),([],start,"b"*64)]):
   with self.assertRaisesRegex(ValueError, "race card source is empty"):
    collector.collect(self.day)
   self.assertFalse(list(self.store.glob("*.json")))
if __name__=="__main__":unittest.main()

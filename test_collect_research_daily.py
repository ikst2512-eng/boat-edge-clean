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
 def test_primary_csv_outage_uses_independent_pre_race_program(self):
  start=datetime.strptime(self.day+"23:59","%Y%m%d%H:%M").replace(tzinfo=JST)-timedelta(hours=3)
  source={"source":"nonofficial_openapi_v1","valid":1,"rejected":0}
  with patch.object(collector,"model_provenance",return_value={"model_git_sha":"a"*40,"model_source_sha256":"b"*64}),patch.object(collector,"STORE",self.store),patch("research_model.STORE",self.store),patch.object(collector,"read_rows",side_effect=OSError("primary unavailable")),patch("clean_openapi_sources.load",return_value=([self.title],[self.card],start,"c"*64,source)) as alternate:
   result=collector.collect(self.day)
  self.assertEqual(result["saved"],1)
  alternate.assert_called_once_with(self.day)
  record=json.loads(next(self.store.glob("*.json")).read_text())
  self.assertEqual(record["input_source_kind"],"nonofficial_openapi_v1")
  self.assertEqual(record["source_title_sha256"],"c"*64)
  self.assertEqual(len(record["predictions"]),10)

 def test_http_unavailable_uses_alternate_before_cutoff(self):
  start=datetime.strptime(self.day+"23:59","%Y%m%d%H:%M").replace(tzinfo=JST)-timedelta(hours=3)
  metadata={"source":"nonofficial_openapi_v1","valid":1,"rejected":0}
  with patch.object(collector,"model_provenance",return_value={"model_git_sha":"a"*40,"model_source_sha256":"b"*64}),patch.object(collector,"STORE",self.store),patch("research_model.STORE",self.store),patch.object(collector,"read_rows",side_effect=ValueError("source unavailable")),patch("clean_openapi_sources.load",return_value=([self.title],[self.card],start,"d"*64,metadata)) as alternate:
   self.assertEqual(collector.collect(self.day)["saved"],1)
  alternate.assert_called_once_with(self.day)
  record=json.loads(next(self.store.glob("*.json")).read_text())
  self.assertEqual(record["input_source_kind"],"nonofficial_openapi_v1")
  self.assertEqual(len(record["predictions"]),10)

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
 def test_late_source_classified_separately_from_clock(self):
  cutoff=datetime.strptime(self.day+"23:59","%Y%m%d%H:%M").replace(tzinfo=JST)-timedelta(minutes=12)
  source_after_cutoff=cutoff+timedelta(minutes=1)
  with patch.object(collector,"STORE",self.store),patch("research_model.STORE",self.store),patch.object(collector,"read_rows",side_effect=[([self.title],source_after_cutoff,"a"*64),([self.card],source_after_cutoff,"b"*64)]):
   counts=collector.collect(self.day)
   self.assertEqual((counts["not_ready"],counts["not_ready_clock"],counts["not_ready_source"]),(1,0,1))
   self.assertFalse(list(self.store.glob("*.json")))
 def test_expired_deadline_classified_as_clock_not_source(self):
  today=datetime.now(JST).strftime("%Y%m%d")
  title={"レースコード":today+"1201","電話投票締切予定":"00:01"}
  card=dict(self.card,レースコード=today+"1201")
  source=datetime.strptime(today+"00:01","%Y%m%d%H:%M").replace(tzinfo=JST)-timedelta(hours=3)
  with patch.object(collector,"STORE",self.store),patch("research_model.STORE",self.store),patch.object(collector,"read_rows",side_effect=[([title],source,"a"*64),([card],source,"b"*64)]):
   counts=collector.collect(today)
   self.assertEqual((counts["not_ready"],counts["not_ready_clock"],counts["not_ready_source"]),(1,1,0))
   self.assertFalse(list(self.store.glob("*.json")))
 def test_missing_card(self):
  start=datetime.now(JST)
  with patch.object(collector,"STORE",self.store),patch.object(collector,"read_rows",side_effect=[([self.title],start,"a"*64),([],start,"b"*64)]),patch("clean_openapi_sources.load",side_effect=ValueError("no_valid_races")):
   with self.assertRaisesRegex(ValueError,"no_valid_races"):
    collector.collect(self.day)
   self.assertFalse(list(self.store.glob("*.json")))
 def test_empty_titles_rejected(self):
  with patch.object(collector,"STORE",self.store),patch.object(collector,"read_rows",side_effect=[([],datetime.now(JST),"a"*64),([self.card],datetime.now(JST),"b"*64)]),patch("clean_openapi_sources.load",side_effect=ValueError("no_valid_races")):
   with self.assertRaisesRegex(ValueError,"no_valid_races"):
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

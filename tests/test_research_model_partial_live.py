"""Regression of the real predictor, not only schedule selection mocks."""
import json
import tempfile
import unittest
from datetime import datetime,timedelta
from pathlib import Path
from unittest.mock import patch

import research_model as model

NOW=datetime.now(model.JST)
DAY=(NOW+timedelta(days=1)).strftime("%Y%m%d")
CODE=DAY+"0708"
TITLE={"レースコード":CODE,"電話投票締切予定":"23:55"}
CARD={"レースコード":CODE,**{f"艇{i}_全国勝率":str(4.2+i/10) for i in range(1,7)}}
DIGEST="a"*64

def mocked_receipt():
    return datetime.now(model.JST)

def direct_mocks(*, direct_title=None):
    return (
        patch("clean_direct_sources.holding_rows",return_value=([direct_title or TITLE],mocked_receipt(),DIGEST)),
        patch("clean_direct_sources.fetch_bytes",return_value=b"race-specific-six-racers"),
        patch("clean_direct_sources.parse_card",return_value=CARD)
    )

class PartialPredictorTests(unittest.TestCase):
    def test_partial_published_daily_rows_produce_original_target_forecast(self):
        # Both public daily archives can exist while this exact race is
        # missing. Direct title/card evidence must be used for the right code.
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(model,"STORE",Path(tmp)),\
                 patch.object(model,"read_rows",side_effect=lambda url:(
                    [{"レースコード":DAY+"0101","電話投票締切予定":"10:00"}],
                    mocked_receipt(),"b"*64) if "/title/" in url else (
                    [{"レースコード":DAY+"0101"}],mocked_receipt(),"c"*64)),\
                 patch.object(model,"model_provenance",return_value={
                     "model_git_sha":"1"*40,"model_source_sha256":"2"*64,
                     "model_dependency_scope":"research_model.py_only_not_complete_environment"}),\
                 direct_mocks()[0],direct_mocks()[1],direct_mocks()[2]:
                out=model.predict(DAY,"07","08")
                self.assertEqual(out["status"],"research")
                self.assertEqual(len(out["predictions"]),10)
                saved=json.loads((Path(tmp)/(CODE+".json")).read_text())
                self.assertEqual(saved["race_code"],CODE)
                self.assertEqual(saved["input_source_kind"],"direct_race_specific_pre_race")
                self.assertEqual(saved["source_title_sha256"],DIGEST)
                self.assertEqual(saved["source_cards_sha256"],
                                 __import__("hashlib").sha256(b"race-specific-six-racers").hexdigest())
                self.assertLessEqual(datetime.fromisoformat(saved["generated_at"]),
                                     datetime.fromisoformat(saved["cutoff_jst"]))
    def test_unpublished_daily_csv_uses_exact_direct_race_and_avoids_openapi(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(model,"STORE",Path(tmp)),\
                 patch.object(model,"read_rows",side_effect=OSError("daily CSV not yet available")),\
                 patch.object(model,"model_provenance",return_value={
                     "model_git_sha":"1"*40,"model_source_sha256":"2"*64,
                     "model_dependency_scope":"research_model.py_only_not_complete_environment"}),\
                 patch("clean_direct_sources.holding_rows",return_value=(
                     [TITLE],mocked_receipt(),DIGEST)),\
                 patch("clean_direct_sources.fetch_bytes",return_value=b"correct-race-card"),\
                 patch("clean_direct_sources.parse_card",return_value=CARD),\
                 patch("clean_openapi_sources.load",side_effect=AssertionError("direct was complete")):
                response=model.predict(DAY,"07","08")
                self.assertEqual(response["status"],"research")
                record=json.loads((Path(tmp)/(CODE+".json")).read_text())
                self.assertEqual(record["input_source_kind"],"direct_race_specific_pre_race")
                self.assertEqual(record["race_code"],CODE)
    def test_public_missing_and_direct_unavailable_uses_same_race_openapi(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(model,"STORE",Path(tmp)),\
                 patch.object(model,"read_rows",side_effect=OSError("daily missing")),\
                 patch.object(model,"model_provenance",return_value={
                     "model_git_sha":"1"*40,"model_source_sha256":"2"*64,
                     "model_dependency_scope":"research_model.py_only_not_complete_environment"}),\
                 patch("clean_direct_sources.holding_rows",side_effect=OSError("holding unavailable")),\
                 patch("clean_openapi_sources.load",return_value=(
                     [TITLE],[CARD],mocked_receipt(),"f"*64,
                     {"source":"nonofficial_openapi_v1"})):
                model.predict(DAY,"07","08")
                record=json.loads((Path(tmp)/(CODE+".json")).read_text())
                self.assertEqual(record["input_source_kind"],"nonofficial_openapi_v1")
                self.assertEqual(record["source_cards_sha256"],"f"*64)
    def test_all_unavailable_sources_never_create_prediction(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(model,"STORE",Path(tmp)),\
                 patch.object(model,"read_rows",side_effect=OSError("daily missing")),\
                 patch("clean_direct_sources.holding_rows",side_effect=OSError("direct missing")),\
                 patch("clean_openapi_sources.load",side_effect=OSError("alternative missing")):
                with self.assertRaises(OSError):
                    model.predict(DAY,"07","08")
                self.assertFalse((Path(tmp)/(CODE+".json")).exists())
    def test_published_title_vs_direct_deadline_conflict_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(model,"STORE",Path(tmp)),\
                 patch.object(model,"read_rows",side_effect=lambda url:(
                    [TITLE],mocked_receipt(),"a"*64) if "/title/" in url else (
                    [{"レースコード":DAY+"0101"}],mocked_receipt(),"a"*64)),\
                 patch("clean_direct_sources.holding_rows",return_value=(
                     [{"レースコード":CODE,"電話投票締切予定":"23:56"}],
                     mocked_receipt(),"a"*64)),\
                 patch("clean_openapi_sources.load",side_effect=AssertionError("conflict cannot fall back")):
                with self.assertRaisesRegex(ValueError,"race_deadline_source_conflict"):
                    model.predict(DAY,"07","08")
                self.assertFalse((Path(tmp)/(CODE+".json")).exists())
    def test_unknown_race_from_all_sources_never_generates(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(model,"STORE",Path(tmp)),\
                 patch.object(model,"read_rows",side_effect=lambda url:(
                    [],mocked_receipt(),"a"*64)),\
                 patch("clean_direct_sources.holding_rows",return_value=(
                     [{"レースコード":DAY+"0909","電話投票締切予定":"23:55"}],
                     mocked_receipt(),"a"*64)),\
                 patch("clean_openapi_sources.load",return_value=(
                     [],[],mocked_receipt(),"a"*64,{"source":"nonofficial_openapi_v1"})):
                with self.assertRaisesRegex(ValueError,"race_missing_from_all_pre_race_sources"):
                    model.predict(DAY,"07","08")
                self.assertFalse((Path(tmp)/(CODE+".json")).exists())
if __name__=="__main__":
    unittest.main()

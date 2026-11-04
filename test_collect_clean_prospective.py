import unittest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch
from datetime import datetime, timedelta
from research_model import JST
from collect_clean_prospective import build, finalize_records
import collect_clean_prospective as capture

class ProspectiveTests(unittest.TestCase):
    def test_pre_cutoff_and_no_formal_promotion(self):
        now=datetime(2026,10,28,10,0,tzinfo=JST)
        title=[{"レースコード":"202610281201","電話投票締切予定":"14:00"}]
        card=[{"レースコード":"202610281201",**{f"艇{i}_全国勝率":"5.1" for i in range(1,7)}}]
        rows=build("20261028",title,card,now,now,"a"*64,"b"*64,now,{"model_git_sha":"a"*40,"model_source_sha256":"b"*64})
        r=rows["202610281201"]
        self.assertFalse(r["formal"])
        self.assertFalse(r["scoring"])
        self.assertEqual(len(r["predictions"]),10)
        late=build("20261028",title,card,now,now,"a"*64,"b"*64,datetime(2026,10,28,13,49,tzinfo=JST),{})
        self.assertEqual(late,{})
    def test_finalized_generation_timestamp_is_after_input_receipts(self):
        now=datetime(2026,11,4,11,0,0,tzinfo=JST)
        title=[{"レースコード":"202611040404","電話投票締切予定":"12:16"}]
        card=[{"レースコード":"202611040404",**{f"艇{i}_全国勝率":"5.1" for i in range(1,7)}}]
        title_time=now+timedelta(milliseconds=100)
        cards_time=now+timedelta(milliseconds=200)
        tentative=build("20261104",title,card,title_time,cards_time,"a"*64,"b"*64,
                        now+timedelta(milliseconds=201),{})
        completed=now+timedelta(milliseconds=400)
        saved=finalize_records(tentative,title_time,cards_time,completed)
        self.assertEqual(saved["202611040404"]["generated_at"],completed.isoformat())
        self.assertLessEqual(cards_time,datetime.fromisoformat(saved["202611040404"]["generated_at"]))
        # Existing stored records must never be rewritten by the helper.
        self.assertEqual(tentative["202611040404"]["generated_at"],
                         (now+timedelta(milliseconds=201)).isoformat())

    def test_finalization_excludes_records_that_cross_twelve_minute_cutoff(self):
        now=datetime(2026,11,4,12,3,58,tzinfo=JST)
        title=[{"レースコード":"202611040404","電話投票締切予定":"12:16"}]
        card=[{"レースコード":"202611040404",**{f"艇{i}_全国勝率":"5.1" for i in range(1,7)}}]
        source_time=now
        tentative=build("20261104",title,card,source_time,source_time,"a","b",now,{})
        self.assertIn("202611040404",tentative)
        self.assertEqual(finalize_records(tentative,source_time,source_time,
                         datetime(2026,11,4,12,4,tzinfo=JST)),{})
        self.assertEqual(finalize_records(tentative,source_time,source_time,
                         datetime(2026,11,4,12,3,59,tzinfo=JST))["202611040404"]["generated_at"],
                         "2026-11-04T12:03:59+09:00")

    def test_end_to_end_source_receipts_precede_frozen_generated_at(self):
        day="20990101"
        code=day+"0404"
        titles=[{"レースコード":code,"電話投票締切予定":"12:16"}]
        cards=[{"レースコード":code,**{f"艇{i}_全国勝率":"5.1" for i in range(1,7)}}]
        received=[]
        def fake_read(url):
            now=datetime.now(JST)
            received.append(now)
            return (titles if "/title/" in url else cards),now,"a"*64
        with tempfile.TemporaryDirectory() as tmp, \
             patch.object(capture,"STORE",Path(tmp)/"prospective_predictions"), \
             patch.object(capture,"read_rows",side_effect=fake_read) as calls, \
             patch.object(capture,"model_provenance",return_value={
                 "model_git_sha":"a"*40,"model_source_sha256":"b"*64}):
            result=capture.collect(day)
            self.assertEqual(result["saved"],1)
            saved=json.loads((Path(tmp)/"prospective_predictions"/(code+".json")).read_text())
        self.assertEqual(calls.call_count,2)
        generated=datetime.fromisoformat(saved["generated_at"])
        self.assertGreaterEqual(generated,max(received))
        self.assertEqual(saved["race_code"],code)
        self.assertIs(saved["formal"],False)
        self.assertIs(saved["scoring"],False)

    def test_daily_csv_http_failure_uses_pre_race_fallback_without_formal_promotion(self):
        day="20990101"
        code=day+"0404"
        titles=[{"レースコード":code,"電話投票締切予定":"23:59"}]
        cards=[{"レースコード":code,**{f"艇{i}_全国勝率":"5.1" for i in range(1,7)}}]
        received=datetime.now(JST)
        with tempfile.TemporaryDirectory() as tmp, \
             patch.object(capture,"STORE",Path(tmp)/"prospective_predictions"), \
             patch.object(capture,"read_rows",side_effect=OSError("daily CSV unavailable")) as primary, \
             patch("clean_openapi_sources.load",return_value=(titles,cards,received,"d"*64,
                 {"source":"nonofficial_openapi_v1","valid":1,"rejected":0})) as alternate, \
             patch.object(capture,"model_provenance",return_value={"model_git_sha":"a"*40}):
            result=capture.collect(day)
            saved=json.loads((Path(tmp)/"prospective_predictions"/(code+".json")).read_text())
        self.assertEqual(result["saved"],1)
        self.assertEqual(primary.call_count,1)
        alternate.assert_called_once_with(day)
        self.assertEqual(saved["input_source_kind"],"nonofficial_openapi_v1")
        self.assertEqual(saved["source_title_sha256"],"d"*64)
        self.assertEqual(saved["source_cards_sha256"],"d"*64)
        self.assertGreaterEqual(datetime.fromisoformat(saved["generated_at"]),received)
        self.assertIs(saved["formal"],False)
        self.assertIs(saved["scoring"],False)

    def test_primary_bad_data_does_not_silently_fall_back(self):
        day="20990101"
        with patch.object(capture,"read_rows",side_effect=ValueError("source too large")), \
             patch("clean_openapi_sources.load") as alternate:
            with self.assertRaisesRegex(ValueError,"source too large"):
                capture.collect(day)
        alternate.assert_not_called()

    def test_missing_csv_and_missing_alt_are_not_fabricated_success(self):
        day="20990101"
        with patch.object(capture,"read_rows",side_effect=OSError("daily 404")), \
             patch("clean_openapi_sources.load",side_effect=ValueError("no_valid_races")):
            with self.assertRaisesRegex(ValueError,"no_valid_races"):
                capture.collect(day)

    def test_successful_freeze_push_dispatches_existing_audit_only_once(self):
        workflow=(Path(__file__).resolve().parent/".github/workflows/clean-prospective.yml").read_text(encoding="utf-8")
        audit=(Path(__file__).resolve().parent/".github/workflows/clean-prospective-evaluation.yml").read_text(encoding="utf-8")
        self.assertIn("actions: write",workflow)
        self.assertIn("GH_TOKEN: ${{ github.token }}",workflow)
        self.assertIn("workflow_dispatch:",audit)
        # A capture with zero additions or a failed push must never claim audit dispatch.
        success=workflow.index("if git push origin HEAD:main; then")
        dispatch=workflow.index("gh workflow run clean-prospective-evaluation.yml --ref main")
        marker=workflow.index("PROSPECTIVE_FIRST_ADD_AUDIT_DISPATCHED")
        retry=workflow.index('if [ "$attempt" -eq 3 ]; then',success)
        self.assertLess(success,dispatch)
        self.assertLess(dispatch,marker)
        self.assertLess(marker,retry)
        self.assertEqual(workflow.count("gh workflow run clean-prospective-evaluation.yml --ref main"),1)

    def test_duplicate_inputs_rejected(self):
        now=datetime(2026,10,28,10,0,tzinfo=JST)
        row={"レースコード":"202610281201","電話投票締切予定":"14:00"}
        card={"レースコード":"202610281201",**{f"艇{i}_全国勝率":"5.1" for i in range(1,7)}}
        self.assertEqual(build("20261028",[row,row],[card],now,now,"a","b",now,{}),{})

if __name__=="__main__":
    unittest.main()

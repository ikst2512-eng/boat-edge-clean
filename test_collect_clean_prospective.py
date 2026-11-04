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
             patch.object(capture,"supplement_unlisted",return_value={}), \
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
             patch.object(capture,"supplement_unlisted",return_value={}), \
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

    def test_empty_published_daily_csv_uses_pre_race_alternate(self):
        day="20990101"
        code=day+"0404"
        titles=[{"レースコード":code,"電話投票締切予定":"23:59"}]
        cards=[{"レースコード":code,**{f"艇{i}_全国勝率":"5.1" for i in range(1,7)}}]
        received=datetime.now(JST)
        with tempfile.TemporaryDirectory() as tmp, \
             patch.object(capture,"STORE",Path(tmp)/"prospective_predictions"), \
             patch.object(capture,"read_rows",return_value=([],received,"a"*64)) as primary, \
             patch("clean_openapi_sources.load",return_value=(titles,cards,received,"b"*64,
                 {"source":"nonofficial_openapi_v1"})) as alternate, \
             patch.object(capture,"supplement_unlisted",return_value={}), \
             patch.object(capture,"model_provenance",return_value={}):
            output=capture.collect(day)
        self.assertEqual(output["saved"],1)
        self.assertEqual(primary.call_count,2)
        alternate.assert_called_once_with(day)

    def test_nonmatching_daily_race_lists_use_alternate(self):
        day="20990101"
        target=day+"0404"
        t=datetime.now(JST)
        daily_titles=[{"レースコード":day+"0101","電話投票締切予定":"23:59"}]
        daily_cards=[{"レースコード":day+"0202","艇1_全国勝率":"5.1"}]
        alternate_titles=[{"レースコード":target,"電話投票締切予定":"23:59"}]
        alternate_cards=[{"レースコード":target,**{f"艇{i}_全国勝率":"5.1" for i in range(1,7)}}]
        def primary(url):
            return (daily_titles if "/title/" in url else daily_cards),t,"a"*64
        with tempfile.TemporaryDirectory() as tmp, \
             patch.object(capture,"STORE",Path(tmp)/"prospective_predictions"), \
             patch.object(capture,"read_rows",side_effect=primary) as fetch, \
             patch("clean_openapi_sources.load",return_value=(
                 alternate_titles,alternate_cards,t,"b"*64,{"source":"nonofficial_openapi_v1"})) as fallback, \
             patch.object(capture,"supplement_unlisted",return_value={}), \
             patch.object(capture,"model_provenance",return_value={}):
            result=capture.collect(day)
            saved=json.loads((Path(tmp)/"prospective_predictions"/(target+".json")).read_text())
        self.assertEqual(fetch.call_count,2)
        fallback.assert_called_once_with(day)
        self.assertEqual(result["saved"],1)
        self.assertEqual(saved["race_code"],target)
        self.assertEqual(saved["input_source_kind"],"nonofficial_openapi_v1")
        self.assertEqual(saved["source_title_sha256"],"b"*64)
        self.assertEqual(saved["source_cards_sha256"],"b"*64)
        self.assertGreaterEqual(datetime.fromisoformat(saved["generated_at"]),t)
        self.assertFalse(saved["formal"])
        self.assertFalse(saved["scoring"])

    def test_zero_candidate_run_reports_source_coverage_without_certification(self):
        import io
        day="20000101"
        code=day+"0101"
        title=[{"レースコード":code,"電話投票締切予定":"15:00"}]
        cards=[{"レースコード":code,**{f"艇{i}_全国勝率":"5.1" for i in range(1,7)}}]
        def primary(url):
            return (title if "/title/" in url else cards),datetime.now(JST),"a"*64
        error=io.StringIO()
        with tempfile.TemporaryDirectory() as tmp, \
             patch.object(capture,"STORE",Path(tmp)/"prospective_predictions"), \
             patch.object(capture,"read_rows",side_effect=primary), \
             patch.object(capture,"supplement_unlisted",return_value={}), \
             patch.object(capture,"model_provenance",return_value={}), \
             patch("sys.stderr",error):
            result=capture.collect(day)
        self.assertEqual(result["saved"],0)
        self.assertEqual(result["eligible"],0)
        self.assertIn("PROSPECTIVE_CAPTURE_ZERO ",error.getvalue())
        diagnostic=json.loads(error.getvalue().split("PROSPECTIVE_CAPTURE_ZERO ",1)[1])
        self.assertEqual(diagnostic["matching_race_codes"],1)
        self.assertEqual(diagnostic["source_kind"],"public_pre_race_csv")
        self.assertEqual(diagnostic["reason"],"no_pre_cutoff_eligible_races")
        self.assertIs(diagnostic["formal"],False)

    def test_partial_daily_csv_is_supplemented_only_by_complete_direct_pairs(self):
        import hashlib
        day="20990101"
        a,b,c=(day+"0101",day+"0102",day+"0103")
        t=datetime.now(JST)
        primary_titles=[{"レースコード":a,"電話投票締切予定":"23:59"},
                        {"レースコード":b,"電話投票締切予定":"23:59"}]
        primary_cards=[{"レースコード":a,**{f"艇{i}_全国勝率":"4.1" for i in range(1,7)}}]
        holding=primary_titles+[{"レースコード":c,"電話投票締切予定":"23:59"}]
        direct_cards=[{"レースコード":code,**{f"艇{i}_全国勝率":"5.1" for i in range(1,7)}}
                      for code in (b,c)]
        def read(url):
            rows=primary_titles if "/title/" in url else primary_cards
            return rows,t,("a" if "/title/" in url else "b")*64
        with tempfile.TemporaryDirectory() as tmp, \
             patch.object(capture,"STORE",Path(tmp)/"prospective_predictions"), \
             patch.object(capture,"read_rows",side_effect=read), \
             patch("clean_direct_sources.holding_rows",return_value=(holding,t,"c"*64)) as holding_get, \
             patch("clean_direct_sources.direct_cards",return_value=(
                 direct_cards,t,"x"*64,{b:"d"*64,c:"e"*64},{})) as card_get, \
             patch.object(capture,"model_provenance",return_value={}):
            result=capture.collect(day)
            records={code:json.loads((Path(tmp)/"prospective_predictions"/(code+".json")).read_text())
                     for code in (a,b,c)}
        self.assertEqual(result["saved"],3)
        holding_get.assert_called_once_with(day)
        self.assertEqual([r["レースコード"] for r in card_get.call_args.args[1]],[b,c])
        self.assertEqual(card_get.call_args.kwargs["limit"],12)
        self.assertEqual(records[a]["input_source_kind"],"public_pre_race_csv")
        self.assertEqual(records[a]["source_title_sha256"],"a"*64)
        self.assertEqual(records[a]["source_cards_sha256"],"b"*64)
        for code,card_sha in ((b,"d"*64),(c,"e"*64)):
            record=records[code]
            self.assertEqual(record["input_source_kind"],"direct_race_specific_pre_race")
            self.assertEqual(record["source_title_sha256"],"c"*64)
            self.assertEqual(record["source_cards_sha256"],card_sha)
            self.assertEqual(record["input_sha256"],
                hashlib.sha256(("c"*64+":"+card_sha).encode()).hexdigest())
            self.assertGreaterEqual(datetime.fromisoformat(record["generated_at"]),t)
            self.assertIs(record["formal"],False)
            self.assertIs(record["scoring"],False)

    def test_partial_daily_deadline_conflict_is_never_supplemented(self):
        day="20990101"
        a,b=day+"0101",day+"0102"
        t=datetime.now(JST)
        titles=[{"レースコード":code,"電話投票締切予定":"23:59"} for code in (a,b)]
        cards=[{"レースコード":a,**{f"艇{i}_全国勝率":"5.1" for i in range(1,7)}}]
        holding=[{"レースコード":b,"電話投票締切予定":"23:58"}]
        def primary(url):
            return (titles if "/title/" in url else cards),t,"a"*64
        with tempfile.TemporaryDirectory() as tmp, \
             patch.object(capture,"STORE",Path(tmp)/"prospective_predictions"), \
             patch.object(capture,"read_rows",side_effect=primary), \
             patch("clean_direct_sources.holding_rows",return_value=(holding,t,"b"*64)), \
             patch("clean_direct_sources.direct_cards") as cards_get, \
             patch.object(capture,"model_provenance",return_value={}):
            result=capture.collect(day)
            saved=[p.stem for p in (Path(tmp)/"prospective_predictions").glob("*.json")]
        self.assertEqual(result["saved"],1)
        self.assertEqual(saved,[a])
        cards_get.assert_not_called()

    def test_duplicate_primary_rows_are_not_masked_by_direct_supplement(self):
        day="20990101"
        code=day+"0101"
        t=datetime.now(JST)
        title={"レースコード":code,"電話投票締切予定":"23:59"}
        card={"レースコード":code,**{f"艇{i}_全国勝率":"5.1" for i in range(1,7)}}
        for titles,cards in (([title,title],[card]),([], [card,card])):
            with self.subTest(titles=len(titles),cards=len(cards)), \
                 tempfile.TemporaryDirectory() as tmp, \
                 patch.object(capture,"STORE",Path(tmp)/"prospective_predictions"), \
                 patch("clean_direct_sources.holding_rows",return_value=([title],t,"a"*64)), \
                 patch("clean_direct_sources.direct_cards") as card_get:
                supplemented=capture.supplement_unlisted(day,titles,cards,{}, {})
            self.assertEqual(supplemented,{})
            card_get.assert_not_called()

    def test_partial_daily_supplement_outage_does_not_erase_primary(self):
        day="20990101"
        code=day+"0101"
        t=datetime.now(JST)
        titles=[{"レースコード":code,"電話投票締切予定":"23:59"}]
        cards=[{"レースコード":code,**{f"艇{i}_全国勝率":"5.1" for i in range(1,7)}}]
        def primary(url):
            return (titles if "/title/" in url else cards),t,"a"*64
        with tempfile.TemporaryDirectory() as tmp, \
             patch.object(capture,"STORE",Path(tmp)/"prospective_predictions"), \
             patch.object(capture,"read_rows",side_effect=primary), \
             patch("clean_direct_sources.holding_rows",side_effect=OSError("supplement unavailable")), \
             patch.object(capture,"model_provenance",return_value={}):
            result=capture.collect(day)
            saved=(Path(tmp)/"prospective_predictions"/(code+".json")).is_file()
        self.assertEqual(result["saved"],1)
        self.assertTrue(saved)

    def test_supplement_all_card_failures_with_no_primary_candidate_is_not_zero(self):
        # One old matched CSV pair does not make a failed future direct
        # card fetch a legitimate no-op. The existing cutoff still governs.
        day=datetime.now(JST).strftime("%Y%m%d")
        old,future=day+"0101",day+"0102"
        now=datetime.now(JST)
        titles=[{"レースコード":old,"電話投票締切予定":"00:01"}]
        cards=[{"レースコード":old,**{
            f"艇{i}_全国勝率":"5.1" for i in range(1,7)}}]
        holding=[{"レースコード":future,"電話投票締切予定":"23:59"}]
        def primary(url):
            return (titles if "/title/" in url else cards),now,"a"*64
        with tempfile.TemporaryDirectory() as tmp, \
             patch.object(capture,"STORE",Path(tmp)/"prospective_predictions"), \
             patch.object(capture,"read_rows",side_effect=primary), \
             patch("clean_direct_sources.holding_rows",
                   return_value=(holding,now,"b"*64)), \
             patch("clean_direct_sources.direct_cards",
                   return_value=([],now,"",{},{"HTTPError":1})) as fetch, \
             patch.object(capture,"model_provenance",return_value={}):
            with self.assertRaisesRegex(
                    ValueError,"supplement_all_card_fetches_failed"):
                capture.collect(day)
            self.assertFalse(
                list((Path(tmp)/"prospective_predictions").glob("*.json")))
        fetch.assert_called_once()

    def test_supplement_empty_without_card_errors_remains_safe_zero(self):
        day=datetime.now(JST).strftime("%Y%m%d")
        old,future=day+"0101",day+"0102"
        now=datetime.now(JST)
        titles=[{"レースコード":old,"電話投票締切予定":"00:01"}]
        cards=[{"レースコード":old,**{
            f"艇{i}_全国勝率":"5.1" for i in range(1,7)}}]
        holding=[{"レースコード":future,"電話投票締切予定":"23:59"}]
        def primary(url):
            return (titles if "/title/" in url else cards),now,"a"*64
        with tempfile.TemporaryDirectory() as tmp, \
             patch.object(capture,"STORE",Path(tmp)/"prospective_predictions"), \
             patch.object(capture,"read_rows",side_effect=primary), \
             patch("clean_direct_sources.holding_rows",
                   return_value=(holding,now,"b"*64)), \
             patch("clean_direct_sources.direct_cards",
                   return_value=([],now,"",{},{})), \
             patch.object(capture,"model_provenance",return_value={}):
            result=capture.collect(day)
            self.assertEqual((result["saved"],result["eligible"]),(0,0))

    def test_supplement_direct_card_failure_preserves_valid_primary(self):
        day="20990101"
        a,b=day+"0101",day+"0102"
        now=datetime.now(JST)
        titles=[{"レースコード":a,"電話投票締切予定":"23:59"}]
        cards=[{"レースコード":a,**{
            f"艇{i}_全国勝率":"5.1" for i in range(1,7)}}]
        holding=[{"レースコード":b,"電話投票締切予定":"23:59"}]
        def primary(url):
            return (titles if "/title/" in url else cards),now,"a"*64
        with tempfile.TemporaryDirectory() as tmp, \
             patch.object(capture,"STORE",Path(tmp)/"prospective_predictions"), \
             patch.object(capture,"read_rows",side_effect=primary), \
             patch("clean_direct_sources.holding_rows",
                   return_value=(holding,now,"b"*64)), \
             patch("clean_direct_sources.direct_cards",
                   return_value=([],now,"",{},{"TimeoutError":1})), \
             patch.object(capture,"model_provenance",return_value={}):
            result=capture.collect(day)
            self.assertEqual(result["saved"],1)
            self.assertTrue(
                (Path(tmp)/"prospective_predictions"/(a+".json")).is_file())

    def test_direct_source_only_after_both_daily_sources_unavailable(self):
        day="20990101"
        code=day+"0404"
        t=datetime.now(JST)
        titles=[{"レースコード":code,"電話投票締切予定":"23:59"}]
        cards=[{"レースコード":code,**{f"艇{i}_全国勝率":"5.1" for i in range(1,7)}}]
        with tempfile.TemporaryDirectory() as tmp, \
             patch.object(capture,"STORE",Path(tmp)/"prospective_predictions"), \
             patch.object(capture,"read_rows",side_effect=OSError("daily HTTP 404")), \
             patch("clean_openapi_sources.load",side_effect=ValueError("no_valid_races")), \
             patch("clean_direct_sources.holding_rows",return_value=(titles,t,"a"*64)) as holding, \
             patch("clean_direct_sources.direct_cards",return_value=(
                 cards,t,"c"*64,{code:"b"*64},{})) as direct, \
             patch.object(capture,"model_provenance",return_value={}):
            output=capture.collect(day)
            saved=json.loads((Path(tmp)/"prospective_predictions"/(code+".json")).read_text())
        holding.assert_called_once_with(day)
        self.assertEqual(direct.call_args.args[:2],(day,titles))
        self.assertEqual(output["saved"],1)
        self.assertEqual(saved["input_source_kind"],"direct_race_specific_pre_race")
        self.assertEqual(saved["source_title_sha256"],"a"*64)
        self.assertEqual(saved["source_cards_sha256"],"b"*64)
        self.assertEqual(saved["input_sha256"],__import__("hashlib").sha256(
            ("a"*64+":"+"b"*64).encode()).hexdigest())
        self.assertGreaterEqual(datetime.fromisoformat(saved["generated_at"]),t)
        self.assertFalse(saved["formal"])
        self.assertFalse(saved["scoring"])

    def test_direct_fallback_all_already_frozen_is_zero_not_failed(self):
        day="20990101"
        code=day+"0404"
        t=datetime.now(JST)
        titles=[{"レースコード":code,"電話投票締切予定":"23:59"}]
        with tempfile.TemporaryDirectory() as tmp:
            store=Path(tmp)/"prospective_predictions"
            store.mkdir()
            original=store/(code+".json")
            original.write_text(json.dumps({"race_code":code,"status":"prospective_candidate"}))
            frozen=original.read_bytes()
            with patch.object(capture,"STORE",store), \
                 patch.object(capture,"read_rows",side_effect=OSError("daily unavailable")), \
                 patch("clean_openapi_sources.load",side_effect=ValueError("no_valid_races")), \
                 patch("clean_direct_sources.holding_rows",return_value=(titles,t,"a"*64)), \
                 patch("clean_direct_sources.direct_cards",return_value=(
                     [],t,"",{},{})) as direct, \
                 patch.object(capture,"model_provenance",return_value={}):
                output=capture.collect(day)
            self.assertEqual(output["saved"],0)
            self.assertEqual(output["eligible"],0)
            self.assertEqual(original.read_bytes(),frozen)
            self.assertEqual(direct.call_args.kwargs["existing_codes"],{code})
            self.assertEqual(direct.call_args.kwargs["limit"],18)

    def test_direct_fallback_failed_card_fetch_is_not_silent_zero(self):
        day="20990101"
        code=day+"0404"
        t=datetime.now(JST)
        titles=[{"レースコード":code,"電話投票締切予定":"23:59"}]
        with tempfile.TemporaryDirectory() as tmp, \
             patch.object(capture,"STORE",Path(tmp)/"prospective_predictions"), \
             patch.object(capture,"read_rows",side_effect=OSError("daily unavailable")), \
             patch("clean_openapi_sources.load",side_effect=ValueError("no_valid_races")), \
             patch("clean_direct_sources.holding_rows",return_value=(titles,t,"a"*64)), \
             patch("clean_direct_sources.direct_cards",return_value=(
                 [],t,"",{},{"HTTPError":1})), \
             patch.object(capture,"model_provenance",return_value={}):
            with self.assertRaisesRegex(ValueError,"all_pre_race_sources_unavailable"):
                capture.collect(day)

    def test_invalid_alternate_response_never_invokes_direct_source(self):
        day="20990101"
        with patch.object(capture,"read_rows",side_effect=OSError("daily HTTP 404")), \
             patch("clean_openapi_sources.load",side_effect=ValueError("stadiums_invalid")), \
             patch("clean_direct_sources.holding_rows") as direct:
            with self.assertRaisesRegex(ValueError,"stadiums_invalid"):
                capture.collect(day)
        direct.assert_not_called()

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
             patch("clean_openapi_sources.load",side_effect=ValueError("no_valid_races")), \
             patch("clean_direct_sources.holding_rows",side_effect=OSError("direct source 404")):
            with self.assertRaisesRegex(ValueError,"all_pre_race_sources_unavailable"):
                capture.collect(day)

    def test_workflow_archives_actual_source_http_bytes_without_certification(self):
        import hashlib
        import os
        from four_mode_raw_receipt import preserve
        workflow=(Path(__file__).resolve().parent/".github/workflows/clean-prospective.yml").read_text(encoding="utf-8")
        capture_step=workflow.split("      - name: Capture if public race cards are already published",1)[1].split("      - name: Freeze immutable candidate evidence",1)[0]
        archive_step=workflow.split("      - name: Archive prospective capture diagnostics",1)[1]
        self.assertIn("FOUR_MODE_RAW_RECEIPT_DIR: test-results/prospective-source-originals",capture_step)
        self.assertIn("test-results/prospective-capture.log",archive_step)
        self.assertIn("test-results/prospective-source-originals/",archive_step)
        self.assertIn("if: always() && github.event_name != 'pull_request'",archive_step)
        raw=b'{"raw":"prospective-only"}'
        received=datetime(2026,11,4,12,0,tzinfo=JST)
        url="https://race.boatcast.jp/api_txt/getHoldingList2_20261104.json"
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ,{"FOUR_MODE_RAW_RECEIPT_DIR":tmp}):
            receipt=preserve(url,raw,received)
            manifest_files=list(Path(tmp).glob("*.json"))
            originals=list(Path(tmp).glob("*.bin"))
            self.assertEqual(len(manifest_files),1)
            self.assertEqual(len(originals),1)
            self.assertEqual(originals[0].read_bytes(),raw)
            self.assertEqual(receipt["sha256"],hashlib.sha256(raw).hexdigest())
            self.assertEqual(receipt["received_at_jst"],received.isoformat())
            self.assertIs(receipt["independent_remote_receipt_verified"],False)

    def test_pr_unit_checks_do_not_replace_pending_immutable_collector(self):
        workflow=(Path(__file__).resolve().parent/".github/workflows/clean-prospective.yml").read_text(encoding="utf-8")
        concurrency=workflow.split("concurrency:\n",1)[1].split("\njobs:",1)[0]
        expected=(
            "group: ${{ github.event_name == 'pull_request' && "
            "format('clean-prospective-pr-{0}', github.event.pull_request.number) "
            "|| github.event_name == 'push' && 'clean-prospective-main-push-ci' "
            "|| 'clean-prospective-capture' }}"
        )
        self.assertIn(expected,concurrency)
        self.assertIn("cancel-in-progress: false",concurrency)
        # PR and main push both run unit tests only, never stage/push originals.
        capture=workflow.split("      - name: Capture if public race cards are already published",1)[1].split(
            "      - name: Freeze immutable candidate evidence",1)[0]
        freeze=workflow.split("      - name: Freeze immutable candidate evidence",1)[1].split(
            "      - name: Flag zero daily captures after midday JST",1)[0]
        self.assertIn("if: github.event_name == 'schedule' || github.event_name == 'workflow_dispatch'",capture)
        self.assertIn("if: github.event_name == 'schedule' || github.event_name == 'workflow_dispatch'",freeze)
        self.assertIn("git commit -m 'data: freeze prospective pre-cutoff",freeze)
        # Only schedule/manual recovery keep one immutable writer; main push
        # still wakes the independent watchdog, which may manual-dispatch
        # when a real scheduled slot is missing.
        watchdog=(Path(__file__).resolve().parent/".github/workflows/four-mode-capture-watchdog.yml").read_text()
        self.assertIn("  push:\n    branches: [main]",watchdog)
        self.assertIn("run: python -m scripts.clean_prospective_watchdog",watchdog)
        safe="github.event_name == 'schedule' || github.event_name == 'workflow_dispatch'"
        self.assertIn(safe,workflow.split("      - name: Flag zero daily captures after midday JST",1)[1])
        self.assertIn(safe,workflow.split("      - name: Archive prospective capture diagnostics",1)[1])
        self.assertIn("git -c rebase.autoStash=true rebase origin/main",freeze)
        self.assertIn("Post-rebase candidate receipt buffer expired; refusing late push:",freeze)
        # No extra schedule, no T-12 relaxation.
        self.assertIn("  schedule:",workflow)
        self.assertIn("  workflow_dispatch:",workflow)
        self.assertIn("  push:",workflow)

    def test_precommit_freeze_blocks_unknown_source_and_untrusted_digest(self):
        workflow=(Path(__file__).resolve().parent/".github/workflows/clean-prospective.yml").read_text(encoding="utf-8")
        self.assertIn("kind not in ('public_pre_race_csv','nonofficial_openapi_v1','direct_race_specific_pre_race')",workflow)
        self.assertIn("Candidate source digest inconsistency: ",workflow)
        self.assertIn("Candidate is not research-only: ",workflow)
        self.assertIn("hashlib.sha256((title_sha+':'+cards_sha).encode()).hexdigest()",workflow)
        self.assertIn("kind=='nonofficial_openapi_v1' and title_sha!=cards_sha",workflow)
        self.assertLess(workflow.index("Candidate source digest inconsistency: "),workflow.index("git commit -m 'data: freeze prospective pre-cutoff"))

    def test_precommit_freeze_executes_race_identity_day_and_jst_gates(self):
        # Exercise the exact embedded pre-commit validator in an isolated
        # staged Git repository, not just a source-string assertion.
        import hashlib
        import subprocess
        import sys
        import textwrap
        workflow=(Path(__file__).resolve().parent/".github/workflows/clean-prospective.yml").read_text(encoding="utf-8")
        precommit=workflow.split("          python - <<'PY'\n",1)[1].split("\n          PY",1)[0]
        script=textwrap.dedent(precommit)
        self.assertIn("Invalid candidate race identity:",script)
        self.assertIn("Candidate deadline does not match race day:",script)
        self.assertIn("Candidate source/deadline must be JST:",script)
        tickets=["1-2-3","1-2-4","1-3-2","1-3-4","1-4-2",
                 "1-4-3","2-1-3","2-1-4","2-3-1","2-3-4"]
        a,b="a"*64,"b"*64
        base={
            "race_code":"209901010104",
            "predictions":tickets,"status":"prospective_candidate",
            "validated":False,"formal":False,"scoring":False,
            "input_source_kind":"public_pre_race_csv",
            "source_title_sha256":a,"source_cards_sha256":b,
            "input_sha256":hashlib.sha256((a+":"+b).encode()).hexdigest(),
            "source_deadline_jst":"2099-01-01T23:59:00+09:00",
            "cutoff_jst":"2099-01-01T23:47:00+09:00",
            "source_title_received_jst":"2099-01-01T20:00:00+09:00",
            "source_cards_received_jst":"2099-01-01T20:01:00+09:00",
            "generated_at":"2099-01-01T20:02:00+09:00",
        }
        cases=[
            ({},None),
            ({"race_code":"209901012504"},"Invalid candidate race identity"),
            ({"race_code":"209901010113"},"Invalid candidate race identity"),
            ({"source_deadline_jst":"2099-01-02T23:59:00+09:00"},"Candidate deadline does not match race day"),
            ({"generated_at":"2099-01-01T20:02:00+00:00"},"Candidate source/deadline must be JST"),
        ]
        for update,error in cases:
            with self.subTest(update=update),tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp)
                target=root/"prospective_predictions"/(update.get("race_code",base["race_code"])+".json")
                target.parent.mkdir(parents=True)
                target.write_text(json.dumps({**base,**update}),encoding="utf-8")
                subprocess.run(["git","init","-q"],cwd=root,check=True)
                subprocess.run(["git","add","--","prospective_predictions/"],cwd=root,check=True)
                result=subprocess.run([sys.executable,"-c",script],cwd=root,
                                      capture_output=True,text=True)
                if error:
                    self.assertNotEqual(result.returncode,0,result.stdout)
                    self.assertIn(error,result.stderr+result.stdout)
                else:
                    self.assertEqual(result.returncode,0,result.stderr)
                    self.assertIn('"eligible_for_commit": 1',result.stdout)

    def test_post_rebase_receipt_gate_rechecks_actual_new_git_blob(self):
        # Execute the exact workflow post-rebase gate on real Git commits.
        # Successful pre-rebase checks do not prove the late push is safe.
        import subprocess
        import sys
        import textwrap
        from datetime import timedelta
        workflow=(Path(__file__).resolve().parent/".github/workflows/clean-prospective.yml").read_text(encoding="utf-8")
        rebase=workflow.index("git -c rebase.autoStash=true rebase origin/main")
        gate=workflow.index("PROSPECTIVE_POST_REBASE_GATE",rebase)
        push=workflow.index("if git push origin HEAD:main; then",rebase)
        self.assertLess(rebase,gate)
        self.assertLess(gate,push)
        code=workflow[rebase:].split("            python - <<'PY'\n",1)[1].split("\n          PY",1)[0]
        script=textwrap.dedent(code)
        now=datetime.now(JST)
        cases=[
            ("valid", (now+timedelta(minutes=10)).isoformat(), None),
            ("expired", (now+timedelta(seconds=30)).isoformat(),
             "Post-rebase candidate receipt buffer expired"),
            ("wrong_timezone", (now+timedelta(minutes=10)).astimezone(
                __import__("datetime").timezone.utc).isoformat(),
             "Non-JST cutoff after rebase"),
            ("no_additions", None, "No immutable candidate additions after rebase"),
        ]
        for name,cutoff,error in cases:
            with self.subTest(name=name),tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp)
                def git(*args):
                    return subprocess.run(
                        ["git",*args],cwd=root,check=True,capture_output=True,text=True)
                git("init","-q")
                git("config","user.name","Test collector")
                git("config","user.email","test@example.invalid")
                (root/"README.md").write_text("base",encoding="utf-8")
                git("add","README.md")
                git("commit","-qm","initial")
                if cutoff is None:
                    (root/"another.txt").write_text("not a prediction",encoding="utf-8")
                    git("add","another.txt")
                else:
                    target=root/"prospective_predictions"/"209901010101.json"
                    target.parent.mkdir(parents=True)
                    target.write_text(json.dumps({"cutoff_jst":cutoff}),encoding="utf-8")
                    git("add","prospective_predictions/")
                git("commit","-qm","candidate")
                check=subprocess.run([sys.executable,"-c",script],cwd=root,
                                     capture_output=True,text=True)
                if error:
                    self.assertNotEqual(check.returncode,0,check.stdout)
                    self.assertIn(error,check.stderr+check.stdout)
                else:
                    self.assertEqual(check.returncode,0,check.stderr)
                    self.assertIn("PROSPECTIVE_POST_REBASE_GATE",check.stdout)
                    self.assertIn('"eligible_for_push": 1',check.stdout)

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

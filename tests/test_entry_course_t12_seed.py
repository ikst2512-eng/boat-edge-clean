import json
import tempfile
import unittest
from datetime import datetime,timezone,timedelta
from pathlib import Path
from entry_course_t12_seed import near_t12,seed_once,validate_base,publish_base
from entry_course_collector import candidates
from research_model import probabilities

JST=timezone(timedelta(hours=9))
NOW=datetime(2026,11,3,18,15,tzinfo=JST)
CODE="202611030708"

def base():
    rates=[5.5,6.0,6.3,4.9,5.2,5.7]
    return {"race_code":CODE,"status":"research","validated":False,
        "model_version":"national-beta0.4-exploratory-v1",
        "generated_at":NOW.isoformat(),
        "source_deadline_jst":"2026-11-03T18:33:00+09:00",
        "cutoff_jst":"2026-11-03T18:21:00+09:00",
        "source_title_received_jst":NOW.isoformat(),
        "source_cards_received_jst":NOW.isoformat(),
        "national_win_rates":rates,
        "predictions":["-".join(map(str,t)) for t,p in probabilities(rates)[:10]],
        "source_title_sha256":"a"*64,"source_cards_sha256":"b"*64,
        "input_sha256":"c"*64,"model_source_sha256":"d"*64}
def raw():
    return (json.dumps(base(),ensure_ascii=False,sort_keys=True)+"\n").encode()
def title():
    return ("レースコード,電話投票締切予定\n"+CODE+",18:33\n").encode()

class T12SeedTests(unittest.TestCase):
    def test_both_missing_morning_schedules_use_existing_pre_race_openapi(self):
        from unittest.mock import patch
        from urllib.error import HTTPError
        from entry_course_t12_seed import _title
        unavailable=HTTPError("https://source.example",404,"not yet published",None,None)
        rows=[{"レースコード":CODE,"電話投票締切予定":"18:33"}]
        cards=[dict({"レースコード":CODE},
                    **{f"艇{i}_全国勝率":"5.5" for i in range(1,7)})]
        alt=(rows,cards,NOW,"e"*64,
             {"source":"nonofficial_openapi_v1"})
        with (patch("entry_course_t12_seed.urlopen",side_effect=unavailable),
              patch("clean_direct_sources.holding_rows",side_effect=unavailable),
              patch("clean_openapi_sources.load",return_value=alt) as fallback):
            found,day,digest,source=_title(NOW)
        self.assertEqual(found,rows)
        self.assertEqual(day,"20261103")
        self.assertEqual(digest,"e"*64)
        self.assertEqual(source,"nonofficial_openapi_v1")
        fallback.assert_called_once_with("20261103")

    def test_morning_alternative_receipt_cannot_be_future_or_unverified(self):
        from unittest.mock import patch
        from urllib.error import HTTPError
        from entry_course_t12_seed import _title
        unavailable=HTTPError("https://source.example",404,"not yet published",None,None)
        rows=[{"レースコード":CODE,"電話投票締切予定":"18:33"}]
        cards=[{"レースコード":CODE}]
        for arrived,digest in [
            (NOW+timedelta(minutes=1),"e"*64),
            (NOW,"invalid"),
        ]:
            with self.subTest(received=arrived,digest=digest):
                with (patch("entry_course_t12_seed.urlopen",side_effect=unavailable),
                      patch("clean_direct_sources.holding_rows",side_effect=unavailable),
                      patch("clean_openapi_sources.load",return_value=(
                          rows,cards,arrived,digest,
                          {"source":"nonofficial_openapi_v1"}))):
                    with self.assertRaisesRegex(ValueError,"alt_pre_race_schedule_receipt_invalid"):
                        _title(NOW)

    def test_all_morning_pre_race_sources_unavailable_fails_closed(self):
        from unittest.mock import patch
        from urllib.error import HTTPError
        from entry_course_t12_seed import _title
        unavailable=HTTPError("https://source.example",404,"not yet published",None,None)
        with (patch("entry_course_t12_seed.urlopen",side_effect=unavailable),
              patch("clean_direct_sources.holding_rows",side_effect=unavailable),
              patch("clean_openapi_sources.load",side_effect=unavailable)):
            with self.assertRaisesRegex(ValueError,"t12_all_pre_race_schedules_unavailable"):
                _title(NOW)

    def test_missing_published_title_uses_timestamped_live_holding_list(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);store={}
            def save(code):return root/(code+".json")
            def predictor(day,venue,race):save(CODE).write_bytes(raw())
            out=seed_once(now=lambda:NOW,
                fetch_title=lambda url:(_ for _ in ()).throw(OSError("daily CSV not published")),
                fallback_title=lambda day:(
                    [{"レースコード":CODE,"電話投票締切予定":"18:33"}],
                    NOW,"e"*64),
                predictor=predictor,record_path=save,
                ledger_ops=(store.get,lambda key,value:store.setdefault(key,value)))
            self.assertEqual(out["title_schedule_source"],"live_holding_schedule")
            self.assertEqual(out["stored_count"],1)
            self.assertEqual(out["newly_stored_count"],1)
            self.assertEqual(out["reused_count"],0)
            self.assertEqual(store["t12_baselines/20261103/"+CODE+".json"],raw())
    def test_bad_live_holding_timestamp_is_not_used(self):
        with self.assertRaisesRegex(ValueError,"live_schedule_receipt_invalid"):
            seed_once(now=lambda:NOW,
                fetch_title=lambda url:(_ for _ in ()).throw(OSError("daily missing")),
                fallback_title=lambda day:(
                    [{"レースコード":CODE,"電話投票締切予定":"18:33"}],
                    NOW+timedelta(minutes=2),"e"*64),
                predictor=lambda *a:self.fail("future schedule not allowed"),
                ledger_ops=(lambda p:None,lambda p,b:self.fail("not allowed")))
    def test_bad_csv_schema_does_not_silently_switch_source(self):
        with self.assertRaisesRegex(ValueError,"t12_title_source_schema_invalid"):
            seed_once(now=lambda:NOW,fetch_title=lambda url:b"foo,bar\n1,2\n",
                fallback_title=lambda day:self.fail("malformed published source must fail"))
    def test_partial_published_title_is_supplemented_without_mutating_original(self):
        more="202611030709"
        with tempfile.TemporaryDirectory() as tmp:
            store={}
            root=Path(tmp)
            original=(f"レースコード,電話投票締切予定\n202611030101,15:20\n").encode()
            seen=[]
            def saver(code):return root/(code+".json")
            def make(day,venue,race):
                seen.append(day+venue+race)
                d=base();d["race_code"]=more
                saver(more).write_bytes(json.dumps(d).encode())
            output=seed_once(now=lambda:NOW,fetch_title=lambda url:original,
                fallback_title=lambda day:(
                    [{"レースコード":"202611030101","電話投票締切予定":"15:20"},
                     {"レースコード":more,"電話投票締切予定":"18:33"}],
                    NOW,"a"*64),
                predictor=make,record_path=saver,
                ledger_ops=(store.get,lambda k,v:store.setdefault(k,v)))
            # The live-supplemented race receives a genuine test-fixture
            # archive while the unrelated published race is left untouched.
            self.assertEqual(output["title_schedule_source"],
                             "published_title_plus_live_checked")
            self.assertEqual(output["eligible_count"],1)
            self.assertEqual(seen,[more])
            self.assertEqual(output["stored_count"],1)
            self.assertEqual(output["results"][0]["status"],"new_t12_baseline")
            self.assertIn("t12_baselines/20261103/"+more+".json",store)
    def test_conflicting_deadline_is_not_selected(self):
        partial=(f"レースコード,電話投票締切予定\n{CODE},18:33\n").encode()
        output=seed_once(now=lambda:NOW,
            fetch_title=lambda url:partial,
            fallback_title=lambda day:(
                [{"レースコード":CODE,"電話投票締切予定":"18:36"}],
                NOW,"f"*64),
            predictor=lambda *a:self.fail("conflicted race must never be used"))
        self.assertEqual(output["title_schedule_source"],
                         "published_title_plus_live_checked")
        self.assertEqual(output["eligible_count"],0)
    def test_unavailable_supplement_does_not_hide_valid_archive(self):
        output=seed_once(now=lambda:NOW,fetch_title=lambda url:title(),
            fallback_title=lambda day:(_ for _ in ()).throw(OSError("holding unavailable")),
            predictor=lambda *a:(_ for _ in ()).throw(ValueError("test-stop")),
            ledger_ops=(lambda p:None,lambda p,b:self.fail("not saved")))
        self.assertEqual(output["title_schedule_source"],"published_daily_title")
        self.assertEqual(output["eligible_count"],1)
        self.assertEqual(output["results"][0]["status"],"failed")
    def test_selector_rejects_after_cutoff_and_very_early(self):
        rows=[{"レースコード":CODE,"電話投票締切予定":"18:33"},
              {"レースコード":"202611030709","電話投票締切予定":"18:10"}]
        self.assertEqual(near_t12(rows,"20261103",now=NOW),[CODE])
        self.assertEqual(near_t12(rows,"20261103",
                         now=datetime(2026,11,3,18,22,tzinfo=JST)),[])
        self.assertEqual(near_t12(rows,"20261103",
                         now=datetime(2026,11,3,18,1,tzinfo=JST)),[])
    def test_broader_retry_window_preserves_strict_twelve_minute_cutoff(self):
        rows=[{"レースコード":CODE,"電話投票締切予定":"18:33"}]
        # T−12 is 18:21; discover from 18:07 (14m before) through
        # 18:19 (2m before), then refuse after that. A broad retry
        # window NEVER moves the research cutoff itself.
        for minute in (7,10,15,19):
            self.assertEqual(near_t12(rows,"20261103",
                now=datetime(2026,11,3,18,minute,tzinfo=JST)),[CODE])
        for minute in (6,20,21,22):
            self.assertEqual(near_t12(rows,"20261103",
                now=datetime(2026,11,3,18,minute,tzinfo=JST)),[])
        with self.assertRaisesRegex(ValueError,"missed_cutoff"):
            validate_base(raw(),CODE,
                now=datetime(2026,11,3,18,21,tzinfo=JST))
    def test_scheduled_batch_has_capacity_for_seven_overlapping_day_races(self):
        # Source: immutable published-day deadline snapshot. This is an
        # offline selection-capacity test, NOT evidence any T-12 data existed
        # in real time or was remotely persisted.
        from inspect import signature
        import json
        from pathlib import Path
        day="20261110"
        full=json.loads((Path(__file__).resolve().parent.parent/
                         "schedule_snapshots"/(day+".json")).read_text())
        rows=[]
        for venue in full["venues"]:
            for race in venue["races"]:
                rows.append({
                    "レースコード":day+str(venue["jcd"]).zfill(2)+
                                str(race["race_no"]).zfill(2),
                    "電話投票締切予定":race["deadline"],
                })
        self.assertEqual(len(rows),156)
        sample=datetime(2026,11,10,10,35,tzinfo=JST)
        limited=near_t12(rows,day,now=sample,max_per_run=5)
        complete=near_t12(rows,day,now=sample,max_per_run=10)
        self.assertEqual(len(limited),5)
        self.assertEqual(len(complete),7)
        self.assertTrue(set(limited).issubset(complete))
        # Only seed_once's default cap changes: near_t12 remains selectable
        # and its caller must still enforce strict time-based publication.
        self.assertEqual(signature(seed_once).parameters["max_per_run"].default,10)
        self.assertEqual(len(near_t12(rows,day,now=sample)),5)

    def test_five_simultaneous_research_races_not_truncated_to_four(self):
        rows=[{"レースコード":f"2026110307{i:02d}",
               "電話投票締切予定":clock}
              for i,clock in enumerate(("18:29","18:31","18:33",
                                         "18:35","18:39"),1)]
        selected=near_t12(rows,"20261103",now=NOW)
        self.assertEqual(len(selected),5)
        self.assertEqual(len(near_t12(rows,"20261103",now=NOW,
                                      max_per_run=4)),4)
        self.assertEqual(set(selected),{f"2026110307{i:02d}"
                                         for i in range(1,6)})
    def test_four_overlapping_live_races_not_truncated_to_three(self):
        # The Nov 3 full title schedule has a four-race overlap at 15:55 JST.
        # Retain all four distinct eligible race codes in the same run.
        rows=[{"レースコード":f"2026110307{i:02d}",
               "電話投票締切予定":deadline}
              for i,deadline in enumerate(("18:31","18:32","18:33","18:34"),1)]
        selected=near_t12(rows,"20261103",now=NOW)
        self.assertEqual(len(selected),4)
        self.assertEqual(set(selected),{f"2026110307{i:02d}" for i in range(1,5)})
        self.assertEqual(len(near_t12(rows,"20261103",now=NOW,max_per_run=3)),3)
    def test_archives_original_bytes_and_T2_finds_them(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);store={}
            def saved(code):
                return root/(code+".json")
            def predict(day,venue,race):
                saved(CODE).write_bytes(raw())
            result=seed_once(now=lambda:NOW,fetch_title=lambda url:title(),
                predictor=predict,record_path=saved,
                ledger_ops=(store.get,lambda key,data:store.setdefault(key,data)))
            self.assertEqual(result["stored_count"],1)
            key="t12_baselines/20261103/"+CODE+".json"
            self.assertEqual(store[key],raw())
            folder=root/"entry-course-ledger"/"t12_baselines"/"20261103"
            folder.mkdir(parents=True)
            (folder/(CODE+".json")).write_bytes(store[key])
            matching=candidates(root,now=datetime(2026,11,3,18,28,tzinfo=JST))
            self.assertEqual(len(matching),1)
            self.assertEqual(matching[0][1],CODE)
            self.assertEqual(matching[0][2]["predictions"],base()["predictions"])
    def test_repeated_scheduled_run_reuses_original_without_predicting(self):
        with tempfile.TemporaryDirectory() as tmp:
            store={"t12_baselines/20261103/"+CODE+".json":raw()}
            def no_prediction(*args):
                self.fail("already archived: never regenerate")
            first=seed_once(now=lambda:NOW,fetch_title=lambda url:title(),
                predictor=no_prediction,
                record_path=lambda code:self.fail("no local file needed"),
                ledger_ops=(store.get,lambda k,v:self.fail("must not overwrite")))
            self.assertEqual(first["stored_count"],1)
            self.assertEqual(first["newly_stored_count"],0)
            self.assertEqual(first["reused_count"],1)
            self.assertEqual(first["results"][0]["status"],"existing_identical_t12_baseline")
            self.assertEqual(first["results"][0]["sha256"],__import__("hashlib").sha256(raw()).hexdigest())
    def test_existing_wrong_race_rejected_without_overwrite(self):
        bad=base()
        bad["race_code"]="202611030709"
        store={"t12_baselines/20261103/"+CODE+".json":json.dumps(bad).encode()}
        output=seed_once(now=lambda:NOW,fetch_title=lambda url:title(),
            predictor=lambda *args:self.fail("cannot regenerate conflicting evidence"),
            ledger_ops=(store.get,lambda k,v:self.fail("overwrite")))
        self.assertEqual(output["stored_count"],0)
        self.assertEqual(output["results"][0]["status"],"failed")
        self.assertIn("invalid_reference",output["results"][0]["error_code"])
    def test_git_read_after_create_lag_is_bounded_and_never_creates_twice(self):
        from unittest.mock import patch
        payload=raw()
        for failure_kind in ("missing", "transient_api_error"):
            with self.subTest(failure_kind=failure_kind):
                store={}
                calls=[0]
                created=[]
                def read(path):
                    calls[0]+=1
                    # First get is the legitimate pre-create absence.
                    # First two post-PUT reads lag the successful write.
                    if calls[0] in (2,3):
                        if failure_kind=="transient_api_error":
                            raise ValueError("course_ledger_read_failed")
                        return None
                    return store.get(path)
                def create(path,content):
                    self.assertNotIn(path,store)
                    store[path]=content
                    created.append(path)
                with patch("entry_course_t12_seed.sleep",return_value=None) as delay:
                    result=publish_base(payload,CODE,read,create,clock=lambda:NOW)
                self.assertEqual(result["status"],"new_t12_baseline")
                self.assertEqual(len(created),1)
                self.assertEqual(store[result["path"]],payload)
                self.assertEqual(calls[0],4)
                self.assertEqual(delay.call_count,2)

    def test_git_readback_conflicting_bytes_are_rejected_without_retry(self):
        from unittest.mock import patch
        count=[0]
        def read(_):
            count[0]+=1
            return None if count[0]==1 else b"other-payload"
        created=[]
        with patch("entry_course_t12_seed.sleep") as delay:
            with self.assertRaisesRegex(ValueError,"readback_failed"):
                publish_base(raw(),CODE,read,
                    lambda path,content:created.append(path),clock=lambda:NOW)
        self.assertEqual(len(created),1)
        self.assertEqual(count[0],2)
        delay.assert_not_called()

    def test_git_readback_cutoff_crossing_cannot_be_reported_as_timely(self):
        from unittest.mock import patch
        cutoff=datetime(2026,11,3,18,21,tzinfo=JST)
        ticks=iter((NOW,NOW,cutoff))
        created=[]
        with patch("entry_course_t12_seed.sleep",return_value=None) as delay:
            with self.assertRaisesRegex(ValueError,"remote_commit_after_cutoff"):
                publish_base(raw(),CODE,lambda _:None,
                    lambda path,content:created.append(path),
                    clock=lambda:next(ticks))
        self.assertEqual(len(created),1)
        delay.assert_called_once()

    def test_git_readback_persistent_absence_remains_unverified(self):
        from unittest.mock import patch
        created=[]
        with patch("entry_course_t12_seed.sleep",return_value=None) as delay:
            with self.assertRaisesRegex(ValueError,"readback_failed"):
                publish_base(raw(),CODE,lambda _:None,
                    lambda path,content:created.append(path),clock=lambda:NOW)
        self.assertEqual(len(created),1)
        self.assertEqual(delay.call_count,3)

    def test_remote_readback_mutation_blocks_existing_baseline(self):
        calls=[raw(), b"mutated"]
        def read(path):
            return calls.pop(0)
        output=seed_once(now=lambda:NOW,fetch_title=lambda url:title(),
            predictor=lambda *args:self.fail("must not re-predict"),
            ledger_ops=(read,lambda k,v:self.fail("overwrite")))
        self.assertEqual(output["stored_count"],0)
        self.assertEqual(output["results"][0]["status"],"failed")
        self.assertIn("readback_changed",output["results"][0]["error_code"])
    def test_different_generation_deadline_rejected_before_archival(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            def saved(code):return root/(code+".json")
            def predictor(day,venue,race):
                item=base()
                # Same race and valid T−12 source receipts, but the predictor
                # obtained a later deadline from a different pre-race source.
                item["source_deadline_jst"]="2026-11-03T18:34:00+09:00"
                item["cutoff_jst"]="2026-11-03T18:22:00+09:00"
                saved(CODE).write_text(json.dumps(item))
            out=seed_once(now=lambda:NOW,fetch_title=lambda url:title(),
                predictor=predictor,record_path=saved,
                ledger_ops=(lambda path:None,lambda path,raw:self.fail("deadline mismatch must never publish")))
            self.assertEqual(out["stored_count"],0)
            self.assertEqual(out["newly_stored_count"],0)
            self.assertEqual(out["reused_count"],0)
            self.assertEqual(out["results"][0]["status"],"failed")
            self.assertIn("missed_cutoff",out["results"][0]["error_code"])
    def test_existing_original_with_different_deadline_rejected(self):
        archived=base()
        archived["source_deadline_jst"]="2026-11-03T18:34:00+09:00"
        archived["cutoff_jst"]="2026-11-03T18:22:00+09:00"
        old=json.dumps(archived).encode()
        out=seed_once(now=lambda:NOW,fetch_title=lambda url:title(),
            predictor=lambda *args:self.fail("cannot generate over conflicting original"),
            ledger_ops=(lambda path:old,lambda path,data:self.fail("never overwrite")))
        self.assertEqual(out["stored_count"],0)
        self.assertEqual(out["results"][0]["status"],"failed")
        self.assertIn("missed_cutoff",out["results"][0]["error_code"])
    def test_immutable_append_prevents_edited_forecasts(self):
        with self.assertRaisesRegex(ValueError,"immutable_conflict"):
            publish_base(raw(),CODE,lambda path:b"changed",
                         lambda p,d:self.fail("write"),clock=lambda:NOW)
    def test_nov11_first_real_archived_race_is_eligible_in_0825_0830_slots(self):
        # Uses the independently frozen Nov 11 racecard's *scheduled* time;
        # this is a clock-selection regression, NOT a real schedule run or
        # proof that the upstream source will be available at 08:25.
        path=Path(__file__).resolve().parents[1]/"four_mode_forecasts"/"202611111001.json"
        record=json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(record["race_code"],"202611111001")
        self.assertEqual(record["deadline_jst"],"2026-11-11T08:47:00+09:00")
        row={"レースコード":record["race_code"],
             "電話投票締切予定":"08:47"}
        day="20261111"
        for hhmm in ("08:21:00","08:25:00","08:30:00","08:33:00"):
            with self.subTest(eligible=hhmm):
                at=datetime.fromisoformat("2026-11-11T"+hhmm+"+09:00")
                self.assertEqual(near_t12([row],day,now=at),[record["race_code"]])
        for hhmm in ("08:20:59","08:33:01","08:35:00","08:47:00"):
            with self.subTest(ineligible=hhmm):
                at=datetime.fromisoformat("2026-11-11T"+hhmm+"+09:00")
                self.assertEqual(near_t12([row],day,now=at),[])

    def test_new_t12_uses_isolated_fresh_source_without_rewriting_old_snapshot(self):
        import research_model
        from unittest.mock import patch
        class FixedDatetime(datetime):
            @classmethod
            def now(cls, tz=None):
                return NOW
        src_titles=[{"レースコード":CODE,"電話投票締切予定":"18:33"}]
        src_cards=[dict({"レースコード":CODE},
                        **{f"艇{i}_全国勝率":str(5+i/10) for i in range(1,7)})]
        def source(url):
            return ((src_titles,NOW,"a"*64) if "/title/" in url
                    else (src_cards,NOW,"b"*64))
        with tempfile.TemporaryDirectory() as tmp:
            local=Path(tmp)/"original_snapshots"
            local.mkdir()
            prior=base()
            prior.update({"ok":True,"message":"既存の研究予想（未検証）"})
            prior["generated_at"]=(NOW-timedelta(hours=2)).isoformat()
            prior["source_title_received_jst"]=prior["generated_at"]
            prior["source_cards_received_jst"]=prior["generated_at"]
            original=json.dumps(prior,ensure_ascii=False,sort_keys=True).encode()
            original_path=local/(CODE+".json")
            original_path.write_bytes(original)
            durable={}
            with (patch.object(research_model,"STORE",local),
                  patch.object(research_model,"datetime",FixedDatetime),
                  patch.object(research_model,"read_rows",side_effect=source),
                  patch.object(research_model,"model_provenance",return_value={
                      "model_git_sha":"c"*40,"model_source_sha256":"d"*64,
                      "model_dependency_scope":"research_model.py_only_not_complete_environment"})):
                # Ordinary API still reuses the old immutable research record.
                self.assertEqual(research_model.predict("20261103","07","08")["generated_at"],
                                 prior["generated_at"])
                # T-12 must make a genuinely new original from new sources.
                report=seed_once(now=lambda:NOW,fetch_title=lambda url:title(),
                    ledger_ops=(durable.get,lambda key,value:durable.setdefault(key,value)))
            self.assertEqual(report["status"],"t12_generation_attempted")
            self.assertEqual(report["newly_stored_count"],1)
            self.assertEqual(report["failed_count"],0)
            self.assertEqual(original_path.read_bytes(),original)
            published=json.loads(durable["t12_baselines/20261103/"+CODE+".json"])
            self.assertEqual(published["generated_at"],NOW.isoformat())
            self.assertEqual(published["source_title_received_jst"],NOW.isoformat())
            self.assertEqual(published["source_cards_received_jst"],NOW.isoformat())
            self.assertEqual(published["input_source_kind"],"public_pre_race_csv")
            self.assertNotEqual(durable["t12_baselines/20261103/"+CODE+".json"],original)
            self.assertEqual(published["predictions"],
                ["-".join(map(str,t)) for t,p in probabilities(published["national_win_rates"])[:10]])
            self.assertFalse(report["research_only"] is False)

    def test_t12_fresh_source_failure_does_not_publish_cached_original(self):
        import research_model
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as tmp:
            local=Path(tmp)/"original_snapshots"
            local.mkdir()
            old=base()
            old["generated_at"]=(NOW-timedelta(hours=2)).isoformat()
            local_original=json.dumps(old).encode()
            (local/(CODE+".json")).write_bytes(local_original)
            created=[]
            with (patch.object(research_model,"STORE",local),
                  patch.object(research_model,"read_rows",
                               side_effect=ValueError("invalid fresh source"))):
                report=seed_once(now=lambda:NOW,fetch_title=lambda url:title(),
                    ledger_ops=(lambda p:None,lambda p,b:created.append(p)))
            self.assertEqual(report["stored_count"],0)
            self.assertEqual(report["failed_count"],1)
            self.assertEqual(created,[])
            self.assertEqual((local/(CODE+".json")).read_bytes(),local_original)

    def test_hours_old_local_prediction_is_never_reclassified_as_t12(self):
        stale=base()
        early=(NOW-timedelta(hours=2)).isoformat()
        for key in ("generated_at","source_title_received_jst","source_cards_received_jst"):
            stale[key]=early
        old_bytes=json.dumps(stale,ensure_ascii=False).encode()
        with self.assertRaisesRegex(ValueError,"generated_before_selection_window"):
            validate_base(old_bytes,CODE,now=NOW)
        # The original research_model.predict may return a previously saved
        # local forecast without regenerating. Refuse ledger publication.
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/(CODE+".json")
            path.write_bytes(old_bytes)
            created=[]
            output=seed_once(
                now=lambda:NOW,
                fetch_title=lambda url:title(),
                predictor=lambda *args:None,
                record_path=lambda code:path,
                ledger_ops=(lambda key:None,lambda key,value:created.append(key)))
            self.assertEqual(output["eligible_count"],1)
            self.assertEqual(output["stored_count"],0)
            self.assertEqual(output["failed_count"],1)
            self.assertEqual(created,[])
            self.assertIn("generated_before_selection_window",
                          output["results"][0]["error_code"])
            self.assertEqual(path.read_bytes(),old_bytes)

    def test_earliest_allowed_t12_generation_still_passes(self):
        payload=base()
        earliest=(datetime(2026,11,3,18,21,tzinfo=JST)-
                  timedelta(minutes=14)).isoformat()
        for key in ("generated_at","source_title_received_jst","source_cards_received_jst"):
            payload[key]=earliest
        self.assertEqual(validate_base(json.dumps(payload).encode(),CODE,now=NOW),
                         "t12_baselines/20261103/"+CODE+".json")

    def test_source_receipt_after_generated_time_never_counts_as_t12(self):
        payload=base()
        payload["source_cards_received_jst"]=(NOW+timedelta(seconds=1)).isoformat()
        with self.assertRaisesRegex(ValueError,"source_received_after_generation"):
            validate_base(json.dumps(payload).encode(),CODE,
                          now=NOW+timedelta(minutes=1))

    def test_source_receipts_and_generated_clock_cannot_be_in_future(self):
        for field in ("generated_at","source_title_received_jst",
                      "source_cards_received_jst"):
            with self.subTest(field=field):
                payload=base()
                payload[field]=(NOW+timedelta(seconds=1)).isoformat()
                with self.assertRaisesRegex(ValueError,"missed_cutoff"):
                    validate_base(json.dumps(payload).encode(),CODE,now=NOW)
    def test_source_or_generation_at_exact_cutoff_is_not_prospective(self):
        cutoff=datetime(2026,11,3,18,21,tzinfo=JST)
        safe_now=cutoff-timedelta(microseconds=1)
        for field in ("generated_at","source_title_received_jst",
                      "source_cards_received_jst"):
            with self.subTest(field=field):
                payload=base()
                payload[field]=cutoff.isoformat()
                with self.assertRaisesRegex(ValueError,"missed_cutoff"):
                    validate_base(json.dumps(payload).encode(),CODE,now=safe_now)
    def test_source_receipt_after_cutoff_is_never_frozen(self):
        row=base();row["source_cards_received_jst"]="2026-11-03T18:22:00+09:00"
        with self.assertRaisesRegex(ValueError,"missed_cutoff"):
            validate_base(json.dumps(row).encode(),CODE,now=NOW)
    def test_actual_commit_after_cutoff_is_never_certified(self):
        past=datetime(2026,11,3,18,23,tzinfo=JST)
        with self.assertRaisesRegex(ValueError,"missed_cutoff"):
            validate_base(raw(),CODE,now=past)
    def test_early_run_does_not_generate_anything(self):
        with tempfile.TemporaryDirectory() as tmp:
            out=seed_once(now=lambda:datetime(2026,11,3,18,1,tzinfo=JST),
                fetch_title=lambda url:title(),
                predictor=lambda *args:self.fail("too early"),
                ledger_ops=(lambda p:None,lambda p,raw:self.fail("write")))
            self.assertEqual(out["stored_count"],0)
            self.assertEqual(out["status"],"no_races_in_t12_generation_window")
    def test_partial_failure_is_not_reported_as_success(self):
        report=seed_once(now=lambda:NOW,fetch_title=lambda url:title(),
                 predictor=lambda *a:(_ for _ in ()).throw(ValueError("source_unavailable")),
                 ledger_ops=(lambda p:None,lambda p,r:self.fail("write")))
        self.assertEqual(report["stored_count"],0)
        self.assertEqual(report["failed_count"],1)
        self.assertEqual(report["results"][0]["status"],"failed")
if __name__=="__main__":unittest.main()

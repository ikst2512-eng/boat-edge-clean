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
    def test_default_t12_path_generates_fresh_without_mutating_cached_research(self):
        import research_model as model
        from unittest.mock import patch

        class FrozenDatetime(datetime):
            @classmethod
            def now(cls, tz=None):
                return NOW if tz is None else NOW.astimezone(tz)

        with tempfile.TemporaryDirectory() as tmp:
            older=Path(tmp)/"research_snapshots"
            older.mkdir()
            cached=base()
            cached["generated_at"]=(NOW-timedelta(hours=2)).isoformat()
            cached["source_title_received_jst"]=cached["generated_at"]
            cached["source_cards_received_jst"]=cached["generated_at"]
            cached_bytes=json.dumps(cached,ensure_ascii=False).encode()
            cached_path=older/(CODE+".json")
            cached_path.write_bytes(cached_bytes)
            archive={}
            calls=[]

            def source(url):
                calls.append(url)
                if "/title/" in url:
                    return ([{"レースコード":CODE,
                              "電話投票締切予定":"18:33"}],NOW,"a"*64)
                if "/race_cards/" in url:
                    return ([dict({"レースコード":CODE},
                         **{f"艇{i}_全国勝率":str(5+i/10)
                            for i in range(1,7)})],NOW,"b"*64)
                self.fail("unrelated source")

            provenance={"model_git_sha":"f"*40,
                        "model_source_sha256":"d"*64,
                        "model_dependency_scope":"research_model.py_only_not_complete_environment"}
            with patch.object(model,"STORE",older), \
                 patch.object(model,"datetime",FrozenDatetime), \
                 patch.object(model,"read_rows",side_effect=source), \
                 patch.object(model,"model_provenance",return_value=provenance):
                report=seed_once(now=lambda:NOW,
                    fetch_title=lambda url:title(),
                    ledger_ops=(archive.get,lambda k,v:archive.setdefault(k,v)))
                self.assertEqual(model.STORE,older)

            self.assertEqual(report["eligible_count"],1)
            self.assertEqual(report["newly_stored_count"],1)
            self.assertEqual(report["failed_count"],0)
            self.assertEqual(len(calls),2)
            self.assertEqual(cached_path.read_bytes(),cached_bytes)
            stored=json.loads(archive[f"t12_baselines/20261103/{CODE}.json"])
            self.assertEqual(stored["generated_at"],NOW.isoformat())
            self.assertEqual(stored["source_title_received_jst"],NOW.isoformat())
            self.assertEqual(stored["source_cards_received_jst"],NOW.isoformat())
            self.assertEqual(stored["input_source_kind"],"public_pre_race_csv")
            self.assertNotEqual(stored["generated_at"],cached["generated_at"])
            self.assertEqual(stored["model_source_sha256"],"d"*64)

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

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
            seed_once(now=lambda:NOW,fetch_title=lambda url:b"foo,bar\\n1,2\\n",
                fallback_title=lambda day:self.fail("malformed published source must fail"))
    def test_partial_published_title_is_supplemented_without_mutating_original(self):
        more="202611030709"
        with tempfile.TemporaryDirectory() as tmp:
            store={}
            root=Path(tmp)
            original=(f"レースコード,電話投票締切予定\\n202611030101,15:20\\n").encode()
            seen=[]
            def saver(code):return root/(code+".json")
            def make(day,venue,race):
                seen.append(day+venue+race)
                d=base();d["race_code"]=more
                # The fixture's only purpose is to test selection and
                # immutable bytes, not to construct a post-result forecast.
                saver(more).write_bytes(json.dumps(d).encode())
            output=seed_once(now=lambda:NOW,fetch_title=lambda url:original,
                fallback_title=lambda day:(
                    [{"レースコード":"202611030101","電話投票締切予定":"15:20"},
                     {"レースコード":more,"電話投票締切予定":"18:33"}],
                    NOW,"a"*64),
                predictor=make,record_path=saver,
                ledger_ops=(store.get,lambda k,v:store.setdefault(k,v)))
            # Missing live race is discovered; source consistency and model
            # integrity still gate any actual archival.
            self.assertEqual(output["title_schedule_source"],
                             "published_title_plus_live_checked")
            self.assertEqual(output["eligible_count"],1)
            self.assertEqual(seen,[more])
            self.assertEqual(output["stored_count"],0)
            self.assertEqual(output["results"][0]["status"],"failed")
    def test_conflicting_deadline_is_not_selected(self):
        partial=(f"レースコード,電話投票締切予定\\n{CODE},18:33\\n").encode()
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
    def test_immutable_append_prevents_edited_forecasts(self):
        with self.assertRaisesRegex(ValueError,"immutable_conflict"):
            publish_base(raw(),CODE,lambda path:b"changed",
                         lambda p,d:self.fail("write"),clock=lambda:NOW)
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
        self.assertEqual(report["results"][0]["status"],"failed")
if __name__=="__main__":unittest.main()

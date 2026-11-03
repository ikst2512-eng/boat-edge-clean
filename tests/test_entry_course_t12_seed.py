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

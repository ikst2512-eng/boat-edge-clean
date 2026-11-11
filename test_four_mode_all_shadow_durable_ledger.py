"""Durable four-mode candidate ledger: write-once / T12 remote observation."""
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from test_four_mode_all_mode_same_job_shadow import fixture, JST, CODE, SHA
from four_mode_all_mode_same_job_shadow import capture
from four_mode_all_shadow_durable_ledger import prepare, publish

ORIGINAL = "four_mode_forecasts/"+CODE+".json"
UTC = timezone.utc


def valid_shadow(root):
    p,o,git=fixture(root)
    report=capture(root,p,o,now=datetime(2026,11,7,8,10,0,tzinfo=JST),
                   git=git,clock=lambda:datetime(2026,11,7,8,10,1,tzinfo=JST))
    assert report["frozen_count"]==1
    raw=(json.dumps(report,ensure_ascii=False,sort_keys=True)+"\n").encode()
    def provenance(args):
        if args[:2]==["rev-parse","HEAD"]:
            return (SHA+"\n").encode()
        if args[:2]==["merge-base","--is-ancestor"]:
            return b""
        if args[0]=="diff-tree":
            return (ORIGINAL+"\n").encode()
        if args==["show",SHA+":"+ORIGINAL]:
            return (root/ORIGINAL).read_bytes()
        raise AssertionError(args)
    return raw,provenance


class DurableLedgerTests(unittest.TestCase):
    def test_validate_and_pin_exact_first_add_run(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);raw,git=valid_shadow(root)
            path=prepare(raw,root,"1234567","1",git=git)
            self.assertEqual(path,"four_mode_all/20261107/run-1234567-attempt-1.json")

    def test_write_once_and_early_github_candidate_observation(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);raw,git=valid_shadow(root)
            store={}
            def get(p):return store.get(p)
            def put(p,b,run):
                if p in store:raise AssertionError("overwritten")
                store[p]=b
            observer=lambda p:(datetime(2026,11,6,23,10,3,tzinfo=UTC),store[p])
            out=publish(raw,root,"1234567","1",get,put,observer,git=git)
            self.assertTrue(out["stored"])
            self.assertFalse(out["formal"])
            self.assertFalse(out["candidate_first_remote_receipt_verified"])
            self.assertEqual(out["observed_before_t_minus_12"],1)
            self.assertEqual(out["observed_late_or_ambiguous"],0)
            self.assertEqual(out["records"][0]["race_code"],CODE)
            second=publish(raw,root,"1234567","1",get,put,observer,git=git)
            self.assertEqual(second["status"],"existing_identical_candidate")
            self.assertEqual(len(store),2)
            self.assertIn("four_mode_all_observation/20261107/run-1234567-attempt-1.json",store)
            self.assertEqual(second["immutable_observation_note_status"],"existing_identical_observation_note")

    def test_after_cutoff_not_misclassified_as_early(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);raw,git=valid_shadow(root)
            storage={}
            def read(p):return storage.get(p)
            def create(p,b,run):storage[p]=b
            observe=lambda p:(datetime(2026,11,6,23,24,0,tzinfo=UTC),storage[p])
            out=publish(raw,root,"1234567","1",read,create,observe,git=git)
            self.assertEqual(out["observed_before_t_minus_12"],0)
            self.assertEqual(out["observed_late_or_ambiguous"],1)
            self.assertFalse(out["candidate_first_remote_receipt_verified"])

    def test_ambiguous_same_second_observation_fails_to_prove_early(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);raw,git=valid_shadow(root)
            storage={}
            def read(p):return storage.get(p)
            def create(p,b,run):storage[p]=b
            observe=lambda p:(datetime(2026,11,6,23,10,1,tzinfo=UTC),storage[p])
            out=publish(raw,root,"1234567","1",read,create,observe,git=git)
            self.assertEqual(out["observed_before_t_minus_12"],0)

    def test_untrusted_remote_bytes_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);raw,git=valid_shadow(root)
            storage={}
            def read(p):return storage.get(p)
            def create(p,b,run):storage[p]=b
            observe=lambda p:(datetime(2026,11,6,23,10,3,tzinfo=UTC),b"tampered")
            with self.assertRaisesRegex(ValueError,"candidate_server_observation_not_verified"):
                publish(raw,root,"1234567","1",read,create,observe,git=git)

    def test_tampered_prior_observation_note_refused(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);raw,git=valid_shadow(root)
            store={}
            def get(p):return store.get(p)
            def put(p,b,run):store[p]=b
            observer=lambda p:(datetime(2026,11,6,23,10,3,tzinfo=UTC),store[p])
            first=publish(raw,root,"1234567","1",get,put,observer,git=git)
            note=first["immutable_observation_note_path"]
            corrupted=json.loads(store[note])
            corrupted["observed_before_t_minus_12"]=0
            corrupted["observed_late_or_ambiguous"]=1
            corrupted["records"][0]["status"]="candidate_observation_late_or_same_second"
            store[note]=(json.dumps(corrupted,sort_keys=True)+"\n").encode()
            with self.assertRaisesRegex(ValueError,"existing_observation_note_timing_inconsistent"):
                publish(raw,root,"1234567","1",get,put,observer,git=git)

    def test_changed_existing_blob_cannot_be_overwritten(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);raw,git=valid_shadow(root)
            store={"four_mode_all/20261107/run-1234567-attempt-1.json":b"changed"}
            def create(p,b,run):raise AssertionError("overwrite attempted")
            with self.assertRaisesRegex(ValueError,"immutable_candidate_collision"):
                publish(raw,root,"1234567","1",store.get,create,None,git=git)

    def test_forged_formal_claim_or_tampered_candidate_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);raw,git=valid_shadow(root)
            item=json.loads(raw)
            item["candidate_first_remote_receipt_verified"]=True
            with self.assertRaisesRegex(ValueError,"unsafe_or_forged_evidence"):
                prepare(json.dumps(item).encode(),root,"1234567","1",git=git)
            item=json.loads(raw)
            item["records"][0]["candidate"]["hit"][0]="6-5-4"
            with self.assertRaisesRegex(ValueError,"saved_candidate_not_reproducible"):
                prepare(json.dumps(item).encode(),root,"1234567","1",git=git)

    def test_no_publication_not_fabricated(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            raw=json.dumps({"schema":"FOUR_MODE_ALL_SHADOW_AFTER_PUSH_RESEARCH_V1",
                 "status":"no_publication","formal":False,
                 "candidate_first_remote_receipt_verified":False,
                 "production_forecast_changed":False,"records":[],
                 "published_count":0,"frozen_count":0,"ineligible_count":0,
                 "validation_error_count":0}).encode()
            self.assertIsNone(prepare(raw,root,"1234567","1"))
            out=publish(raw,root,"1234567","1",
                    lambda path:None, lambda *args:None, lambda p:None)
            self.assertFalse(out["stored"])
            self.assertEqual(out["observed_before_t_minus_12"],0)


if __name__=="__main__":
    unittest.main()

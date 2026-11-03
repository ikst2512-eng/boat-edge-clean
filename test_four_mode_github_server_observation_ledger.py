import base64
import hashlib
import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from four_mode_github_server_observation_ledger import prepare,publish,BRANCH

CODE="202611040101"
SHA="a"*40
PATH="four_mode_forecasts/"+CODE+".json"
RAW=json.dumps({"race_code":CODE,"deadline_jst":"2026-11-04T12:00:00+09:00"}).encode()

class ObservationLedgerTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);f=self.root/PATH;f.parent.mkdir();f.write_bytes(RAW)
        self.row={"race_code":CODE,"status":"github_server_observed_before_t_minus_12",
                  "first_add_commit":SHA,"independent_first_remote_receipt_verified":False,
                  "first_add_blob_matches_remote":True,
                  "original_sha256":hashlib.sha256(RAW).hexdigest(),
                  "github_api_server_date_utc":"2026-11-04T02:40:00+00:00",
                  "deadline_minus_12_jst":"2026-11-04T11:48:00+09:00"}
        self.artifact={"schema":"FOUR_MODE_GITHUB_REMOTE_OBSERVATION_V1",
                       "status":"remote_observation_audited_nonformal",
                       "formal":False,"independent_first_remote_receipt_verified":False,
                       "github_server_observation_not_first_receipt":True,
                       "production_forecast_changed":False,
                       "publication_commit_sha":SHA,"publication_count":1,
                       "observed_before_t_minus_12":1,
                       "observed_after_t_minus_12":0,"unverified_count":0,
                       "records":[self.row]}
        self.store={}
    def git(self,*args):
        if args[0]=="diff-tree":return (PATH+"\n").encode()
        if args[0]=="show":return RAW
        raise AssertionError(args)
    def payload(self):return json.dumps(self.artifact,sort_keys=True).encode()
    def read(self,path):return self.store.get(path)
    def put(self,path,original,run):self.assertNotIn(path,self.store);self.store[path]=original

    def test_write_once_roundtrip_and_identical_retry(self):
        raw=self.payload()
        v=publish(raw,self.root,"1234","1",self.read,self.put,self.git)
        self.assertEqual(v["status"],"new_append_only_observation")
        self.assertEqual(v["branch"],BRANCH)
        self.assertEqual(v["path"],"github_server/20261104/run-1234-attempt-1.json")
        self.assertFalse(v["independent_first_remote_receipt_verified"])
        retry=publish(raw,self.root,"1234","1",self.read,
                      lambda *a:self.fail("attempted overwrite"),self.git)
        self.assertEqual(retry["status"],"already_preserved_identical")
        self.assertEqual(self.store[v["path"]],raw)

    def test_reject_rewritten_ledger_entry(self):
        publish(self.payload(),self.root,"1234","1",self.read,self.put,self.git)
        self.row["github_api_server_date_utc"]="2026-11-04T02:39:00+00:00"
        with self.assertRaisesRegex(ValueError,"immutable_observation_collision"):
            publish(self.payload(),self.root,"1234","1",self.read,self.put,self.git)

    def test_mislabeled_late_observation_rejected(self):
        self.row["github_api_server_date_utc"]="2026-11-04T02:48:00+00:00"
        with self.assertRaisesRegex(ValueError,"false_early_observation_label"):
            prepare(self.payload(),self.root,"1234","1",self.git)

    def test_mismatched_exact_source_rejected(self):
        (self.root/PATH).write_bytes(b"altered")
        with self.assertRaisesRegex(ValueError,"original_git_blob_changed"):
            prepare(self.payload(),self.root,"1234","1",self.git)

    def test_unverified_does_not_gain_early_status(self):
        self.row={"race_code":CODE,"status":"remote_observation_unverified",
                  "first_add_commit":SHA}
        self.artifact["observed_before_t_minus_12"]=0
        self.artifact["unverified_count"]=1
        self.artifact["records"]=[self.row]
        self.artifact["observed_after_t_minus_12"]=0
        self.assertIsNotNone(prepare(self.payload(),self.root,"1234","1",self.git))

    def test_pre_eligible_observations_are_skipped_not_failed(self):
        self.row["race_code"]="202611030101"
        self.assertIsNone(prepare(self.payload(),self.root,"1234","1",self.git))

    def test_no_publication_skips(self):
        data={"schema":"FOUR_MODE_GITHUB_REMOTE_OBSERVATION_V1",
              "status":"no_confirmed_publication","records":[],
              "formal":False,"independent_first_remote_receipt_verified":False,
              "github_server_observation_not_first_receipt":True,
              "production_forecast_changed":False}
        self.assertIsNone(prepare(json.dumps(data).encode(),self.root,"1234","1",self.git))

    def test_mismatched_count_and_source_sha_rejected(self):
        self.artifact["publication_count"]=2
        with self.assertRaisesRegex(ValueError,"bad_observation_publication"):
            prepare(self.payload(),self.root,"1234","1",self.git)
        self.artifact["publication_count"]=1
        self.row["original_sha256"]="0"*64
        with self.assertRaisesRegex(ValueError,"remote_blob_digest_mismatch"):
            prepare(self.payload(),self.root,"1234","1",self.git)

if __name__=="__main__":unittest.main()

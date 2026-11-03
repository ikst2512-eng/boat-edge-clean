import base64
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from four_mode_github_server_observation import observe
from four_mode_github_server_observation_ledger import publish
from hole_future_remote_observation_link import match
from scripts.verify_four_mode_capture_evidence import verify

CODE="202611040101"
SHA="a"*40
FILE="four_mode_forecasts/"+CODE+".json"
MODES=("baseline","donor_order","max_ticket_score","third_national_rate")

class PipelineTests(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup)
        self.root=Path(t.name);(self.root/"four_mode_forecasts").mkdir()
        self.raw=json.dumps({"schema":"CLEAN_FOUR_MODES_PREDEADLINE_V1",
            "race_code":CODE,"deadline_jst":"2026-11-04T12:00:00+09:00"}).encode()
        (self.root/FILE).write_bytes(self.raw)
        self.sha256=hashlib.sha256(self.raw).hexdigest()
        self.blob=hashlib.sha1(b"blob "+str(len(self.raw)).encode()+b"\0"+self.raw).hexdigest()
        self.ledger=self.root/"ledger"
        self.store={}
        self.future={"formal":False,"independent_first_receipt_verified":False,
          "race_codes":[CODE],"race_flags":{CODE:{
          p:{"top3":False,"top5":False,"top10":True} for p in MODES}},
          "hits":{p:{"top3":0,"top5":0,"top10":1} for p in MODES}}
        self.first={"formal":False,"independent_remote_first_receipt_verified":False,
          "records":[{"race_code":CODE,
          "status":"local_git_first_add_clock_before_t12_unverified",
          "first_add_commit":SHA,"source_sha256":self.sha256}]}

    def git(self,*args):
        if args[0]=="diff-tree":return (FILE+"\n").encode()
        if args[0]=="show":return self.raw
        raise AssertionError(args)

    def record(self,date_header):
        record={"path":FILE,"type":"file","encoding":"base64",
                "sha":self.blob,
                "content":base64.b64encode(self.raw).decode()}
        publication={"outcome":"pushed_to_main","commit_sha":SHA,"added_forecasts":1}
        result=observe(self.root,publication,"ikst2512-eng/boat-edge-clean",
                       lambda path:(date_header,json.dumps(record).encode()),self.git)
        original=json.dumps(result).encode()
        evidence=self.root/"four-mode-evidence"
        evidence.mkdir(exist_ok=True)
        (evidence/"publication.json").write_text(json.dumps(publication),encoding="utf-8")
        (evidence/"github-server-observation.json").write_bytes(original)
        def get(path):return self.store.get(path)
        def put(path,contents,run):self.store[path]=contents
        receipt=publish(original,self.root,"12345","1",get,put,self.git)
        (evidence/"github-server-observation-ledger.json").write_text(
            json.dumps(receipt),encoding="utf-8")
        target=self.ledger/receipt["path"]
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes(self.store[receipt["path"]])
        self.assertFalse(receipt["formal"])
        # The final gate now also requires the independently preserved
        # same-job frozen third-rate candidate for a Nov 4+ publication.
        shadow = {
            "schema":"V2_THIRD_RATE_SAME_JOB_FROZEN_SHADOW_V1",
            "status":"captured_local_after_push_not_remote_proven",
            "formal":False, "publication_commit_sha":SHA,
            "published_forecasts":1, "frozen_before_t_minus_12":1,
            "validation_error_count":0,
            "records":[{
                "race_code":CODE,
                "status":"frozen_in_same_job_before_t_minus_12",
                "source_commit_sha":SHA,
                "frozen_at_utc":"2026-11-04T02:40:00+00:00",
                "t_minus_12_jst":"2026-11-04T11:48:00+09:00",
            }],
        }
        original_shadow=json.dumps(shadow).encode("utf-8")
        (evidence/"third-rate-shadow.json").write_bytes(original_shadow)
        (evidence/"third-rate-ledger.json").write_text(json.dumps({
            "status":"new_immutable_ledger_entry", "stored":True,
            "formal":False, "branch":"v2-third-rate-evidence-ledger",
            "path":"third_rate/20261104/run-12345-attempt-1.json",
            "original_sha256":hashlib.sha256(original_shadow).hexdigest(),
        }),encoding="utf-8")
        return match(self.future,self.first,self.ledger,self.root)

    def test_actual_observation_and_ledger_pass_final_capture_gate(self):
        self.record("Wed, 04 Nov 2026 02:45:00 GMT")
        verdict=verify(self.root)
        self.assertEqual(verdict["status"],"published_with_durable_early_observation")
        self.assertEqual(verdict["published"],1)

    def test_actual_late_observation_rejected_by_final_capture_gate(self):
        self.record("Wed, 04 Nov 2026 02:48:00 GMT")
        with self.assertRaisesRegex(ValueError,"published_observation_not_durable_and_early"):
            verify(self.root)

    def test_readback_receipt_hash_mismatch_fails_final_capture_gate(self):
        self.record("Wed, 04 Nov 2026 02:45:00 GMT")
        p=self.root/"four-mode-evidence"/"github-server-observation-ledger.json"
        receipt=json.loads(p.read_text(encoding="utf-8"))
        receipt["sha256"]="0"*64
        p.write_text(json.dumps(receipt),encoding="utf-8")
        with self.assertRaisesRegex(ValueError,"published_observation_not_durable_and_early"):
            verify(self.root)

    def test_early_receipt_and_hole_top10(self):
        r=self.record("Wed, 04 Nov 2026 02:45:00 GMT")
        self.assertEqual(r["race_status"][CODE],"observed_before_t12")
        self.assertEqual(r["topn_by_evidence_status"]["observed_before_t12"]
                         ["hits"]["third_national_rate"]["top10"],1)
        self.assertFalse(r["independent_first_remote_receipt_verified"])

    def test_late_receipt_does_not_become_early(self):
        r=self.record("Wed, 04 Nov 2026 02:48:00 GMT")
        self.assertEqual(r["race_status"][CODE],"observed_after_t12")
        self.assertEqual(r["remote_observed_before_t12_count"],0)

    def test_missing_receipt_keeps_hit_in_missing_bucket(self):
        r=match(self.future,self.first,self.ledger,self.root)
        self.assertEqual(r["race_status"][CODE],"missing_observation")
        self.assertEqual(r["topn_by_evidence_status"]["missing_observation"]
                         ["hits"]["third_national_rate"]["top10"],1)

    def test_modified_archive_disqualifies_early_evidence(self):
        self.record("Wed, 04 Nov 2026 02:45:00 GMT")
        (self.root/FILE).write_bytes(b"modified")
        r=match(self.future,self.first,self.ledger,self.root)
        self.assertEqual(r["race_status"][CODE],"conflicting_observations")

if __name__=="__main__":unittest.main()

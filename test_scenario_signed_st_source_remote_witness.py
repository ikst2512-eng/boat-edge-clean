"""No-network source ledger remote witness contract tests.

These JSON/Date/commit responses are all SYNTHETIC. They cannot establish
a real official source first receipt or qualify the signed-F 600 sample.
"""
import base64
import copy
from datetime import datetime, timezone
from email.utils import format_datetime
import hashlib
import json
from urllib.parse import unquote, urlsplit, parse_qs
import unittest

from scenario_future_local_candidate_handoff import _git_blob_sha1
from scenario_signed_st_source_remote_witness import (
    observe_exact_1746_source_first_add, SOURCE_LEDGER, SOURCE_ROOT,
)
from test_scenario_signed_st_cross_ledger_audit import synth, canonical


def synthetic_responses(source_bytes,race,*,flags=None):
    flags=flags or {}
    sha=_git_blob_sha1(source_bytes)
    first="b"*40
    head="c"*40
    parent="d"*40
    path=SOURCE_ROOT+race[:8]+"/"+race+".json"
    parent_content={
        "type":"file","path":path,"encoding":"base64","sha":sha,
        "content":base64.b64encode(source_bytes).decode("ascii"),
    }
    seq=[
        (200,{"ref":"refs/heads/"+SOURCE_LEDGER,
              "object":{"sha":head,"type":"commit"}}),
        (200,parent_content),
        (200,[{"sha":first}]),
        (200,{"sha":first,"parents":[{"sha":parent}],
              "files":[{"filename":path,"status":"added","sha":sha}]}),
        (404,{"message":"Not Found"}),
    ]
    for idx in flags.get("mutate",{}):
        seq[idx]=flags["mutate"][idx]
    response_times=flags.get("times",[
        "2026-11-12T10:45:18+00:00",
        "2026-11-12T10:45:20+00:00",
        "2026-11-12T10:45:21+00:00",
        "2026-11-12T10:45:23+00:00",
        "2026-11-12T10:45:24+00:00",
    ])
    requests=[]
    def sender(req):
        idx=len(requests)
        requests.append(req)
        if idx>=len(seq):
            raise AssertionError("unexpected extra GitHub request")
        expect=[
            "/git/ref/heads/"+SOURCE_LEDGER,
            "/contents/"+path+"?ref="+head,
            "/commits?sha="+head+"&path="+path.replace("/","%2F")+"&per_page=100",
            "/commits/"+first,
            "/contents/"+path+"?ref="+parent,
        ]
        uri=urlsplit(req.full_url)
        actual=uri.path+("?"+uri.query if uri.query else "")
        # Exact query encoding follows urllib.urlencode; match semantics
        # without tolerating a cross-branch or alternate race.
        assert uri.path==expect[idx].split("?")[0],(idx,actual,expect[idx])
        if idx in (1,4):
            assert parse_qs(uri.query)=={"ref":[head if idx==1 else parent]}
        if idx==2:
            assert parse_qs(uri.query)=={"sha":[head],"path":[path],"per_page":["100"]}
        assert req.get_method()=="GET"
        assert uri.netloc=="api.github.com"
        status,body=seq[idx]
        headers={"Date":format_datetime(
            datetime.fromisoformat(response_times[idx]).astimezone(timezone.utc),
            usegmt=True)}
        headers.update(flags.get("headers",{}).get(idx,{}))
        return status,headers,json.dumps(body).encode("utf-8")
    return sender,requests


class SourceRemoteWitnessTests(unittest.TestCase):
    def setUp(self):
        self.prepared,self.source,self.receipt=synth()
        self.bytes=canonical(self.source)
        self.race=self.prepared["race_code"]

    def run_fake(self,flags=None):
        sender,requests=synthetic_responses(self.bytes,self.race,flags=flags)
        result=observe_exact_1746_source_first_add(
            self.prepared,self.bytes,self.receipt,send=sender)
        self.assertEqual(len(requests),5)
        return result

    def test_source_content_added_parent_verified_but_not_first_remote(self):
        result=self.run_fake()
        self.assertTrue(result["current_branch_unique_path_add_verified"])
        self.assertTrue(result["first_add_parent_did_not_contain_source_file"])
        self.assertEqual(result["source_file_git_blob_sha1"],_git_blob_sha1(self.bytes))
        self.assertEqual(result["observed_first_add_commit_sha"],"b"*40)
        self.assertFalse(result["network_transport_is_direct_GitHub_HTTPS"])
        self.assertTrue(result["mock_server_date_before_cutoff_not_evidence"])
        for key in (
            "source_seen_at_observed_time_before_T12",
            "source_writer_receipt_independently_authenticated",
            "source_first_remote_acceptance_verified",
            "source_branch_forcepush_history_excluded",
            "official_HTTP_source_origin_independently_verified",
            "F_candidate_was_written_to_GitHub",
            "F_candidate_first_remote_receipt_verified",
            "eligible_for_300_plus_300","formal",
            "production_changed","accuracy_improvement_proven",
        ):
            self.assertIs(result[key],False,key)

    def test_current_branch_contents_wrong_blob_or_bytes_rejected(self):
        body={"type":"file","path":SOURCE_ROOT+self.race[:8]+"/"+self.race+".json",
              "encoding":"base64","sha":"0"*40,
              "content":base64.b64encode(self.bytes).decode()}
        sender,_=synthetic_responses(self.bytes,self.race,flags={"mutate":{1:(200,body)}})
        with self.assertRaisesRegex(ValueError,"file_or_blob_mismatch"):
            observe_exact_1746_source_first_add(
                self.prepared,self.bytes,self.receipt,send=sender)
        body["sha"]=_git_blob_sha1(self.bytes)
        body["content"]=base64.b64encode(b"tampered").decode()
        sender,_=synthetic_responses(self.bytes,self.race,flags={"mutate":{1:(200,body)}})
        with self.assertRaisesRegex(ValueError,"bundle_bytes_differ"):
            observe_exact_1746_source_first_add(
                self.prepared,self.bytes,self.receipt,send=sender)

    def test_duplicate_history_or_modified_commit_rejected(self):
        sender,_=synthetic_responses(self.bytes,self.race,flags={
            "mutate":{2:(200,[{"sha":"b"*40},{"sha":"a"*40}])}})
        with self.assertRaisesRegex(ValueError,"history_not_unique_add"):
            observe_exact_1746_source_first_add(
                self.prepared,self.bytes,self.receipt,send=sender)
        detail={"sha":"b"*40,"parents":[{"sha":"d"*40}],
                "files":[{"filename":SOURCE_ROOT+self.race[:8]+"/"+self.race+".json",
                          "status":"modified","sha":_git_blob_sha1(self.bytes)}]}
        sender,_=synthetic_responses(self.bytes,self.race,flags={
            "mutate":{3:(200,detail)}})
        with self.assertRaisesRegex(ValueError,"status_not_confirmed"):
            observe_exact_1746_source_first_add(
                self.prepared,self.bytes,self.receipt,send=sender)

    def test_parent_path_present_is_hard_fail(self):
        sender,_=synthetic_responses(self.bytes,self.race,flags={
            "mutate":{4:(200,{"path":"preexisting"})}})
        with self.assertRaisesRegex(ValueError,"http_status_200"):
            observe_exact_1746_source_first_add(
                self.prepared,self.bytes,self.receipt,send=sender)

    def test_missing_date_cached_response_clock_regress_fail(self):
        sender,_=synthetic_responses(self.bytes,self.race,flags={
            "headers":{0:{"Age":"60"}}})
        with self.assertRaisesRegex(ValueError,"cached_response_forbidden"):
            observe_exact_1746_source_first_add(
                self.prepared,self.bytes,self.receipt,send=sender)
        bad_times=[
            "2026-11-12T10:45:18+00:00",
            "2026-11-12T10:45:25+00:00",
            "2026-11-12T10:45:21+00:00",
            "2026-11-12T10:45:23+00:00",
            "2026-11-12T10:45:24+00:00",
        ]
        sender,_=synthetic_responses(self.bytes,self.race,flags={"times":bad_times})
        with self.assertRaisesRegex(ValueError,"server_time_regressed"):
            observe_exact_1746_source_first_add(
                self.prepared,self.bytes,self.receipt,send=sender)

    def test_late_mock_remote_readback_cannot_claim_pre_T12(self):
        late=[
            "2026-11-12T10:48:22+00:00",
            "2026-11-12T10:48:23+00:00",
            "2026-11-12T10:48:24+00:00",
            "2026-11-12T10:48:25+00:00",
            "2026-11-12T10:48:26+00:00",
        ]
        result=self.run_fake({"times":late})
        self.assertFalse(result["source_seen_at_observed_time_before_T12"])
        self.assertFalse(result["formal"])
        self.assertFalse(result["source_first_remote_acceptance_verified"])

    def test_receipt_claims_cannot_change_source_first_remote_flags(self):
        self.receipt["independent_remote_first_seen_verified"]=True
        sender,_=synthetic_responses(self.bytes,self.race)
        with self.assertRaisesRegex(ValueError,"wrong_official_writer_receipt"):
            observe_exact_1746_source_first_add(
                self.prepared,self.bytes,self.receipt,send=sender)

    def test_unexpected_404_on_head_ref_is_failure(self):
        sender,_=synthetic_responses(self.bytes,self.race,flags={
            "mutate":{0:(404,{"message":"Not Found"})}})
        with self.assertRaisesRegex(ValueError,"http_status_404"):
            observe_exact_1746_source_first_add(
                self.prepared,self.bytes,self.receipt,send=sender)


if __name__=="__main__":
    unittest.main()

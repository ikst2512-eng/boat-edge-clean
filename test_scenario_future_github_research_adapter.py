"""Mocked GitHub HTTP contract tests; no Internet write, no forecast claims."""
import base64
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from urllib.parse import parse_qs, urlsplit

from scenario_future_github_research_adapter import (
    API, GitHubOnlyCreateWire, REPO, _remote_path,
    run_from_gateway_file, inspect_candidate_observed_first_add,
    LEDGER_BOOTSTRAP_HEAD_SHA,
)
from scenario_future_local_candidate_handoff import (
    RESEARCH_ONLY_LEDGER_BRANCH, _git_blob_sha1,
    prepare_local_candidate, publish_local_candidate_write_once,
)
from test_scenario_future_local_candidate_handoff import (
    fake_gateway, GENERATED, FROZEN,
)
from test_scenario_future_protocol_freeze import read_protocol


class GitHubMockAPI:
    def __init__(self):
        self.files={}
        self.puts=0
        self.reads=0
        self.bad_ack=False
        self.bad_content=False
        self.force_put_status=None
        self.age_header=False

    def __call__(self, request):
        url=request.full_url
        expected=API+"/contents/scenario_four_mode_research/202611111710.json"
        if not url.startswith(expected):
            raise AssertionError("unexpected path or repository")
        method=request.get_method()
        if method=="GET":
            if "?ref="+RESEARCH_ONLY_LEDGER_BRANCH not in url:
                raise AssertionError("unexpected ref")
            self.reads+=1
            raw=self.files.get(expected)
            if raw is None:
                return (404, {}, b'{"message":"not found"}')
            content=raw if not self.bad_content else raw+b"tampered"
            body={
                "path":"scenario_four_mode_research/202611111710.json",
                "type":"file",
                "encoding":"base64",
                "content":base64.b64encode(content).decode(),
                "sha":_git_blob_sha1(raw),
            }
            return (200, {"Age":"5"} if self.age_header else {},
                    json.dumps(body).encode())
        if method!="PUT":
            raise AssertionError("unsafe HTTP method")
        self.puts+=1
        data=json.loads(request.data)
        if set(data)!={"message","branch","content"} or data["branch"]!=RESEARCH_ONLY_LEDGER_BRANCH:
            raise AssertionError("not strict create-only GitHub Contents PUT")
        if "sha" in data:
            raise AssertionError("PUT must never contain old content SHA/upsert")
        if request.get_header("Authorization") != "Bearer fake-unit-token":
            raise AssertionError("expected test token")
        if self.force_put_status:
            return (self.force_put_status,{},b'{"message":"conflict"}')
        if expected in self.files:
            return (422,{},b'{"message":"already exists"}')
        raw=base64.b64decode(data["content"],validate=True)
        self.files[expected]=raw
        response={
            "content":{
                "path":"scenario_four_mode_research/202611111710.json",
                "sha":"0"*40 if self.bad_ack else _git_blob_sha1(raw),
            },
            "commit":{"sha":"1"*40},
        }
        return (201,{},json.dumps(response).encode())


class ActualWireWithOnlyFakeTransportTests(unittest.TestCase):
    def setUp(self):
        self.p=read_protocol()
        self.g=fake_gateway(self.p)
        self.prep=prepare_local_candidate(self.g,self.p,GENERATED,FROZEN)
        self.h=GitHubMockAPI()
        self.w=GitHubOnlyCreateWire("fake-unit-token",send=self.h)
        self.clock=lambda:datetime.fromisoformat("2026-11-11T15:09:00+09:00")

    def invoke(self):
        return publish_local_candidate_write_once(
            self.prep,self.g,self.p,GENERATED,FROZEN,
            RESEARCH_ONLY_LEDGER_BRANCH,self.w.read,self.w.create,self.clock)

    def test_mocked_api_atomic_create_and_replay_without_second_put(self):
        result=self.invoke()
        same=self.invoke()
        self.assertEqual(result["status"],"create_only_storage_call_returned_unattested")
        self.assertEqual(same["status"],"identical_candidate_already_present_unattested")
        self.assertEqual(self.h.puts,1)
        self.assertEqual(self.h.reads,4)
        self.assertEqual(len(self.h.files),1)
        self.assertEqual(list(self.h.files.values()),[self.prep["bytes"]])
        self.assertFalse(result["first_remote_candidate_receipt_verified"])
        self.assertFalse(result["formal"])

    def test_existing_other_bytes_never_overwritten(self):
        key=API+"/contents/"+self.prep["path"]
        self.h.files[key]=b"different"
        with self.assertRaisesRegex(ValueError,"immutable_candidate_collision"):
            self.invoke()
        self.assertEqual(self.h.files[key],b"different")
        self.assertEqual(self.h.puts,0)

    def test_server_conflict_or_bad_ack_never_means_success(self):
        self.h.force_put_status=422
        with self.assertRaisesRegex(ValueError,"http_422"):
            self.invoke()
        self.assertEqual(self.h.puts,1)
        self.assertEqual(self.h.reads,1)
        self.h.force_put_status=None
        self.h.bad_ack=True
        with self.assertRaisesRegex(ValueError,"ack_not_matching"):
            self.invoke()

    def test_stale_or_corrupt_response_hard_fail(self):
        key=API+"/contents/"+self.prep["path"]
        self.h.files[key]=self.prep["bytes"]
        self.h.age_header=True
        with self.assertRaisesRegex(ValueError,"cached_response"):
            self.invoke()
        self.h.age_header=False
        self.h.bad_content=True
        with self.assertRaisesRegex(ValueError,"git_blob_or_length_mismatch"):
            self.invoke()

    def test_research_branch_only_and_limited_exact_path(self):
        for path in ("scenario_four_mode_research/202611111710.json",
                     "scenario_four_mode_research/202611110710.json"):
            self.assertEqual(_remote_path(path),path)
        for path in ("four_mode_forecasts/202611111710.json",
                     "scenario_four_mode_research/../../main.json",
                     "scenario_four_mode_research/202611111710.yaml",
                     "scenario_four_mode_research/20A611111710.json",
                     "scenario_four_mode_research/202611111710.json/extra"):
            with self.subTest(path=path),self.assertRaisesRegex(
                    ValueError,"unapproved_research_candidate_path"):
                _remote_path(path)
        with self.assertRaisesRegex(ValueError,"branch_required"):
            self.w.read("main",self.prep["path"])
        with self.assertRaisesRegex(ValueError,"explicit_token"):
            GitHubOnlyCreateWire("",send=self.h)
        self.assertEqual(self.h.puts,0)

    def test_cli_default_is_strictly_offline_even_if_token_available(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/"mocked-future-gateway.json"
            path.write_text(json.dumps(self.g,sort_keys=True)+"\n",encoding="utf-8")
            result=run_from_gateway_file(path,GENERATED,FROZEN,
                                         publish=False,token="fake-unit-token",
                                         send=self.h)
            self.assertEqual(result["status"],"validated_local_only_no_github_write")
            self.assertFalse(result["github_create_attempted"])
            self.assertFalse(result["first_remote_candidate_receipt_verified"])
            self.assertEqual(self.h.puts,0)
            self.assertEqual(self.h.reads,0)


class SyntheticFirstAddGitHubWitnessHTTP:
    """No real GitHub traffic. Freeze SHA, head, history, parent, compare."""
    FIRST="b"*40
    PARENT="8443570d4a642c97bc700c9691ff7e8e4c5c314d"
    PATH="scenario_four_mode_research/202611111710.json"

    def __init__(self, exact_bytes):
        self.raw=exact_bytes
        self.requests=[]
        self.diff_mode=None
        self.utc=datetime(2026,11,11,6,9,0,tzinfo=timezone.utc)

    def __call__(self,request):
        assert request.get_method()=="GET", "witness must NEVER make PUT"
        assert request.full_url.startswith(API+"/")
        url=urlsplit(request.full_url)
        p=url.path.split("/repos/ikst2512-eng/boat-edge-clean",1)[-1]
        params=parse_qs(url.query)
        self.requests.append((p,params))
        utc=self.utc+timedelta(seconds=len(self.requests)-1)
        if self.diff_mode=="late_existence" and len(self.requests)==2:
            utc=datetime(2026,11,11,6,18,2,tzinfo=timezone.utc)
        headers={"Date":format_datetime(utc,usegmt=True)}
        if self.diff_mode=="cached" and len(self.requests)==2:
            headers["Age"]="60"
        if self.diff_mode=="missing_date" and len(self.requests)==1:
            del headers["Date"]
        if p=="/git/ref/heads/"+RESEARCH_ONLY_LEDGER_BRANCH:
            obj={"ref":"refs/heads/"+RESEARCH_ONLY_LEDGER_BRANCH,
                 "object":{"sha":self.FIRST,"type":"commit"}}
        elif p=="/contents/"+self.PATH:
            if params=={"ref":[self.FIRST]}:
                candidate=self.raw
                if self.diff_mode=="tampered_content":
                    candidate+=b"x"
                obj={"type":"file","path":self.PATH,
                     "encoding":"base64",
                     "sha":_git_blob_sha1(self.raw),
                     "content":base64.b64encode(candidate).decode()}
            elif params=={"ref":[self.PARENT]}:
                if self.diff_mode=="parent_still_exists":
                    return 200,headers,json.dumps({"type":"file"}).encode()
                return 404,headers,b'{"message":"Not Found"}'
            else:
                raise AssertionError("unrecognized pinned candidate sha")
        elif p=="/commits":
            assert params=={"sha":[self.FIRST],"path":[self.PATH],"per_page":["100"]}
            obj=[{"sha":self.FIRST}]
            if self.diff_mode=="modified_second_commit":
                obj.append({"sha":"a"*40})
            if self.diff_mode=="history_paginated":
                headers["Link"]='<https://api.github.com/next>; rel="next"'
        elif p=="/commits/"+self.FIRST:
            obj={"sha":self.FIRST,"parents":[{"sha":self.PARENT}],
                 "files":[{"filename":self.PATH,"status":"added",
                           "sha":_git_blob_sha1(self.raw)}]}
            if self.diff_mode=="not_added":
                obj["files"][0]["status"]="modified"
        elif p=="/compare/"+LEDGER_BOOTSTRAP_HEAD_SHA+"..."+self.FIRST:
            obj={"status":"ahead","behind_by":0,"ahead_by":2,
                 "total_commits":2,
                 "base_commit":{"sha":LEDGER_BOOTSTRAP_HEAD_SHA},
                 "commits":[{"sha":self.PARENT},{"sha":self.FIRST}]}
            if self.diff_mode=="nonlinear_branch":
                obj["behind_by"]=1
        else:
            raise AssertionError("unexpected GitHub endpoint:"+p)
        return 200,headers,json.dumps(obj).encode()


class FrozenFutureWitnessOnlySyntheticTests(unittest.TestCase):
    def setUp(self):
        self.p=read_protocol()
        self.g=fake_gateway(self.p)
        self.prepared=prepare_local_candidate(self.g,self.p,GENERATED,FROZEN)
        self.fake=SyntheticFirstAddGitHubWitnessHTTP(self.prepared["bytes"])

    def witness(self):
        return inspect_candidate_observed_first_add(
            self.prepared,self.g,self.p,GENERATED,FROZEN,
            send=self.fake,
        )

    def test_unique_first_add_pre_t12_existence_never_promotes(self):
        result=self.witness()
        self.assertEqual(len(self.fake.requests),6)
        self.assertEqual(result["observed_first_add_commit_sha"],self.fake.FIRST)
        self.assertEqual(result["observed_first_add_parent_sha"],self.fake.PARENT)
        self.assertTrue(result["candidate_existed_before_T12_at_observation"])
        self.assertTrue(result["unique_candidate_path_add_in_current_history"])
        self.assertTrue(result["observed_branch_ancestry_from_bootstrap"])
        self.assertEqual(result["candidate_sha256"],self.prepared["sha256"])
        for key in (
            "first_remote_candidate_receipt_verified",
            "github_network_responses_independently_authenticated",
            "remote_branch_force_push_history_excluded",
            "upstream_first_source_receipts_authenticated",
            "complete_capture_and_rescue_run_inventory_verified",
            "eligible_for_300_plus_300", "formal",
            "model_improvement_proven","promotion_allowed","production_changed",
        ):
            self.assertIs(result[key],False,key)

    def test_late_existence_or_untrusted_headers_rejected(self):
        for failure in ("late_existence","cached","missing_date",
                        "tampered_content","history_paginated"):
            self.fake=SyntheticFirstAddGitHubWitnessHTTP(self.prepared["bytes"])
            self.fake.diff_mode=failure
            with self.subTest(failure=failure),self.assertRaises(ValueError):
                self.witness()

    def test_path_was_modified_parent_already_had_it_or_diverged_branch(self):
        for failure in (
            "modified_second_commit","not_added","parent_still_exists",
            "nonlinear_branch",
        ):
            self.fake=SyntheticFirstAddGitHubWitnessHTTP(self.prepared["bytes"])
            self.fake.diff_mode=failure
            with self.subTest(failure=failure),self.assertRaises(ValueError):
                self.witness()

    def test_cli_readonly_witness_mode_uses_only_six_github_gets(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/"synthetic-gateway.json"
            path.write_text(json.dumps(self.g)+"\n",encoding="utf-8")
            report=run_from_gateway_file(
                path,GENERATED,FROZEN,
                observe_first_add=True,send=self.fake)
            self.assertEqual(report["status"],
                             "pinned_branch_unique_add_and_existence_preT12_unattested_first_receipt")
            self.assertEqual(len(self.fake.requests),6)
            self.assertIs(report["first_remote_candidate_receipt_verified"],False)
            self.assertIs(report["formal"],False)

    def test_cli_mutual_exclusion_cannot_accidentally_write_during_readonly_audit(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/"synthetic-gateway.json"
            path.write_text(json.dumps(self.g)+"\n",encoding="utf-8")
            with self.assertRaisesRegex(ValueError,"cannot_publish_and_observe"):
                run_from_gateway_file(
                    path,GENERATED,FROZEN,
                    publish=True,observe_first_add=True,
                    token="fake-unit-token",send=self.fake)
            self.assertEqual(self.fake.requests,[])

    def test_unregistered_prepared_candidate_rejected_before_remote_request(self):
        changed=dict(self.prepared)
        changed["sha256"]="0"*64
        with self.assertRaisesRegex(ValueError,"not_exact_frozen_bytes"):
            inspect_candidate_observed_first_add(
                changed,self.g,self.p,GENERATED,FROZEN,send=self.fake)
        self.assertEqual(self.fake.requests,[])

if __name__=="__main__":
    unittest.main()

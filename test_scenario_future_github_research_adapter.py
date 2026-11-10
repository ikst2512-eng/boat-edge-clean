"""Mocked GitHub HTTP contract tests; no Internet write, no forecast claims."""
import base64
from datetime import datetime
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from scenario_future_github_research_adapter import (
    API, GitHubOnlyCreateWire, REPO, _remote_path,
    run_from_gateway_file,
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

if __name__=="__main__":
    unittest.main()

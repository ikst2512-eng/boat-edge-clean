"""No-network exact F candidate first-add/parent/bootstrap/clock witness tests.

Every HTTP Date here is synthetic. These fixtures MUST NEVER be admitted
to future 300+300, interpreted as real Git first add, or as model accuracy.
"""
import base64
import copy
from datetime import datetime, timezone
from email.utils import format_datetime
import hashlib
import json
import unittest
from urllib.parse import parse_qs, urlsplit

from scenario_signed_st_F_remote_candidate_witness import (
    witness_existing_F_candidate, BASELINE_HEAD, F_LEDGER, PATH_ROOT,
)
from scenario_future_local_candidate_handoff import _git_blob_sha1
from test_scenario_signed_st_cross_ledger_audit import synth, canonical


def mocked_F_commit_api(prepared, flags=None):
    flags=flags or {}
    race=prepared["race_code"]
    path=PATH_ROOT+race+".json"
    head="c"*40
    first="b"*40
    parent=BASELINE_HEAD
    expected_bytes=prepared["bytes"]
    blob=_git_blob_sha1(expected_bytes)
    returned=[
        (200,{"ref":"refs/heads/"+F_LEDGER,
              "object":{"sha":head,"type":"commit"}}),
        (200,{"type":"file","path":path,"encoding":"base64",
              "sha":blob,"content":base64.b64encode(expected_bytes).decode()}),
        (200,[{"sha":first}]),
        (200,{"sha":first,"parents":[{"sha":parent}],
              "files":[{"filename":path,"status":"added","sha":blob}]}),
        (404,{"message":"Not Found"}),
        (200,{"status":"ahead","behind_by":0,"ahead_by":2,
              "total_commits":2,"base_commit":{"sha":BASELINE_HEAD},
              "commits":[{"sha":first},{"sha":head}]}),
    ]
    for i,v in flags.get("mutate",{}).items():
        returned[i]=v
    utc_times=flags.get("times",[
        "2026-11-12T10:45:20+00:00",
        "2026-11-12T10:45:21+00:00",
        "2026-11-12T10:45:22+00:00",
        "2026-11-12T10:45:23+00:00",
        "2026-11-12T10:45:24+00:00",
        "2026-11-12T10:45:25+00:00",
    ])
    requests=[]
    def send(req):
        index=len(requests)
        requests.append(req)
        if index>=len(returned):
            raise AssertionError("extra GET")
        url=urlsplit(req.full_url)
        path_check=[
            "/git/ref/heads/"+F_LEDGER,
            "/contents/"+path,
            "/commits",
            "/commits/"+first,
            "/contents/"+path,
            "/compare/"+BASELINE_HEAD+"..."+head,
        ]
        assert url.netloc=="api.github.com"
        assert url.path=="/repos/ikst2512-eng/boat-edge-clean"+path_check[index],(index,url.path)
        assert req.get_method()=="GET"
        if index in (1,4):
            assert parse_qs(url.query)=={"ref":[head if index==1 else parent]}
        if index==2:
            assert parse_qs(url.query)=={"sha":[head],"path":[path],"per_page":["100"]}
        response_status,response_body=returned[index]
        headers={"Date":format_datetime(
            datetime.fromisoformat(utc_times[index]).astimezone(timezone.utc),
            usegmt=True)}
        headers.update(flags.get("headers",{}).get(index,{}))
        return response_status,headers,json.dumps(response_body).encode()
    return send,requests


class FRemoteWitnessTests(unittest.TestCase):
    def setUp(self):
        self.prepared,_,_=synth()

    def call(self, flags=None):
        send,requests=mocked_F_commit_api(self.prepared,flags)
        output=witness_existing_F_candidate(self.prepared,send=send)
        self.assertEqual(len(requests),6)
        return output

    def test_synthetic_success_is_always_unattested(self):
        result=self.call()
        self.assertTrue(result["candidate_in_current_history_unique_add"])
        self.assertTrue(result["candidate_absent_at_first_add_parent"])
        self.assertTrue(result["candidate_branch_descends_from_pinned_baseline"])
        self.assertEqual(result["candidate_sha256"],self.prepared["sha256"])
        self.assertEqual(result["candidate_git_blob_sha1"],self.prepared["git_blob_sha1"])
        self.assertEqual(result["observed_added_commit_sha"],"b"*40)
        self.assertTrue(result["synthetic_predeadline_mock_not_evidence"])
        for key in (
            "actual_uncached_GET_existence_before_T12",
            "source_origin_and_first_receipt_authenticated",
            "first_remote_F_candidate_acceptance_verified",
            "capture_and_rescue_attempt_inventory_verified",
            "independent_600_cohort_admitted","outcomes_read","formal",
            "accuracy_improvement_proven","production_changed",
        ):
            self.assertIs(result[key],False,key)

    def test_wrong_blob_or_content_or_nonbase64_rejected(self):
        for mutation,error in (
            ({"sha":"0"*40},"head_content_invalid"),
            ({"content":base64.b64encode(b"different").decode()},"not_exact_preflight_bytes"),
            ({"content":"bad!base64"},"base64_invalid"),
        ):
            with self.subTest(mutation=mutation):
                send,_=mocked_F_commit_api(self.prepared)
                # Use injected API mutation, never mutate live data.
                good={
                    "type":"file","path":self.prepared["path"],
                    "sha":self.prepared["git_blob_sha1"],
                    "encoding":"base64",
                    "content":base64.b64encode(self.prepared["bytes"]).decode(),
                }
                good.update(mutation)
                send,_=mocked_F_commit_api(self.prepared,{"mutate":{1:(200,good)}})
                with self.assertRaisesRegex(ValueError,error):
                    witness_existing_F_candidate(self.prepared,send=send)

    def test_modified_initial_commit_and_existing_parent_denied(self):
        p=self.prepared
        detail={"sha":"b"*40,"parents":[{"sha":BASELINE_HEAD}],
                "files":[{"filename":p["path"],"status":"modified",
                          "sha":p["git_blob_sha1"]}]}
        send,_=mocked_F_commit_api(p,{"mutate":{3:(200,detail)}})
        with self.assertRaisesRegex(ValueError,"added_status_missing"):
            witness_existing_F_candidate(p,send=send)
        send,_=mocked_F_commit_api(p,{"mutate":{4:(200,{"path":p["path"]})}})
        with self.assertRaisesRegex(ValueError,"http_status_200"):
            witness_existing_F_candidate(p,send=send)

    def test_duplicate_path_history_and_unrelated_branch_rejected(self):
        p=self.prepared
        send,_=mocked_F_commit_api(p,{"mutate":{2:(200,[{"sha":"b"*40},{"sha":"d"*40}])}})
        with self.assertRaisesRegex(ValueError,"history_not_unique"):
            witness_existing_F_candidate(p,send=send)
        send,_=mocked_F_commit_api(p,{"mutate":{0:(200,{"ref":"refs/heads/main",
                   "object":{"sha":"c"*40,"type":"commit"}})}})
        with self.assertRaisesRegex(ValueError,"branch_ref_invalid"):
            witness_existing_F_candidate(p,send=send)

    def test_non_descendant_or_missing_original_add_commit_fail(self):
        p=self.prepared
        broken={"status":"diverged","behind_by":1,"ahead_by":2,
                "total_commits":2,"base_commit":{"sha":BASELINE_HEAD},
                "commits":[{"sha":"b"*40},{"sha":"c"*40}]}
        send,_=mocked_F_commit_api(p,{"mutate":{5:(200,broken)}})
        with self.assertRaisesRegex(ValueError,"not_descendant_of_pinned"):
            witness_existing_F_candidate(p,send=send)
        broken["status"]="ahead";broken["behind_by"]=0
        broken["commits"]=[{"sha":"a"*40},{"sha":"c"*40}]
        send,_=mocked_F_commit_api(p,{"mutate":{5:(200,broken)}})
        with self.assertRaisesRegex(ValueError,"not_in_baseline_ancestry"):
            witness_existing_F_candidate(p,send=send)

    def test_GitHub_cache_header_and_server_clock_regression_fail(self):
        p=self.prepared
        send,_=mocked_F_commit_api(p,{"headers":{1:{"Age":"60"}}})
        with self.assertRaisesRegex(ValueError,"cached_response_forbidden"):
            witness_existing_F_candidate(p,send=send)
        times=[
            "2026-11-12T10:45:20+00:00",
            "2026-11-12T10:45:23+00:00",
            "2026-11-12T10:45:22+00:00",
            "2026-11-12T10:45:24+00:00",
            "2026-11-12T10:45:25+00:00",
            "2026-11-12T10:45:26+00:00",
        ]
        send,_=mocked_F_commit_api(p,{"times":times})
        with self.assertRaisesRegex(ValueError,"dates_regressed"):
            witness_existing_F_candidate(p,send=send)

    def test_late_mock_cannot_claim_live_predeadline(self):
        times=[
            "2026-11-12T10:49:20+00:00",
            "2026-11-12T10:49:21+00:00",
            "2026-11-12T10:49:22+00:00",
            "2026-11-12T10:49:23+00:00",
            "2026-11-12T10:49:24+00:00",
            "2026-11-12T10:49:25+00:00",
        ]
        result=self.call({"times":times})
        self.assertFalse(result["actual_uncached_GET_existence_before_T12"])
        self.assertFalse(result["synthetic_predeadline_mock_not_evidence"])
        self.assertFalse(result["formal"])

    def test_forged_candidate_flags_and_changed_bytes_rejected_before_get(self):
        for field,bad in (
            ("formal",True),("candidate_first_remote_receipt_verified",True),
            ("future_cohort_admitted",True),("publish_implemented_here",True),
        ):
            with self.subTest(field=field):
                p=copy.deepcopy(self.prepared)
                p[field]=bad
                send,req=mocked_F_commit_api(p)
                with self.assertRaisesRegex(ValueError,"preflight_bytes_or_claim_invalid"):
                    witness_existing_F_candidate(p,send=send)
                self.assertEqual(req,[])
        p=copy.deepcopy(self.prepared)
        p["bytes"]+=b" "
        send,req=mocked_F_commit_api(p)
        with self.assertRaisesRegex(ValueError,"preflight_bytes_or_claim_invalid"):
            witness_existing_F_candidate(p,send=send)
        self.assertEqual(req,[])

    def test_forged_protocol_or_hidden_results_rejected_before_get(self):
        for k,bad in (
            ("protocol_git_blob_sha1","0"*40),
            ("result_or_payout_read",True),
            ("registered_same_race_paired_comparison",False),
            ("ticket_count_by_mode",{"narrow":4}),
        ):
            p=copy.deepcopy(self.prepared)
            decoded=json.loads(p["bytes"])
            decoded[k]=bad
            p["bytes"]=canonical(decoded)
            p["sha256"]=hashlib.sha256(p["bytes"]).hexdigest()
            p["git_blob_sha1"]=_git_blob_sha1(p["bytes"])
            send,req=mocked_F_commit_api(p)
            with self.subTest(field=k),self.assertRaisesRegex(ValueError,"unregistered_or_false_formal"):
                witness_existing_F_candidate(p,send=send)
            self.assertEqual(req,[])


if __name__=="__main__":
    unittest.main()

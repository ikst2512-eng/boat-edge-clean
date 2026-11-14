"""Synthetic, no-network cross-ledger compatibility and tampering tests.

Never simulate source/action receipt as an actual GitHub first remote witness.
"""
import base64
import copy
from datetime import datetime
import hashlib
import json
import unittest

from scenario_future_local_candidate_handoff import _git_blob_sha1
from scenario_signed_st_cross_ledger_audit import (
    audit_source_writer_against_signed_candidate, SCHEMA, F_LEDGER, SOURCE_LEDGER,
)
import scenario_signed_st_future_pre_t12_handoff as handoff
from scenario_signed_st_registered_shadow import PROTOCOL
from test_scenario_signed_st_future_pre_t12_handoff import audit_fixture, hypothetical_math


def canonical(payload):
    return (json.dumps(payload,sort_keys=True,ensure_ascii=False,
                       separators=(",",":"))+"\n").encode("utf-8")


def synth():
    audit=audit_fixture()
    protocol=json.loads(PROTOCOL.read_bytes())
    temporal=handoff.require_future_source_before_math(
        audit,protocol,datetime.fromisoformat("2026-11-12T19:45:00+09:00"))
    prepared=handoff.package_time_guarded_research_result(
        audit,protocol,hypothetical_math(),temporal,
        datetime.fromisoformat("2026-11-12T19:45:04+09:00"))
    race=audit["race_code"]
    cutoff=audit["cutoff_jst"]
    originals={}
    sources={}
    for cname,sname in (("racelist","racelist"),
                        ("beforeinfo","beforeinfo"),
                        ("odds120","odds")):
        raw=cname.encode()
        sha=hashlib.sha256(raw).hexdigest()
        sources[sname]={
            "bytes":len(raw),"sha256":sha,
            "received_at_jst":audit["latest_original_received_jst"],
        }
        originals[sname]={
            **sources[sname],
            "filename":{"racelist":"racelist.html",
                        "beforeinfo":"beforeinfo.json",
                        "odds":"original.html"}[sname],
            "base64":base64.b64encode(raw).decode("ascii"),
        }
    manifest={
        "schema":"OFFICIAL_REAUDITED_INPUT_MANIFEST_V1",
        "race_code":race,"cutoff_jst":cutoff,
        "official_sources":sources,
        "six_boat_inputs":[
            {"lane":i,"registration":str(4000+i),"exhibition_course":i}
            for i in range(1,7)],
    }
    basefields={k:manifest[k] for k in (
        "race_code","cutoff_jst","official_sources","six_boat_inputs")}
    manifest["input_sha256"]=hashlib.sha256(json.dumps(
        basefields,ensure_ascii=False,sort_keys=True,
        separators=(",",":")).encode()).hexdigest()
    shadow={
        "schema":"OFFICIAL_SIX_LANE_RESEARCH_SHADOW_V1",
        "race_code":race,
        "status":"research_shadow_generated_pre_t12",
        "generated":True,
        "research_only":True,
        "model_consumed_official_exhibition_fields":True,
        "generated_at_jst":"2026-11-12T19:44:30+09:00",
        "t12_cutoff_jst":cutoff,
        "official_input_sha256":manifest["input_sha256"],
        "formal_t12_certified":False,
        "independent_remote_first_seen_verified":False,
    }
    bundle={
        "schema":"OFFICIAL_RESEARCH_SOURCE_AND_SHADOW_BUNDLE_V1",
        "race_code":race,"cutoff_jst":cutoff,
        "research_only":True,
        "formal":False,
        "independent_remote_first_seen_verified":False,
        "final_race_entry_verified":False,
        "purchase_approved":False,
        "official_input_manifest":manifest,
        "official_raw_originals":originals,
        "official_research_shadow":shadow,
        "capture_action_context":{
            "same_run_source_paths_verified":True,
            "independent_remote_first_seen_verified":False,
            "source_collection_action_run_id":"43099999999",
            "source_collection_action_run_attempt":"1",
            "event":"schedule",
            "main_head_sha":"a"*40,
        },
    }
    raw=canonical(bundle)
    blob=_git_blob_sha1(raw)
    outcome={
        "race_code":race,
        "status":"new_research_bundle_first_add_put_and_get_matched",
        "path":f"official_source_forecast_bundles/{race[:8]}/{race}.json",
        "stored":True,"newly_stored":True,
        "sha256":hashlib.sha256(raw).hexdigest(),
        "git_blob_sha1":blob,
        "git_commit_file_blob_sha1":blob,
        "git_commit_sha":"b"*40,
        "git_commit_file_status":"added",
        "git_commit_added_path_verified":True,
        "put_response_observed_at_jst":"2026-11-12T19:45:21+09:00",
        "readback_response_observed_at_jst":"2026-11-12T19:45:23+09:00",
        "commit_status_observed_at_jst":"2026-11-12T19:45:24+09:00",
        "formal_t12_certified":False,
        "independent_remote_first_seen_verified":False,
    }
    receipt={
        "schema":"OFFICIAL_RESEARCH_GIT_WRITE_RECEIPT_V1",
        "status":"checked",
        "repository":"ikst2512-eng/boat-edge-clean",
        "ledger_branch":"entry-course-evidence-ledger",
        "action_event":"schedule",
        "action_run_id":"43099999999",
        "action_run_attempt":"1",
        "observed_at_jst":"2026-11-12T19:45:30+09:00",
        "newly_stored":1,
        "outcomes":[outcome],
        "research_only":True,
        "formal_t12_certified":False,
        "production_forecast":False,
        "independent_remote_first_seen_verified":False,
    }
    return prepared,bundle,receipt


def check(prepared,bundle,receipt):
    return audit_source_writer_against_signed_candidate(
        prepared,canonical(bundle),receipt)


class CrossLedgerTests(unittest.TestCase):
    def test_different_branch_same_race_bytes_match_but_first_seen_unverified(self):
        prepared,bundle,receipt=synth()
        out=check(prepared,bundle,receipt)
        self.assertEqual(out["schema"],SCHEMA)
        self.assertEqual(out["official_source_ledger_branch"],SOURCE_LEDGER)
        self.assertEqual(out["F_candidate_intended_ledger_branch"],F_LEDGER)
        self.assertNotEqual(SOURCE_LEDGER,F_LEDGER)
        self.assertTrue(out["source_writer_receipt_claims_added_and_readback"])
        self.assertEqual(out["source_original_sha256"],json.loads(
            prepared["bytes"])["source_original_sha256"])
        for key in ("source_writer_receipt_independently_authenticated",
                    "source_first_remote_receipt_verified",
                    "F_candidate_was_written_to_GitHub",
                    "F_candidate_first_remote_receipt_verified",
                    "source_and_F_candidate_are_same_model",
                    "formal","eligible_for_300_plus_300",
                    "accuracy_improvement_proven","production_changed"):
            self.assertIs(out[key],False,key)

    def test_batched_multi_race_source_receipts_do_not_require_single_race_run(self):
        p,b,r=synth()
        r["outcomes"].append({"race_code":"202611120712",
                              "status":"shadow_not_generated",
                              "newly_stored":False})
        self.assertEqual(check(p,b,r)["race_code"],"202611120711")
        r["outcomes"].append(copy.deepcopy(r["outcomes"][0]))
        r["newly_stored"]=2
        with self.assertRaisesRegex(ValueError,"ambiguous_or_missing_writer_race"):
            check(p,b,r)

    def test_source_wrong_branch_or_action_run_is_rejected(self):
        for field,new in (
            ("ledger_branch","scenario-four-mode-triple-source-evidence-ledger"),
            ("action_run_id","123456789"),
            ("action_event","push"),
        ):
            with self.subTest(field=field):
                p,b,r=synth()
                r[field]=new
                with self.assertRaisesRegex(ValueError,"wrong_official_writer_receipt"):
                    check(p,b,r)

    def test_source_raw_base64_or_sha_not_matching_candidate_rejected(self):
        p,b,r=synth()
        b["official_raw_originals"]["beforeinfo"]["base64"]=base64.b64encode(
            b"manipulated").decode()
        with self.assertRaisesRegex(ValueError,"original_bytes_or_chronology_mismatch"):
            check(p,b,r)
        p,b,r=synth()
        b["official_raw_originals"]["odds"]["sha256"]="0"*64
        with self.assertRaisesRegex(ValueError,"raw_source_manifest_sha_mismatch"):
            check(p,b,r)

    def test_source_writer_requires_first_add_and_exact_retrieved_blob(self):
        for field,value in (
            ("git_commit_file_status","modified"),
            ("git_commit_added_path_verified",False),
            ("git_blob_sha1","0"*40),
            ("git_commit_file_blob_sha1","0"*40),
            ("status","preexisting_identical_reused"),
            ("newly_stored",False),
        ):
            with self.subTest(field=field):
                p,b,r=synth()
                r["outcomes"][0][field]=value
                if field=="newly_stored":
                    r["newly_stored"]=0
                with self.assertRaisesRegex(ValueError,"official_source_first_add_not_supported"):
                    check(p,b,r)

    def test_too_late_or_reverse_write_observation_denied(self):
        for field,value in (
            ("put_response_observed_at_jst","2026-11-12T19:48:01+09:00"),
            ("readback_response_observed_at_jst","2026-11-12T19:45:20+09:00"),
            ("commit_status_observed_at_jst","2026-11-12T19:48:00+09:00"),
        ):
            with self.subTest(field=field):
                p,b,r=synth()
                r["outcomes"][0][field]=value
                with self.assertRaisesRegex(ValueError,"writer_timing_not_proven"):
                    check(p,b,r)

    def test_no_actions_local_receipt_can_claim_independent_first_seen(self):
        p,b,r=synth()
        r["independent_remote_first_seen_verified"]=True
        with self.assertRaisesRegex(ValueError,"wrong_official_writer_receipt"):
            check(p,b,r)
        p,b,r=synth()
        b["independent_remote_first_seen_verified"]=True
        with self.assertRaisesRegex(ValueError,"wrong_official_source_bundle"):
            check(p,b,r)

    def test_F_candidate_never_claims_formal_or_first_remote(self):
        p,b,r=synth()
        p["formal"]=True
        with self.assertRaisesRegex(ValueError,"unverified_candidate"):
            check(p,b,r)
        p,b,r=synth()
        candidate=json.loads(p["bytes"])
        candidate["future_cohort_admitted"]=True
        p["bytes"]=canonical(candidate)
        p["sha256"]=hashlib.sha256(p["bytes"]).hexdigest()
        p["git_blob_sha1"]=_git_blob_sha1(p["bytes"])
        with self.assertRaisesRegex(ValueError,"F_candidate_false_certification"):
            check(p,b,r)

    def test_missing_batch_race_or_failed_1746_writer_never_passes(self):
        p,b,r=synth()
        r["outcomes"]=[{"race_code":"202611120712",
                        "status":"unverified_writer_failure",
                        "newly_stored":False}]
        r["newly_stored"]=0
        with self.assertRaisesRegex(ValueError,"ambiguous_or_missing_writer_race"):
            check(p,b,r)
        p,b,r=synth()
        r["outcomes"][0]["status"]="unverified_writer_failure"
        with self.assertRaisesRegex(ValueError,"official_source_first_add_not_supported"):
            check(p,b,r)

    def test_official_manifest_is_recomputed_not_trusted_on_own_claim(self):
        p,b,r=synth()
        b["official_input_manifest"]["six_boat_inputs"][0]["registration"]="FAKE"
        with self.assertRaisesRegex(ValueError,"manifest_content_hash_changed"):
            check(p,b,r)
        p,b,r=synth()
        b["official_input_manifest"]["six_boat_inputs"][1]["lane"]=1
        values={k:b["official_input_manifest"][k] for k in (
            "race_code","cutoff_jst","official_sources","six_boat_inputs")}
        b["official_input_manifest"]["input_sha256"]=hashlib.sha256(
            json.dumps(values,sort_keys=True,ensure_ascii=False,
                       separators=(",",":")).encode()).hexdigest()
        b["official_research_shadow"]["official_input_sha256"]=b["official_input_manifest"]["input_sha256"]
        with self.assertRaisesRegex(ValueError,"six_boat_identity_invalid"):
            check(p,b,r)

    def test_candidate_claimed_latest_source_must_equal_actual_manifest(self):
        p,b,r=synth()
        payload=json.loads(p["bytes"])
        payload["latest_archive_source_received_claim_jst"]="2026-11-12T19:43:59+09:00"
        p["bytes"]=canonical(payload)
        p["sha256"]=hashlib.sha256(p["bytes"]).hexdigest()
        p["git_blob_sha1"]=_git_blob_sha1(p["bytes"])
        with self.assertRaisesRegex(ValueError,"F_candidate_source_receipts_not_aligned"):
            check(p,b,r)

    def test_duplicate_keys_in_source_bundle_rejected(self):
        p,b,r=synth()
        with self.assertRaisesRegex(ValueError,"source_bundle_json_unreadable"):
            audit_source_writer_against_signed_candidate(
                p,b'{"race_code":"A","race_code":"B"}',r)


if __name__=="__main__":
    unittest.main()

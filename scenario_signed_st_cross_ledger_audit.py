"""Read-only cross-ledger source/candidate contract for the F-aware study.

Compare a proposed F four-mode candidate with the DIFFERENT official-source
writer (#1746): entry-course-evidence-ledger / official_source_forecast_bundles.
The F candidate is intended for scenario-four-mode-triple-source-evidence-ledger
and has NOT been stored. These schemas, branches and first-add receipts are
NOT interchangeable.

This parser accepts externally supplied bytes and an Actions-local receipt;
it does not fetch the GitHub API, authenticate that receipt, establish remote
first-seen, publish a candidate or certify a prospective accuracy sample.
"""
import base64
import binascii
from datetime import datetime, timedelta
import hashlib
import json
import re

from scenario_signed_st_future_pre_t12_handoff import (
    SCHEMA as SIGNED_CANDIDATE_SCHEMA, PATH_ROOT as F_PATH_ROOT,
)
from scenario_future_local_candidate_handoff import _git_blob_sha1

SCHEMA="SIGNED_F_VS_OFFICIAL_SOURCE_WRITER_CROSS_LEDGER_READONLY_V1"
SOURCE_LEDGER="entry-course-evidence-ledger"
F_LEDGER="scenario-four-mode-triple-source-evidence-ledger"
SOURCE_ROOT="official_source_forecast_bundles/"
RACE=re.compile(r"20\d{6}(?:0[1-9]|1\d|2[0-4])(?:0[1-9]|1[0-2])\Z")
HEX40=re.compile(r"[0-9a-f]{40}\Z")
HEX64=re.compile(r"[0-9a-f]{64}\Z")
SOURCES={"racelist":"racelist","beforeinfo":"beforeinfo","odds120":"odds"}
JST=timedelta(hours=9)


def _uniq(pairs):
    result={}
    for key,value in pairs:
        if key in result:
            raise ValueError("cross_ledger_duplicate_json_key")
        result[key]=value
    return result


def _json(raw,limit,label):
    if type(raw) is not bytes or not 0<len(raw)<=limit:
        raise ValueError("cross_ledger_"+label+"_bytes_invalid")
    try:
        return json.loads(raw.decode("utf-8"),object_pairs_hook=_uniq,
                          parse_constant=lambda x: (_ for _ in ()).throw(
                              ValueError("nonfinite_number")))
    except (UnicodeError,ValueError) as exc:
        raise ValueError("cross_ledger_"+label+"_json_unreadable") from exc


def _time(s,label):
    if type(s) is not str:
        raise ValueError("cross_ledger_"+label+"_time_missing")
    try:
        t=datetime.fromisoformat(s)
    except (ValueError,OverflowError) as exc:
        raise ValueError("cross_ledger_"+label+"_time_unreadable") from exc
    if t.utcoffset()!=JST:
        raise ValueError("cross_ledger_"+label+"_clock_not_jst")
    return t


def audit_source_writer_against_signed_candidate(prepared, source_bundle_raw,
                                                 source_writer_receipt):
    """Never promote an Actions receipt to an authenticated GitHub witness.

    Prepared bytes need to originate from the future T-12 signed-F runner.
    Verify source ZIP contents of an externally obtained *new source bundle*
    against the candidate original digests and 1746 write receipt. Return
    zero prospective-cohort and zero first-receipt claims, even on a pass.
    """
    if (type(prepared) is not dict
            or prepared.get("schema")!="SIGNED_F_FOUR_MODE_LOCAL_DRYRUN_PREPARED_V1"
            or prepared.get("status")!="locally_prepared_unpublished_UNVERIFIED"
            or prepared.get("candidate_first_remote_receipt_verified") is not False
            or prepared.get("has_independent_first_receipt") is not False
            or prepared.get("future_cohort_admitted") is not False
            or prepared.get("publish_implemented_here") is not False
            or prepared.get("formal") is not False
            or type(source_writer_receipt) is not dict):
        raise ValueError("cross_ledger_unverified_candidate_or_receipt_contract")
    race=prepared.get("race_code")
    path=prepared.get("path")
    candidate_raw=prepared.get("bytes")
    if (type(race) is not str or RACE.fullmatch(race) is None
            or path!=F_PATH_ROOT+race+".json"
            or type(candidate_raw) is not bytes
            or not 0<len(candidate_raw)<=90000
            or prepared.get("sha256")!=hashlib.sha256(candidate_raw).hexdigest()
            or prepared.get("git_blob_sha1")!=_git_blob_sha1(candidate_raw)):
        raise ValueError("cross_ledger_candidate_path_or_bytes_tampered")
    candidate=_json(candidate_raw,90000,"F_candidate")
    if (candidate.get("schema")!=SIGNED_CANDIDATE_SCHEMA
            or candidate.get("race_code")!=race
            or candidate.get("result_or_payout_read") is not False
            or candidate.get("formal") is not False
            or candidate.get("candidate_first_remote_receipt_independently_proven") is not False
            or candidate.get("future_cohort_admitted") is not False
            or candidate.get("producer_local_clock_is_independent_witness") is not False
            or type(candidate.get("F_display_boat_count")) is not int
            or not 1<=candidate["F_display_boat_count"]<=6):
        raise ValueError("cross_ledger_F_candidate_false_certification")
    cutoff=_time(candidate.get("T_minus_12_cutoff_jst"),"cutoff")
    if _time(candidate.get("official_deadline_jst"),"deadline")-timedelta(minutes=12)!=cutoff:
        raise ValueError("cross_ledger_F_candidate_deadline_mismatch")
    if not _time(candidate.get("model_finished_local_jst"),"model_finish")<cutoff-timedelta(seconds=60):
        raise ValueError("cross_ledger_F_candidate_math_not_before_T12")

    source=_json(source_bundle_raw,900000,"source_bundle")
    official_path=f"{SOURCE_ROOT}{race[:8]}/{race}.json"
    if (type(source) is not dict
            or source.get("schema")!="OFFICIAL_RESEARCH_SOURCE_AND_SHADOW_BUNDLE_V1"
            or source.get("race_code")!=race
            or source.get("cutoff_jst")!=cutoff.isoformat()
            or source.get("research_only") is not True
            or source.get("formal") is not False
            or source.get("independent_remote_first_seen_verified") is not False
            or source.get("final_race_entry_verified") is not False
            or source.get("purchase_approved") is not False):
        raise ValueError("cross_ledger_wrong_official_source_bundle")
    context=source.get("capture_action_context")
    manifest=source.get("official_input_manifest")
    originals=source.get("official_raw_originals")
    if (type(context) is not dict or type(manifest) is not dict
            or type(originals) is not dict or set(originals)!=set(SOURCES.values())
            or context.get("same_run_source_paths_verified") is not True
            or context.get("independent_remote_first_seen_verified") is not False
            or manifest.get("schema")!="OFFICIAL_REAUDITED_INPUT_MANIFEST_V1"
            or manifest.get("race_code")!=race
            or manifest.get("cutoff_jst")!=cutoff.isoformat()
            or set(manifest.get("official_sources",{}))!=set(SOURCES.values())):
        raise ValueError("cross_ledger_source_action_and_manifest_invalid")
    # Rebuild #1746's canonical original-input manifest SHA rather than
    # trusting matching strings in a source archive and its Action receipt.
    manifest_fields=("race_code","cutoff_jst","official_sources","six_boat_inputs")
    if any(k not in manifest for k in manifest_fields):
        raise ValueError("cross_ledger_original_manifest_fields_missing")
    reconstructed=hashlib.sha256(json.dumps(
        {k:manifest[k] for k in manifest_fields},
        ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()).hexdigest()
    if manifest.get("input_sha256")!=reconstructed:
        raise ValueError("cross_ledger_original_manifest_content_hash_changed")
    boats=manifest.get("six_boat_inputs")
    if (type(boats) is not list or len(boats)!=6
            or any(type(x) is not dict for x in boats)
            or {x.get("lane") for x in boats}!={1,2,3,4,5,6}
            or {x.get("exhibition_course") for x in boats}!={1,2,3,4,5,6}
            or len({str(x.get("registration")) for x in boats})!=6):
        raise ValueError("cross_ledger_official_manifest_six_boat_identity_invalid")
    inputsha=candidate.get("source_original_sha256")
    if (type(inputsha) is not dict or set(inputsha)!=set(SOURCES)
            or any(type(v) is not str or HEX64.fullmatch(v) is None
                   for v in inputsha.values())):
        raise ValueError("cross_ledger_candidate_original_hashes_missing")
    received_by_kind={}
    for candidate_key,source_key in SOURCES.items():
        record=originals[source_key]
        manifest_entry=manifest["official_sources"][source_key]
        if (type(record) is not dict or type(manifest_entry) is not dict
                or record.get("sha256")!=inputsha[candidate_key]
                or manifest_entry.get("sha256")!=inputsha[candidate_key]
                or record.get("bytes")!=manifest_entry.get("bytes")
                or record.get("received_at_jst")!=manifest_entry.get("received_at_jst")
                or type(record.get("base64")) is not str):
            raise ValueError("cross_ledger_raw_source_manifest_sha_mismatch")
        try:
            raw=base64.b64decode(record["base64"],validate=True)
        except (ValueError,binascii.Error) as exc:
            raise ValueError("cross_ledger_original_base64_invalid") from exc
        when=_time(record["received_at_jst"],"original")
        if (not 0<len(raw)<=150000
                or len(raw)!=record["bytes"]
                or hashlib.sha256(raw).hexdigest()!=inputsha[candidate_key]
                or not when<cutoff):
            raise ValueError("cross_ledger_original_bytes_or_chronology_mismatch")
        received_by_kind[source_key]=when
    if (candidate.get("latest_archive_source_received_claim_jst")!=
            max(received_by_kind.values()).isoformat()
            or not max(received_by_kind.values())<
                _time(candidate.get("model_started_local_jst"),"F_model_start")):
        raise ValueError("cross_ledger_F_candidate_source_receipts_not_aligned")
    # The official shadow is a DIFFERENT heuristic, not the signed-F four-mode
    # model or proof that the latter generated its candidate before cutoff.
    shadow=source.get("official_research_shadow")
    if (type(shadow) is not dict
            or shadow.get("schema")!="OFFICIAL_SIX_LANE_RESEARCH_SHADOW_V1"
            or shadow.get("race_code")!=race
            or shadow.get("status")!="research_shadow_generated_pre_t12"
            or shadow.get("generated") is not True
            or shadow.get("research_only") is not True
            or shadow.get("model_consumed_official_exhibition_fields") is not True
            or shadow.get("official_input_sha256")!=manifest.get("input_sha256")
            or shadow.get("t12_cutoff_jst")!=cutoff.isoformat()
            or shadow.get("formal_t12_certified") is not False
            or shadow.get("independent_remote_first_seen_verified") is not False):
        raise ValueError("cross_ledger_unrelated_source_shadow_claim")
    shadow_generated=_time(shadow.get("generated_at_jst"),"source_shadow")
    if (not max(received_by_kind.values())<=shadow_generated<cutoff):
        raise ValueError("cross_ledger_source_shadow_timing_invalid")
    receipt=source_writer_receipt
    if (receipt.get("schema")!="OFFICIAL_RESEARCH_GIT_WRITE_RECEIPT_V1"
            or receipt.get("status")!="checked"
            or receipt.get("ledger_branch")!=SOURCE_LEDGER
            or receipt.get("repository")!="ikst2512-eng/boat-edge-clean"
            or receipt.get("research_only") is not True
            or receipt.get("formal_t12_certified") is not False
            or receipt.get("independent_remote_first_seen_verified") is not False
            or receipt.get("production_forecast") is not False
            or receipt.get("action_event")!=context.get("event")
            or receipt.get("action_run_id")!=context.get("source_collection_action_run_id")
            or receipt.get("action_run_attempt")!=context.get("source_collection_action_run_attempt")):
        raise ValueError("cross_ledger_wrong_official_writer_receipt")
    records=receipt.get("outcomes")
    if (type(records) is not list or not records
            or any(type(x) is not dict for x in records)
            or receipt.get("newly_stored")!=sum(x.get("newly_stored") is True for x in records)):
        raise ValueError("cross_ledger_writer_receipt_inventory_invalid")
    matches=[x for x in records if x.get("race_code")==race]
    if len(matches)!=1:
        raise ValueError("cross_ledger_ambiguous_or_missing_writer_race")
    stored=matches[0]
    if (type(stored) is not dict
            or stored.get("race_code")!=race
            or stored.get("path")!=official_path
            or stored.get("status")!="new_research_bundle_first_add_put_and_get_matched"
            or stored.get("stored") is not True
            or stored.get("newly_stored") is not True
            or stored.get("git_commit_added_path_verified") is not True
            or stored.get("git_commit_file_status")!="added"
            or stored.get("git_blob_sha1")!=_git_blob_sha1(source_bundle_raw)
            or stored.get("git_commit_file_blob_sha1")!=_git_blob_sha1(source_bundle_raw)
            or stored.get("sha256")!=hashlib.sha256(source_bundle_raw).hexdigest()
            or type(stored.get("git_commit_sha")) is not str
            or HEX40.fullmatch(stored["git_commit_sha"]) is None
            or stored.get("formal_t12_certified") is not False
            or stored.get("independent_remote_first_seen_verified") is not False):
        raise ValueError("cross_ledger_official_source_first_add_not_supported")
    # 1746's status reports locally observed response times, NOT independent
    # GitHub HTTP server acceptance times. Requiring every observation before
    # cutoff prevents a delayed receipt from masquerading as timely proof,
    # but does not certify independently observed first remote acceptance.
    stages=("put_response_observed_at_jst",
            "readback_response_observed_at_jst",
            "commit_status_observed_at_jst")
    prev=None
    for stage in stages:
        observed=_time(stored.get(stage),stage)
        if observed>=cutoff or (prev is not None and observed<prev):
            raise ValueError("cross_ledger_official_writer_timing_not_proven")
        prev=observed
    if _time(receipt.get("observed_at_jst"),"receipt")<prev:
        raise ValueError("cross_ledger_receipt_before_last_write_observation")
    return {
        "schema":SCHEMA,
        "status":"two_different_research_ledgers_source_local_receipt_and_F_bytes_consistent",
        "race_code":race,
        "official_source_ledger_branch":SOURCE_LEDGER,
        "F_candidate_intended_ledger_branch":F_LEDGER,
        "source_bundle_path":official_path,
        "F_candidate_unpublished_path":path,
        "source_original_sha256":dict(inputsha),
        "source_bundle_git_blob_sha1":_git_blob_sha1(source_bundle_raw),
        "F_candidate_unpublished_git_blob_sha1":prepared["git_blob_sha1"],
        "source_writer_receipt_claims_added_and_readback":True,
        "source_writer_receipt_independently_authenticated":False,
        "source_first_remote_receipt_verified":False,
        "F_candidate_was_written_to_GitHub":False,
        "F_candidate_first_remote_receipt_verified":False,
        "source_and_F_candidate_are_same_model":False,
        "formal":False,"eligible_for_300_plus_300":False,
        "accuracy_improvement_proven":False,"production_changed":False,
        "warning":"Untrusted Action-local receipt and cross-ledger byte checks are not independent remote first-seen, source HTTP provenance, or F-candidate first-add.",
    }

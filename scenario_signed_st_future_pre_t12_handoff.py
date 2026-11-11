"""Isolated one-shot signed-F FUTURE T-12 research candidate preflight.

This module NEVER writes a file, hits GitHub, runs a cron, fetches sources,
publishes a forecast or admits formal evaluation. It is the missing boundary
between pinned result-blind four-mode math and a future separately reviewed,
create-only remote writer with independent first-receipt evidence.

The underlying archived-math-only function may replay historical observations
for CI, but THIS preflight rejects them at the very first temporal gate:
actual local time must still be ahead of the race's T-minus-12 cutoff.
"""
from datetime import datetime, timedelta, timezone
import hashlib
import json
import math
from pathlib import Path
import re

from scripts.audit_three_official_t12_originals import audit_three_originals
from scenario_signed_st_registered_shadow import (
    archived_signed_F_four_mode_math_only,
    require_registered_signed_F_method,
    PROTOCOL_BLOB, STUDY_ID,
)
from scenario_future_local_candidate_handoff import _git_blob_sha1

JST = timezone(timedelta(hours=9))
SCHEMA = "SIGNED_F_FOUR_MODE_PRE_T12_UNPUBLISHED_HANDOFF_V1"
PATH_ROOT = "signed_f_four_mode_research/"
REMAINING_BEFORE_MATH_SECONDS = 90
REMAINING_AFTER_MATH_SECONDS = 60
VALID_MODES = {"narrow":5, "hit":10, "balance":16, "hole":22}
TICKET = re.compile(r"[1-6]-[1-6]-[1-6]\\Z")


def _jst(value, label):
    if (type(value) is not datetime
            or value.utcoffset()!=timedelta(hours=9)):
        raise ValueError("signed_F_"+label+"_clock_must_be_JST")
    return value


def _canonical(value):
    return (json.dumps(value,ensure_ascii=False,sort_keys=True,
                       separators=(",",":"),allow_nan=False)+"\\n").encode("utf-8")


def _timestamp(value, label):
    if type(value) is not str:
        raise ValueError("signed_F_"+label+"_source_timestamp_missing")
    try:
        d=datetime.fromisoformat(value)
    except (ValueError,OverflowError) as exc:
        raise ValueError("signed_F_"+label+"_source_timestamp_invalid") from exc
    return _jst(d,label)


def require_future_source_before_math(audit, protocol, observed_now):
    """Fail CLOSED before computing even one hypothetical ticket."""
    if (type(audit) is not dict or type(protocol) is not dict
            or audit.get("all_research_components_observed_by_t12") is not True
            or audit.get("three_originals_hash_verified") is not True
            or audit.get("missing_components") != []
            or type(audit.get("component_checks")) is not dict
            or len(audit["component_checks"]) != 12
            or any(v is not True for v in audit["component_checks"].values())
            or audit.get("t12_eligible") is not False
            or audit.get("forecast_usable") is not False):
        raise ValueError("signed_F_future_three_originals_incomplete")
    code=audit.get("race_code")
    if (type(code) is not str or not re.fullmatch(r"20[0-9]{10}",code)
            or not 1<=int(code[8:10])<=24 or not 1<=int(code[10:12])<=12):
        raise ValueError("signed_F_future_race_code_invalid")
    deadline=_timestamp(audit.get("official_deadline_jst"),"deadline")
    cutoff=_timestamp(audit.get("cutoff_jst"),"cutoff")
    latest=_timestamp(audit.get("latest_original_received_jst"),"source")
    start=_timestamp(protocol.get("eligible_new_race_deadline_start_jst"),"study_start")
    end=_timestamp(protocol.get("eligible_new_race_deadline_end_jst"),"study_end")
    now=_jst(observed_now,"pre_model_observation")
    if (deadline - timedelta(minutes=12)!=cutoff
            or not start<=deadline<=end
            or any(dt.strftime("%Y%m%d")!=code[:8]
                   for dt in (now,deadline,latest))
            or not latest<now
            or not now<cutoff-timedelta(seconds=REMAINING_BEFORE_MATH_SECONDS)):
        raise ValueError("signed_F_future_T12_cutoff_or_current_clock_failed")
    return {"race_code":code,"deadline":deadline,"cutoff":cutoff,
            "latest_source":latest,"pre_model_observed":now}


def package_time_guarded_research_result(audit, protocol, math, temporal, observed_after):
    """Prepare deterministic immutable bytes; never send them to any endpoint.

    This function's inputs can be mocked. The output remains formally
    unattested and is not eligible for a research cohort by itself.
    """
    if (type(math) is not dict
            or math.get("schema")!="REGISTERED_SIGNED_F_FOUR_MODE_ARCHIVED_MATH_ONLY_V1"
            or math.get("registered_study_protocol_git_blob_sha1")!=PROTOCOL_BLOB
            or math.get("registered_method_sources_checked_locally") is not True
            or math.get("actual_original_source_race_card_beforeinfo_odds120_reparsed") is not True
            or math.get("study_id")!=STUDY_ID
            or math.get("race_code")!=audit["race_code"]
            or math.get("F_boats") not in (1,2,3,4,5,6)
            or math.get("historical_archive_replay_not_predeadline_forecast") is not True
            or math.get("prospective_candidate_generated") is not False
            or math.get("results_or_payouts_read") is not False
            or math.get("formal") is not False):
        raise ValueError("signed_F_future_math_not_pinned_and_result_blind")
    after=_jst(observed_after,"post_model_observation")
    before=temporal["pre_model_observed"]
    cutoff=temporal["cutoff"]
    if (not before<=after<cutoff-timedelta(seconds=REMAINING_AFTER_MATH_SECONDS)
            or after.date()!=temporal["deadline"].date()):
        raise ValueError("signed_F_future_model_finished_too_late_for_T12")
    if math.get("same_4_mode_ticket_budgets")!=VALID_MODES:
        raise ValueError("signed_F_future_mode_budget_changed")
    for arm in ("math_4_modes_signed_F","math_4_modes_ST_zero_control"):
        modes=math.get(arm)
        if type(modes) is not dict or set(modes)!=set(VALID_MODES):
            raise ValueError("signed_F_future_four_modes_missing")
        for mode, count in VALID_MODES.items():
            row=modes[mode]
            if type(row) is not dict or set(row)!={"tickets","top1","full_120_mixture_sha256"}:
                raise ValueError("signed_F_future_mode_row_invalid")
            tickets=row["tickets"]
            if (type(tickets) is not list or len(tickets)!=count
                    or row["top1"]!=tickets[0].get("combo")
                    or type(row["full_120_mixture_sha256"]) is not str
                    or not re.fullmatch(r"[a-f0-9]{64}",row["full_120_mixture_sha256"])):
                raise ValueError("signed_F_future_mode_count_or_hash_invalid")
            seen=set()
            for item in tickets:
                if (type(item) is not dict or set(item)!={"combo","p"}
                        or type(item["combo"]) is not str
                        or not TICKET.fullmatch(item["combo"])
                        or len(set(item["combo"].split("-")))!=3
                        or item["combo"] in seen
                        or type(item["p"]) not in (float,int)
                        or not math_isfinite_probability_pct(item["p"])):
                    raise ValueError("signed_F_future_unranked_or_invalid_ticket")
                seen.add(item["combo"])
    source=math.get("source_original_sha256")
    feature=math.get("signed_feature_vector_sha256")
    if (type(source) is not dict or set(source)!={"racelist","beforeinfo","odds120"}
            or any(type(v) is not str or not re.fullmatch(r"[a-f0-9]{64}",v)
                   for v in source.values())
            or type(feature) is not str or not re.fullmatch(r"[a-f0-9]{64}",feature)):
        raise ValueError("signed_F_future_unverifiable_original_bytes")
    # The unverified local clock is never used to falsely certify a remote
    # or first-add timestamp. A separate writer must check actual GitHub
    # HTTP Date + commitment ancestry and always retain nonformal labels.
    frozen_payload={
        "schema":SCHEMA,
        "study_id":STUDY_ID,
        "race_code":audit["race_code"],
        "official_deadline_jst":temporal["deadline"].isoformat(),
        "T_minus_12_cutoff_jst":cutoff.isoformat(),
        "first_archive_source_received_claim_jst":audit.get("racelist_received_jst"),
        "latest_archive_source_received_claim_jst":temporal["latest_source"].isoformat(),
        "model_started_local_jst":before.isoformat(),
        "model_finished_local_jst":after.isoformat(),
        "protocol_git_blob_sha1":PROTOCOL_BLOB,
        "source_original_sha256":source,
        "signed_feature_vector_sha256":feature,
        "F_display_boat_count":math["F_boats"],
        "arm_signed_F":math["math_4_modes_signed_F"],
        "arm_ST_zero_control":math["math_4_modes_ST_zero_control"],
        "registered_same_race_paired_comparison":True,
        "ticket_count_by_mode":dict(VALID_MODES),
        "source_HTTP_first_remote_receipt_independently_proven":False,
        "candidate_first_remote_receipt_independently_proven":False,
        "future_cohort_admitted":False,
        "first_add_git_commit_proven":False,
        "producer_local_clock_is_independent_witness":False,
        "result_or_payout_read":False,
        "formal":False,"calibrated":False,
        "promotion_allowed":False,"production_changed":False,
        "accuracy_improvement_proven":False,
        "warning":"UNPUBLISHED local study bytes; not an authenticated predeadline prediction.",
    }
    raw=_canonical(frozen_payload)
    if len(raw)>90000:
        raise ValueError("signed_F_future_candidate_oversize")
    path=PATH_ROOT+audit["race_code"]+".json"
    return {
        "schema":"SIGNED_F_FOUR_MODE_LOCAL_DRYRUN_PREPARED_V1",
        "status":"locally_prepared_unpublished_UNVERIFIED",
        "race_code":audit["race_code"],
        "path":path,
        "bytes":raw,
        "sha256":hashlib.sha256(raw).hexdigest(),
        "git_blob_sha1":_git_blob_sha1(raw),
        "has_independent_first_receipt":False,
        "publish_implemented_here":False,
        "candidate_first_remote_receipt_verified":False,
        "future_cohort_admitted":False,
        "formal":False,
        "production_changed":False,
    }


def math_isfinite_probability_pct(value):
    return math.isfinite(value) and 0<=value<=100


def run_one_shot_unpublished(card_dir,beforeinfo_dir,odds_dir,
                             conditional_callback,clock):
    """Operator may call once while live; research-branch writer is separate."""
    if not callable(clock):
        raise ValueError("signed_F_future_clock_callback_required")
    protocol=require_registered_signed_F_method(conditional_callback)
    audit=audit_three_originals(card_dir,beforeinfo_dir,odds_dir)
    temporal=require_future_source_before_math(audit,protocol,clock())
    math_result=archived_signed_F_four_mode_math_only(
        card_dir,beforeinfo_dir,odds_dir,conditional_callback)
    return package_time_guarded_research_result(
        audit,protocol,math_result,temporal,clock())

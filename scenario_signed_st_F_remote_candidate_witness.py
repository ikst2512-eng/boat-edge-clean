"""Read-only first-add and T-12 observation of an F-aware RESEARCH candidate.

No PUT/POST, tokens, Cron, outcome reads, or proposal to merge. This tests
an *existing* file on the current GitHub research branch against the exact
preflight bytes. A first-add in current linear ancestry and a server Date
of a GET before the cutoff are NOT independent first remote acceptance.
For tests, injected HTTP responses are untrusted synthetic observations.
"""
import base64
import binascii
from datetime import datetime, timezone, timedelta
import hashlib
import json
import math
import re
import urllib.parse

from scenario_future_local_candidate_handoff import _git_blob_sha1
from scenario_signed_st_source_remote_witness import _get, _transport
from scenario_signed_st_future_pre_t12_handoff import (
    SCHEMA as BODY_SCHEMA, PATH_ROOT, VALID_MODES, _canonical,
)
from scenario_signed_st_registered_shadow import STUDY_ID, PROTOCOL_BLOB
from scenario_signed_st_cross_ledger_audit import F_LEDGER

SCHEMA="SIGNED_F_RESEARCH_CANDIDATE_GITHUB_READONLY_FIRST_ADD_V1"
BASELINE_HEAD="8443570d4a642c97bc700c9691ff7e8e4c5c314d"
SHA40=re.compile(r"[0-9a-f]{40}\Z")
SHA64=re.compile(r"[0-9a-f]{64}\Z")
CODE=re.compile(r"20[0-9]{6}(?:0[1-9]|1[0-9]|2[0-4])(?:0[1-9]|1[0-2])\Z")
JST=timedelta(hours=9)
CANDIDATE_FIELDS={
    "schema","study_id","race_code","official_deadline_jst",
    "T_minus_12_cutoff_jst","first_archive_source_received_claim_jst",
    "latest_archive_source_received_claim_jst","model_started_local_jst",
    "model_finished_local_jst","protocol_git_blob_sha1",
    "source_original_sha256","signed_feature_vector_sha256",
    "F_display_boat_count","arm_signed_F","arm_ST_zero_control",
    "registered_same_race_paired_comparison","ticket_count_by_mode",
    "source_HTTP_first_remote_receipt_independently_proven",
    "candidate_first_remote_receipt_independently_proven",
    "future_cohort_admitted","first_add_git_commit_proven",
    "producer_local_clock_is_independent_witness","result_or_payout_read",
    "formal","calibrated","promotion_allowed","production_changed",
    "accuracy_improvement_proven","warning",
}
TICKET=re.compile(r"[1-6]-[1-6]-[1-6]\\Z")


def _validate_preflight(prepared):
    required={"schema","status","race_code","path","bytes","sha256",
              "git_blob_sha1","has_independent_first_receipt",
              "publish_implemented_here",
              "candidate_first_remote_receipt_verified",
              "future_cohort_admitted","formal","production_changed"}
    if type(prepared) is not dict or set(prepared)!=required:
        raise ValueError("F_remote_expected_exact_unpublished_preflight_contract")
    race=prepared["race_code"]
    raw=prepared["bytes"]
    path=PATH_ROOT+str(race)+".json"
    if (type(race) is not str or not CODE.fullmatch(race)
            or prepared["schema"]!="SIGNED_F_FOUR_MODE_LOCAL_DRYRUN_PREPARED_V1"
            or prepared["status"]!="locally_prepared_unpublished_UNVERIFIED"
            or prepared["path"]!=path
            or type(raw) is not bytes or not 0<len(raw)<=90000
            or prepared["sha256"]!=hashlib.sha256(raw).hexdigest()
            or prepared["git_blob_sha1"]!=_git_blob_sha1(raw)
            or any(prepared[k] is not False for k in (
                "has_independent_first_receipt","publish_implemented_here",
                "candidate_first_remote_receipt_verified","future_cohort_admitted",
                "formal","production_changed"))):
        raise ValueError("F_remote_preflight_bytes_or_claim_invalid")
    def uniq(pairs):
        d={}
        for key,value in pairs:
            if key in d:
                raise ValueError("F_remote_duplicate_candidate_key")
            d[key]=value
        return d
    try:
        data=json.loads(raw.decode("utf-8"),object_pairs_hook=uniq,
                        parse_constant=lambda _: (_ for _ in ()).throw(
                            ValueError("nonfinite_F_candidate")))
    except (UnicodeError,ValueError) as exc:
        raise ValueError("F_remote_candidate_json_invalid") from exc
    if type(data) is not dict or _canonical(data)!=raw:
        raise ValueError("F_remote_candidate_not_canonical")
    if set(data)!=CANDIDATE_FIELDS:
        raise ValueError("F_remote_unregistered_candidate_field_or_result_smuggling")
    if (data.get("schema")!=BODY_SCHEMA or data.get("study_id")!=STUDY_ID
            or data.get("race_code")!=race
            or data.get("protocol_git_blob_sha1")!=PROTOCOL_BLOB
            or data.get("registered_same_race_paired_comparison") is not True
            or data.get("ticket_count_by_mode")!=VALID_MODES
            or type(data.get("F_display_boat_count")) is not int
            or not 1<=data["F_display_boat_count"]<=6
            or any(data.get(k) is not False for k in (
                "source_HTTP_first_remote_receipt_independently_proven",
                "candidate_first_remote_receipt_independently_proven",
                "future_cohort_admitted","first_add_git_commit_proven",
                "producer_local_clock_is_independent_witness",
                "result_or_payout_read","formal","calibrated",
                "promotion_allowed","production_changed",
                "accuracy_improvement_proven"))):
        raise ValueError("F_remote_unregistered_or_false_formal_candidate")
    if (type(data.get("source_original_sha256")) is not dict
            or set(data["source_original_sha256"])!={"racelist","beforeinfo","odds120"}):
        raise ValueError("F_remote_candidate_source_hash_missing")
    if (type(data.get("signed_feature_vector_sha256")) is not str
            or SHA64.fullmatch(data["signed_feature_vector_sha256"]) is None):
        raise ValueError("F_remote_signed_feature_sha_invalid")
    if any(type(x) is not str or SHA64.fullmatch(x) is None
           for x in data["source_original_sha256"].values()):
        raise ValueError("F_remote_candidate_source_hash_invalid")
    for arm in ("arm_signed_F","arm_ST_zero_control"):
        rows=data.get(arm)
        if type(rows) is not dict or set(rows)!=set(VALID_MODES):
            raise ValueError("F_remote_four_mode_pair_missing")
        for mode,count in VALID_MODES.items():
            v=rows[mode]
            if (type(v) is not dict
                    or set(v)!={"tickets","top1","full_120_mixture_sha256"}
                    or type(v["full_120_mixture_sha256"]) is not str
                    or SHA64.fullmatch(v["full_120_mixture_sha256"]) is None
                    or type(v["tickets"]) is not list
                    or len(v["tickets"])!=count
                    or type(v["top1"]) is not str):
                raise ValueError("F_remote_ticket_budget_mismatch")
            seen=set()
            for item in v["tickets"]:
                if (type(item) is not dict or set(item)!={"combo","p"}
                        or type(item["combo"]) is not str
                        or TICKET.fullmatch(item["combo"]) is None
                        or len(set(item["combo"].split("-")))!=3
                        or item["combo"] in seen
                        or type(item["p"]) not in (float,int)
                        or not math.isfinite(item["p"])
                        or not 0<=item["p"]<=100):
                    raise ValueError("F_remote_invalid_unranked_or_duplicate_ticket")
                seen.add(item["combo"])
            if v["top1"]!=v["tickets"][0]["combo"]:
                raise ValueError("F_remote_top1_not_first_ranked_ticket")
    try:
        cutoff=datetime.fromisoformat(data["T_minus_12_cutoff_jst"])
        began=datetime.fromisoformat(data["model_started_local_jst"])
        finished=datetime.fromisoformat(data["model_finished_local_jst"])
        source=datetime.fromisoformat(data["latest_archive_source_received_claim_jst"])
        first=datetime.fromisoformat(data["first_archive_source_received_claim_jst"])
        official_deadline=datetime.fromisoformat(data["official_deadline_jst"])
    except (ValueError,TypeError,KeyError) as exc:
        raise ValueError("F_remote_clock_unreadable") from exc
    if (any(dt.utcoffset()!=JST for dt in (
                cutoff,began,finished,source,first,official_deadline))
            or not first<=source<began<=finished<cutoff-timedelta(seconds=60)
            or official_deadline-cutoff!=timedelta(minutes=12)
            or cutoff.date().strftime("%Y%m%d")!=race[:8]
            or cutoff<datetime(2026,11,12,tzinfo=timezone(JST))):
        raise ValueError("F_remote_claimed_pre_T12_source_or_model_clock_invalid")
    return race,path,raw,cutoff,finished


def witness_existing_F_candidate(prepared, *, send=None):
    """Read-only observation; never treat mock Dates as actual evidence."""
    race,path,raw,cutoff,finished=_validate_preflight(prepared)
    transport=_transport if send is None else send
    if not callable(transport):
        raise ValueError("F_remote_network_callable_required")
    ref_time,ref,_=_get(transport,"/git/ref/heads/"+F_LEDGER)
    obj=ref.get("object") if type(ref) is dict else None
    head=obj.get("sha") if type(obj) is dict else None
    if (type(ref) is not dict
            or ref.get("ref")!="refs/heads/"+F_LEDGER
            or obj.get("type")!="commit"
            or type(head) is not str or SHA40.fullmatch(head) is None):
        raise ValueError("F_remote_branch_ref_invalid")
    file_time,contents,_=_get(
        transport,"/contents/"+path+"?"+
        urllib.parse.urlencode({"ref":head}))
    if (type(contents) is not dict or contents.get("path")!=path
            or contents.get("type")!="file"
            or contents.get("sha")!=prepared["git_blob_sha1"]
            or contents.get("encoding")!="base64"
            or type(contents.get("content")) is not str):
        raise ValueError("F_remote_candidate_head_content_invalid")
    try:
        restored=base64.b64decode("".join(contents["content"].splitlines()),
                                  validate=True)
    except (ValueError,binascii.Error) as exc:
        raise ValueError("F_remote_base64_invalid") from exc
    if restored!=raw:
        raise ValueError("F_remote_not_exact_preflight_bytes")
    hist_time,history,headers=_get(
        transport,"/commits?"+urllib.parse.urlencode({
            "sha":head,"path":path,"per_page":100}))
    if (type(history) is not list or len(history)!=1
            or type(history[0]) is not dict
            or any(k.lower()=="link" and 'rel="next"' in str(v)
                   for k,v in headers.items())):
        raise ValueError("F_remote_history_not_unique_in_current_branch")
    initial=history[0].get("sha")
    if type(initial) is not str or SHA40.fullmatch(initial) is None:
        raise ValueError("F_remote_first_add_commit_invalid")
    detail_time,detail,_=_get(transport,"/commits/"+initial)
    parents=detail.get("parents") if type(detail) is dict else None
    files=detail.get("files") if type(detail) is dict else None
    if (type(detail) is not dict or detail.get("sha")!=initial
            or type(parents) is not list or len(parents)!=1
            or type(parents[0]) is not dict
            or type(parents[0].get("sha")) is not str
            or SHA40.fullmatch(parents[0]["sha"]) is None
            or type(files) is not list
            or len([x for x in files if type(x) is dict and x.get("filename")==path
                    and x.get("status")=="added"
                    and x.get("sha")==prepared["git_blob_sha1"]])!=1):
        raise ValueError("F_remote_current_commit_added_status_missing")
    parent=parents[0]["sha"]
    parent_time,_,_=_get(transport,
        "/contents/"+path+"?"+urllib.parse.urlencode({"ref":parent}),
        expected=404)
    compare_time,comparison,compare_headers=_get(
        transport,"/compare/"+BASELINE_HEAD+"..."+head)
    if (type(comparison) is not dict or comparison.get("status")!="ahead"
            or comparison.get("behind_by")!=0
            or type(comparison.get("ahead_by")) is not int
            or not 1<=comparison["ahead_by"]<=200
            or comparison.get("total_commits")!=comparison["ahead_by"]
            or comparison.get("base_commit",{}).get("sha")!=BASELINE_HEAD
            or type(comparison.get("commits")) is not list
            or len(comparison["commits"])!=comparison["ahead_by"]
            or any(k.lower()=="link" and 'rel="next"' in str(v)
                   for k,v in compare_headers.items())):
        raise ValueError("F_remote_not_descendant_of_pinned_ledger_baseline")
    visited={x.get("sha") for x in comparison["commits"] if type(x) is dict}
    if (initial not in visited or head not in visited or
            (parent!=BASELINE_HEAD and parent not in visited)):
        raise ValueError("F_remote_first_add_not_in_baseline_ancestry")
    times=(ref_time,file_time,hist_time,detail_time,parent_time,compare_time)
    if any(a>b for a,b in zip(times,times[1:])):
        raise ValueError("F_remote_github_response_dates_regressed")
    direct=(send is None)
    # Server GET time is proof of existence THEN, NOT first receipt. Any
    # mock 200/GET is an algorithm fixture and must never count even if its
    # forged HTTP Date predates T-12.
    observed_predeadline=direct and finished.astimezone(timezone.utc)<file_time<cutoff.astimezone(timezone.utc)
    return {
        "schema":SCHEMA,
        "race_code":race,"study_id":STUDY_ID,
        "F_candidate_branch":F_LEDGER,
        "F_candidate_path":path,
        "candidate_git_blob_sha1":prepared["git_blob_sha1"],
        "candidate_sha256":prepared["sha256"],
        "pinned_ledger_baseline":BASELINE_HEAD,
        "observed_branch_head":head,
        "observed_added_commit_sha":initial,
        "candidate_in_current_history_unique_add":True,
        "candidate_absent_at_first_add_parent":True,
        "candidate_branch_descends_from_pinned_baseline":True,
        "github_server_observed_file_existing_at_utc":file_time.isoformat(),
        "actual_uncached_GET_existence_before_T12":observed_predeadline,
        "synthetic_predeadline_mock_not_evidence":not direct and file_time<cutoff.astimezone(timezone.utc),
        "current_ledger_history_cannot_exclude_prior_forcepush":True,
        "source_origin_and_first_receipt_authenticated":False,
        "first_remote_F_candidate_acceptance_verified":False,
        "capture_and_rescue_attempt_inventory_verified":False,
        "independent_600_cohort_admitted":False,
        "outcomes_read":False,"formal":False,
        "accuracy_improvement_proven":False,"production_changed":False,
        "warning":"Current branch history + source exact SHA + GET Date are not the independently attested first remote delivery, and a mock GET can never be a sample.",
    }

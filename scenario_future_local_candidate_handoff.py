"""Research-only, deterministic, result-blind #1710 candidate byte preparation.

No source collector, HTTP, scheduler, publisher, existing #1698 candidate
selector, old #1693 scorer or production change. A prepared local candidate
is NOT a remotely published forecast or a formally admitted 300+300 sample.

This is ONLY an adapter for the source-verified #1710 gateway output into a
create-only candidate handoff. The remote observer / receipt analysis MUST
be separately done; never infer first remote Git receipt from this output.
"""
from datetime import datetime, timedelta
import hashlib
from itertools import permutations
import json
import math
from pathlib import Path
import re

SCHEMA = "FOUR_MODE_TRIPLE_SOURCE_LOCAL_FROZEN_CANDIDATE_V1"
STUDY = "EXPLORATORY_ONLY_FUTURE_TRIPLE_SCENARIO_RESEARCH"
PATH_PREFIX = "scenario_four_mode_research/"
BUDGETS = {"narrow":5, "hit":10, "balance":16, "hole":22}
ALL_COMBOS = {"-".join(map(str,x)) for x in permutations(range(1,7),3)}
SHA64 = re.compile(r"[0-9a-f]{64}\Z")
OFFICIAL_MIN_DAY = "20261111"
MIN_REMAINING_SECONDS = 60
# Immutable November 10 protocol Git blob, created before future cohort starts.
# Its first remote commit alone does not prove any later candidate's timestamp.
PINNED_PROTOCOL_BLOB_SHA1 = "bf60d2879065d1f9ecbd6b442db17fcb8fbcb8b7"
PROTOCOL_PATH = Path(__file__).resolve().parent / (
    "research/four_mode_triple_source_forward_protocol_20261110.json"
)
PINNED_METHOD_NAMES = frozenset({
    "research_model.py",
    "clean_four_modes.py",
    "scenario_exhibition_all_mode_runner.py",
    "scenario_mode_specific_exhibition_end_to_end.py",
    "scenario_official_exhibition_projection.py",
    "scenario_first_head_research.py",
    "scenario_four_mode_bridge.py",
    "scenario_future_three_original_gateway.py",
    "scenario_official_racelist_rates.py",
    "scripts/audit_three_official_t12_originals.py",
})

def _git_blob_sha1(raw):
    return hashlib.sha1(
        b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()

def _reject_json_duplicates(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("frozen_study_duplicate_protocol_key")
        result[key] = value
    return result

def require_registered_study_and_unchanged_model(protocol):
    """Fail if runtime is using any protocol/model other than precommitted Nov 10.

    This does not authenticate remote Git or validate generated clock claims.
    """
    if type(protocol) is not dict or not PROTOCOL_PATH.is_file():
        raise ValueError("preregistered_protocol_missing_or_wrong_type")
    raw = PROTOCOL_PATH.read_bytes()
    if not raw or len(raw) > 15000 or _git_blob_sha1(raw) != PINNED_PROTOCOL_BLOB_SHA1:
        raise ValueError("preregistered_protocol_file_git_blob_mismatch")
    try:
        pinned = json.loads(
            raw, object_pairs_hook=_reject_json_duplicates,
            parse_constant=lambda _: (_ for _ in ()).throw(
                ValueError("preregistered_protocol_nonfinite")))
    except (ValueError, UnicodeError) as exc:
        raise ValueError("preregistered_protocol_unreadable") from exc
    if protocol != pinned:
        raise ValueError("preregistered_protocol_argument_modified")
    methods = pinned.get("method_git_blob_sha1")
    if type(methods) is not dict or set(methods) != PINNED_METHOD_NAMES:
        raise ValueError("preregistered_model_manifest_invalid")
    for name, sha in methods.items():
        p = PROTOCOL_PATH.parent.parent / name
        if (type(sha) is not str or not re.fullmatch(r"[a-f0-9]{40}",sha)
                or not p.is_file() or _git_blob_sha1(p.read_bytes()) != sha):
            raise ValueError("preregistered_method_source_changed:" + name)
    # Checked-out files are not proof of independent GitHub receipt; this is
    # the necessary runtime identity check before a candidate is prepared.
    return True

BLOCKED_FIELDS = frozenset({
    "finish_order","winning_ticket","confirmed_result","result",
    "confirmed_at_jst","payout","winning_combo","official_result",
    "post_race_weather","post_race_entry","confirmed_at","winner",
})


def _canonical(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True,
                       allow_nan=False, separators=(",",":"))+"\n").encode()


def _jst(value):
    try:
        dt=datetime.fromisoformat(value)
    except (ValueError,TypeError) as exc:
        raise ValueError("invalid_candidate_clock") from exc
    if dt.utcoffset()!=timedelta(hours=9):
        raise ValueError("candidate_clock_must_be_JST")
    return dt


def _outcomes_present(value):
    # Reuse the exact semantic boundary used in pre-result contracts; no
    # outcome-bearing metadata is allowed at *any* depth.
    pending=[value]
    seen=set()
    while pending:
        x=pending.pop()
        if type(x) not in (dict,list):
            continue
        if id(x) in seen:
            continue
        seen.add(id(x))
        if len(seen)>20000:
            raise ValueError("oversize_candidate_metadata")
        if type(x) is dict:
            if set(x) & BLOCKED_FIELDS:
                return True
            pending.extend(x.values())
        else:
            pending.extend(x)
    return False


def prepare_local_candidate(gateway, registered_protocol, generated_at_jst, frozen_at_jst):
    if (type(gateway) is not dict or type(registered_protocol) is not dict
            or _outcomes_present(gateway)
            or _outcomes_present(registered_protocol)
            or gateway.get("schema") !=
               "FUTURE_THREE_ORIGINAL_FOUR_MODE_RESEARCH_GATEWAY_V1"
            or gateway.get("study_id") != STUDY
            or registered_protocol.get("study_id") != STUDY
            or registered_protocol.get("schema") !=
               "FOUR_MODE_TRIPLE_SOURCE_PROSPECTIVE_RESEARCH_PROTOCOL_V1"
            or registered_protocol.get("status") !=
               "committed_research_protocol_not_active_no_confirmed_future_candidate"
            or registered_protocol.get("new_pilot_admitted") != 0
            or registered_protocol.get("new_confirmation_admitted") != 0):
        raise ValueError("unregistered_or_postresult_candidate")
    require_registered_study_and_unchanged_model(registered_protocol)
    assert_no_promotion = (
        "formal","forecast_usable","calibrated_probabilities",
        "accuracy_improvement_proven","production_changed",
        "promotion_allowed","results_read",
        "candidate_remote_first_receipt_verified",
        "eligible_for_existing_1693_600_races",
        "eligible_for_new_300_plus_300_races",
        "hypotheses_frozen_in_prospective_registration",
        "official_data_real_or_independently_authenticated",
        "official_racelist_HTTP_authenticity_independently_verified",
        "source_to_candidate_remote_receipt_proven",
    )
    if (any(gateway.get(k) is not False for k in assert_no_promotion)
            or gateway.get("candidate_source_consumption_structurally_replayed") is not True
            or gateway.get("official_triple_source_auditor_reported_complete") is not True
            or gateway.get("national_win_rate_from_official_original_structurally_verified") is not True):
        raise ValueError("candidate_source_or_unverified_promotion")
    code=gateway.get("race_code")
    lineage=gateway.get("source_lineage_preflight")
    if (type(code) is not str or not re.fullmatch(r"20\d{10}",code)
            or code[:8] < OFFICIAL_MIN_DAY
            or type(lineage) is not dict or lineage.get("race_code") != code
            or lineage.get("formal") is not False
            or lineage.get("auditor_component_count") != 12
            or lineage.get("registrations_matched_six") is not True
            or lineage.get("exhibition_entry_permutation_matched") is not True
            or lineage.get("initial_remote_candidate_receipt_verified") is not False):
        raise ValueError("invalid_future_source_lineage")
    begin=_jst(registered_protocol.get("eligible_deadline_start_jst"))
    end=_jst(registered_protocol.get("eligible_deadline_end_jst"))
    deadline=_jst(gateway.get("official_deadline_jst")
                  or (_jst(lineage["cutoff_jst"])+timedelta(minutes=12)).isoformat())
    cutoff=_jst(lineage.get("cutoff_jst"))
    if deadline-timedelta(minutes=12)!=cutoff or not begin<=deadline<=end:
        raise ValueError("unregistered_future_deadline")
    generated=_jst(generated_at_jst)
    frozen=_jst(frozen_at_jst)
    latest_source=_jst(lineage.get("latest_three_original_receipt_claim_jst"))
    if (not latest_source < generated <= frozen
            or not frozen < cutoff-timedelta(seconds=MIN_REMAINING_SECONDS)
            or any(dt.strftime("%Y%m%d") != code[:8]
                   for dt in (latest_source,generated,frozen,deadline))):
        raise ValueError("candidate_not_frozen_with_actual_T12_margin")
    rates=gateway.get("six_national_win_rates_from_same_original_html")
    if (type(rates) is not list or len(rates)!=6
            or any(type(x) not in (int,float) or not math.isfinite(x)
                   or not 0 < x <= 10 for x in rates)):
        raise ValueError("unverified_six_national_rates")
    registered_scens=registered_protocol.get("scenario_hypotheses")
    registered_weights=registered_protocol.get("mode_weights")
    # The committed protocol is JSON: 1 and 1.0 mean the same model
    # coefficient, but produce different raw JSON digests. The actual #1710
    # model creates mode weights as Python float(0.0/1.0). Canonicalize
    # numeric type ONLY; do not change any numerical coefficient or
    # recompute/tune weights from race outcomes. Protocol value equality is
    # separately pinned and checked by the existing freeze CI.
    if (type(registered_weights) is not dict
            or set(registered_weights) != set(BUDGETS)
            or any(type(v) is not dict or
                   any(type(w) not in (int,float) or not math.isfinite(w)
                       or not 0 <= w <= 1 for w in v.values())
                   for v in registered_weights.values())):
        raise ValueError("invalid_preregistered_mode_weights")
    canonical_weights={
        mode:{world:float(value) for world,value in registered_weights[mode].items()}
        for mode in BUDGETS
    }
    expected_signature=hashlib.sha256(json.dumps(
        {"scenarios":registered_scens,"weights":canonical_weights},
        sort_keys=True,ensure_ascii=False,
        separators=(",",":"),allow_nan=False).encode()).hexdigest()
    if gateway.get("hypothesis_signature_sha256")!=expected_signature:
        raise ValueError("unregistered_scenario_coefficients")
    method_pins=registered_protocol.get("method_git_blob_sha1")
    if (type(method_pins) is not dict or len(method_pins)!=10
            or any(type(v) is not str or not re.fullmatch(r"[0-9a-f]{40}",v)
                   for v in method_pins.values())):
        raise ValueError("unfrozen_model_source_blobs")
    digest_a=gateway.get("model_input_content_sha256_research_only")
    digest_b=gateway.get("four_mode_ranked_output_content_sha256_research_only")
    claim_source=lineage.get("source_sha256_claims")
    if (not all(type(x) is str and SHA64.fullmatch(x)
                for x in (digest_a,digest_b))
            or type(claim_source) is not dict
            or set(claim_source)!={"racelist","beforeinfo","odds120"}
            or any(type(x) is not str or not SHA64.fullmatch(x)
                   for x in claim_source.values())):
        raise ValueError("unbound_original_or_model_content_digest")
    data=gateway.get("research_mode_tickets")
    budgets=registered_protocol.get("mode_ticket_budgets")
    if type(data) is not dict or set(data)!=set(BUDGETS) or budgets!=BUDGETS:
        raise ValueError("wrong_four_mode_budget_contract")
    # Existing #1693 numerical scorer treats narrow Top10 as its complete
    # five tickets. That is NOT a ten-ticket Top10 endpoint. In the distinct
    # #1710 study the primary endpoint is Top1 and Top10 is only applicable
    # to modes with at least ten tickets. Keep this contract in the immutable
    # candidate so later assessors cannot silently substitute Top10=Top5.
    scientific = registered_protocol.get("scientific_protocol")
    if (type(scientific) is not dict
            or scientific.get("primary_endpoint") !=
               "paired_top1_exact_trifecta_by_mode_with_multiplicity_correction"
            or "top10_if_mode_budget_at_least_ten" not in
               scientific.get("secondary_endpoints", [])
            or set(scientific.get("non_inferiority_guardrails", [])) != {
                "top5_by_mode_not_worse_than_same_cohort_baseline",
                "top10_by_eligible_mode_not_worse_than_same_cohort_baseline",
            }):
        raise ValueError("incorrect_distinct_future_study_metric_policy")
    metric_applicability = {
        mode:{f"top{n}": n <= count for n in (1, 3, 5, 10)}
        for mode,count in BUDGETS.items()
    }
    assert metric_applicability["narrow"]["top10"] is False
    snapshots={}
    for mode,count in BUDGETS.items():
        info=data[mode]
        if (type(info) is not dict or set(info)!={"tickets","top1","research_board_sha256"}
                or type(info["tickets"]) is not list
                or len(info["tickets"])!=count
                or type(info["research_board_sha256"]) is not str
                or not SHA64.fullmatch(info["research_board_sha256"])):
            raise ValueError("missing_mode_or_board_sha")
        combos=[]
        for row in info["tickets"]:
            if (type(row) is not dict or type(row.get("combo")) is not str
                    or row["combo"] not in ALL_COMBOS
                    or type(row.get("p")) not in (int,float)
                    or not math.isfinite(row["p"]) or row["p"] < 0):
                raise ValueError("invalid_pre_result_ticket")
            combos.append(row["combo"])
        if len(set(combos))!=count or info["top1"]!=combos[0]:
            raise ValueError("duplicate_or_inconsistent_ranked_mode")
        snapshots[mode]={
            "top1":info["top1"],
            "tickets":info["tickets"],
            "research_board_sha256":info["research_board_sha256"],
        }
    payload={
        "schema":SCHEMA,
        "status":"locally_frozen_research_handoff_NOT_remote_forecast",
        "study_id":STUDY,
        "race_code":code,
        "official_deadline_jst":deadline.isoformat(),
        "T_minus_12_cutoff_jst":cutoff.isoformat(),
        "candidate_generation_self_report_jst":generated.isoformat(),
        "frozen_local_clock_self_report_jst":frozen.isoformat(),
        "source_original_sha256_claims":claim_source,
        "six_national_win_rates_from_official_racelist_original":rates,
        "model_input_content_sha256":digest_a,
        "four_mode_ranked_output_content_sha256":digest_b,
        "scenario_hypothesis_sha256":expected_signature,
        "research_method_blob_pins":dict(sorted(method_pins.items())),
        "ranked_mode_tickets":snapshots,
        "prospective_metric_applicability_not_results":metric_applicability,
        "distinct_new_study_primary_metric":"paired_top1_exact_trifecta_by_mode",
        "top10_for_narrow_must_never_mean_top5":True,
        "first_remote_candidate_receipt_verified":False,
        "candidate_publication_attempted":False,
        "original_first_remote_receipt_verified":False,
        "actual_official_HTTP_origin_independently_verified":False,
        "complete_actions_attempt_inventory_verified":False,
        "formal":False,
        "eligible_for_300_plus_300":False,
        "result_read":False,
        "model_improvement_proven":False,
        "production_changed":False,
        "promotion_allowed":False,
    }
    raw=_canonical(payload)
    path=PATH_PREFIX+code+".json"
    return {
        "schema":"FOUR_MODE_TRIPLE_SOURCE_LOCAL_CANDIDATE_HANDOFF_V1",
        "path":path,
        "race_code":code,
        "bytes":raw,
        "sha256":hashlib.sha256(raw).hexdigest(),
        "git_blob_sha1":hashlib.sha1(
            b"blob "+str(len(raw)).encode("ascii")+b"\0"+raw).hexdigest(),
        "candidate_first_remote_receipt_verified":False,
        "no_remote_write_performed":True,
        "formal":False,
        "promotion_allowed":False,
    }

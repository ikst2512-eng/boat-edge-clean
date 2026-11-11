"""PROTOTYPE ONLY: result-blind official-exhibition-aware 4-mode exploration.

Deterministic replay of a caller-supplied official-shaped source bundle with
real official-source parsers. Only exploratory, uncalibrated fixed heuristics:
no empirical evidence the coefficients improve accuracy. Odds never affect
the ranking. Existing CLEAN four-mode selector, PR #1698 position research,
production forecasts, and registered 300+300 cohort are UNCHANGED.

There is no live capture, dispatch, remote-first receipt, result read or write.
Any future formal method must be separately preregistered before its first
prospective prediction and approved after independent proof.
"""
import hashlib
import json
import math
from datetime import datetime, timedelta
from itertools import permutations
from pathlib import Path

from clean_four_modes import rank_modes
from four_mode_all_mode_same_job_shadow import candidate_modes
from four_mode_official_future_lineage_preflight import _canonical, _jst, SIZES
from four_mode_official_raw_semantic_replay import replay
from research_model import probabilities

SCHEMA = "FOUR_MODE_OFFICIAL_EXHIBITION_EXPLORATORY_PROTOTYPE_V1"
VERSION = "CLEAN_FOUR_MODES_V2_PROVISIONAL_UNCALIBRATED"
ALL = set(permutations(range(1, 7),3))
# No empirical fit. Frozen only within this testable unregistered prototype.
# Units: exhibition time sec difference / 0.1, ST sec difference / 0.1.
# Exhibition course is observed course, NOT final official entry.
COEFF = {
    "exhibition_time": 0.4,
    "exhibition_st": 0.3,
    "exhibition_course": 0.15,
    "place_weights": (1.0, 0.6, 0.35),
    "clamp": 3.0,
}


def _valid_original(original, race_code):
    if (type(original) is not dict
            or original.get("race_code") != race_code
            or original.get("model_version") != VERSION
            or original.get("beforeinfo") != "optional_not_in_snapshot"
            or not isinstance(original.get("source_sha256"),dict)
            or set(original["source_sha256"]) != {"race_cards","title"}
            or any(key in original for key in (
                "result","finish_order","winning_ticket","confirmed_result","payout"))):
        raise ValueError("wrong_unverified_original_or_outcome_leak")
    rates=original.get("input_national_win_rates")
    if (type(rates) is not list or len(rates)!=6
            or any(type(v) not in (int,float) or not math.isfinite(v)
                   or v<=0 or v>=20 for v in rates)):
        raise ValueError("invalid_pre_result_six_national_rates")
    # Replays the current original against its existing V2 ranking, without
    # modifying any tickets or using historical results.
    candidate_modes(original)
    return rates


def board(normalized, original):
    """Returns an exploratory, normalized 120-ticket score board.

    Do not interpret these normalized *scores* as calibrated hit probabilities.
    """
    if (type(normalized) is not dict or
            normalized.get("race_code") != original.get("race_code")
            or set(normalized) != {
                "race_code","source_sha256","racelist_registration_ids",
                "beforeinfo_registration_ids","exhibition_courses",
                "exhibition_times","exhibition_st","exhibition_tilts","odds_3t"}):
        raise ValueError("wrong_official_feature_claim")
    rates=_valid_original(original,normalized["race_code"])
    times=normalized["exhibition_times"]
    sts=normalized["exhibition_st"]
    courses=normalized["exhibition_courses"]
    if (any(type(x) not in (float,int) or not math.isfinite(x) for x in times+sts)
            or any(type(x) is not int or x not in range(1,7) for x in courses)
            or len(set(courses))!=6):
        raise ValueError("invalid_exhibition_features")
    mean_t=sum(times)/6
    mean_s=sum(sts)/6
    signal=[]
    for i in range(6):
        strength=(COEFF["exhibition_time"]*(mean_t-times[i])/0.1+
                  COEFF["exhibition_st"]*(mean_s-sts[i])/0.1+
                  COEFF["exhibition_course"]*(3.5-courses[i])/2.5)
        signal.append(max(-COEFF["clamp"],min(COEFF["clamp"],strength)))
    base=probabilities(rates)
    if len(base)!=120 or {ticket for ticket,_ in base}!=ALL:
        raise ValueError("unexpected_base_probability_roster")
    raw=[]
    for ticket,p in base:
        adjustment=sum(w*signal[boat-1] for w,boat in
                       zip(COEFF["place_weights"],ticket))
        raw.append((ticket,p*math.exp(adjustment)))
    total=sum(v for _,v in raw)
    if not (0 < total and math.isfinite(total)):
        raise ValueError("invalid_noncalibrated_score_total")
    out=sorted(((ticket,value/total) for ticket,value in raw),
               key=lambda x:(-x[1],x[0]))
    if not math.isclose(sum(value for _,value in out),1.0,abs_tol=1e-12):
        raise ValueError("prototype_normalization_failed")
    return out


def explore(source_bundle, original, *, generated_at_jst):
    """Compute ONLY an ephemeral research candidate after raw semantic replay."""
    if type(source_bundle) is not dict:
        raise ValueError("missing_source_bundle")
    code=source_bundle.get("race_code")
    rates=_valid_original(original,code)
    # Reuse normal candidate schema strictly as a preflight wrapper.
    # The *placeholder* tickets are not the prototype output and do not
    # establish any model consumption, source provenance or remote receipt.
    baseline=rank_modes(probabilities(rates))
    normalized=source_bundle.get("normalized_source_claim")
    if type(normalized) is not dict:
        raise ValueError("missing_source_normalization")
    provisional={
        "race_code":code, "deadline_jst":source_bundle["deadline_jst"],
        "generated_at_jst":generated_at_jst,
        "consumed_source_sha256": normalized["source_sha256"],
        "consumed_normalized_claim_sha256":
            hashlib.sha256(_canonical(normalized)).hexdigest(),
        "candidate_method_sha256": "0"*64,
        "candidate_tickets":{
            name:[t["combo"] for t in baseline[name]["tickets"]]
            for name in SIZES},
        "formal": False,
    }
    verified=replay(source_bundle,provisional)
    if verified["formal"] is not False:
        raise ValueError("unexpected_source_replay_formal_claim")
    ranked=board(normalized,original)
    mode_result=rank_modes(ranked)
    now=_jst(generated_at_jst)
    cutoff=_jst(source_bundle["deadline_jst"])-timedelta(minutes=12)
    if not now<cutoff:
        raise ValueError("late_prototype_generation")
    return {
        "schema":SCHEMA, "status":"exploratory_unregistered_nonformal_only",
        "race_code":code,
        "model_version":"OFFICIAL_EXHIBITION_HEURISTIC_UNREGISTERED_PROTOTYPE",
        "generated_at_jst":generated_at_jst,
        "deadline_jst":source_bundle["deadline_jst"],
        "consumed_source_sha256":dict(normalized["source_sha256"]),
        "consumed_normalized_claim_sha256":
            hashlib.sha256(_canonical(normalized)).hexdigest(),
        "method_source_sha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "heuristic_coefficients_non_empirical":dict(COEFF),
        "mode_tickets":{
            mode:[r["combo"] for r in mode_result[mode]["tickets"]]
            for mode in SIZES
        },
        "model_scores_calibrated":False,
        "official_odds_used_for_rank":False,
        "official_exhibition_features_used_for_rank":True,
        "source_bytes_reparsed_before_computation":True,
        "real_official_http_origin_independently_proven":False,
        "actual_remote_first_receipt_verified":False,
        "selector_preregistered_for_formal_cohort":False,
        "formal":False,"candidate_frozen_remotely":False,
        "future_pairs_admitted":0,"model_improvement_proven":False,
        "model_promotion_allowed":False,
        "warning":"Experimental arbitrary unvalidated coefficients and "
                  "source/clock provenance not independently attested. "
                  "No official hit probability, existing selector, formal "
                  "study or live prediction is altered.",
    }

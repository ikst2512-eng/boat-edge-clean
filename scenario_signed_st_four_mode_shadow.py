"""Separate F-aware four-mode math SHADOW, not the registered #1710 candidate.

Uses exactly the existing #1710 first-head transform, the pinned #1698
conditional-second/third research callback, and the existing #1710 four-mode
120-combination composer. F flags retain sign; L and incomplete input fail
closed. This module does NO fetch, output file, Git write, result read, or
live candidate publication. All results are hypothetical and uncalibrated.

A future PROSPECTIVE forecast would require a distinct study freeze, actual
same-race original source consumption, pre-T-12 create-only Git receipt,
independent witness and result-last 300+300 validation. This is not that.
"""
import hashlib
import json
import math
from decimal import Decimal, InvalidOperation

from research_model import probabilities
from scenario_first_head_research import hypothetical_head_board
from scenario_exhibition_all_mode_runner import _conditional_result
from scenario_four_mode_bridge import (
    _valid_board, compose_scenario_research, MODES, BUDGETS, SCENARIOS,
)
from scenario_flagged_st_feature_study import SCHEMA as SIGNED_SCHEMA
from scenario_official_st_intake_diagnostic import FLAGGED_ST, NUMERIC_ST

SCHEMA = "SEPARATE_SIGNED_F_ST_FOUR_MODE_SHADOW_V1"
STUDY_ID = "EXPLORATORY_ONLY_SIGNED_F_ST_4MODE_SHADOW_V1"
BOATS = set(range(1, 7))
MODES_SET = set(MODES)
FIELDS = {"exhibition_st_s", "exhibition_time_s", "entry_course"}
SIGNED_FIELDS = {
    "schema","study_scope","frozen_1693_1710_method_changed",
    "source_complete_12_of_12","race_code","beforeinfo_source_sha256",
    "vector_sha256","exhibition_st_by_boat","flag_F_count","flag_L_count",
    "numeric_display_count","signed_numeric_available_for_all_six",
    "flagged_display_is_main_race_F_or_L",
    "F_label_interpreted_as_before_zero_only",
    "L_display_time_offset_independently_verified","signed_feature_calibrated",
    "model_executed","candidate_created",
    "official_first_remote_receipt_verified",
    "candidate_first_remote_receipt_verified",
    "eligible_for_existing_300_plus_300","formal",
    "accuracy_improvement_proven","production_changed","warning",
}
ENTRY_FIELDS = {"boat","exhibition_course_only","official_st_raw",
                "display_class","signed_st_seconds_decimal_string",
                "numeric_model_input_authorized"}


def _canon(value):
    return json.dumps(value,sort_keys=True,separators=(",",":"),
                      ensure_ascii=False,allow_nan=False).encode("utf-8")


def _signed_vector(signed):
    if type(signed) is not dict or set(signed) != SIGNED_FIELDS:
        raise ValueError("signed_feature_contract_invalid")
    if (signed["schema"] != SIGNED_SCHEMA
            or signed["study_scope"] != "separate_exploratory_feature_encoding_no_forecast"
            or signed["frozen_1693_1710_method_changed"] is not False
            or signed["source_complete_12_of_12"] is not True
            or signed["signed_feature_calibrated"] is not False
            or signed["model_executed"] is not False
            or signed["candidate_created"] is not False
            or signed["official_first_remote_receipt_verified"] is not False
            or signed["candidate_first_remote_receipt_verified"] is not False
            or signed["eligible_for_existing_300_plus_300"] is not False
            or signed["formal"] is not False
            or signed["accuracy_improvement_proven"] is not False
            or signed["production_changed"] is not False
            or signed["flagged_display_is_main_race_F_or_L"] is not False
            or signed["F_label_interpreted_as_before_zero_only"] is not True
            or signed["L_display_time_offset_independently_verified"] is not False):
        raise ValueError("signed_feature_formal_or_semantic_claim_invalid")
    code=signed["race_code"]
    digest=signed["beforeinfo_source_sha256"]
    if (type(code) is not str or len(code)!=12 or not code.isdigit()
            or type(digest) is not str or len(digest)!=64
            or any(ch not in "0123456789abcdef" for ch in digest)):
        raise ValueError("signed_feature_race_or_source_identity_invalid")
    entries=signed["exhibition_st_by_boat"]
    if type(entries) is not list or len(entries)!=6:
        raise ValueError("signed_ST_six_boats_required")
    expected=hashlib.sha256(_canon({
        "race_code":code,"beforeinfo_source_sha256":digest,
        "exhibition_st_by_boat":entries,
    })).hexdigest()
    if signed["vector_sha256"]!=expected:
        raise ValueError("signed_ST_vector_sha256_mismatch")
    rows=[]
    f=l=0
    for lane,entry in enumerate(entries,1):
        if (type(entry) is not dict or set(entry)!=ENTRY_FIELDS
                or type(entry["boat"]) is not int or entry["boat"]!=lane
                or type(entry["exhibition_course_only"]) is not int
                or entry["exhibition_course_only"] not in BOATS
                or entry["numeric_model_input_authorized"] is not False):
            raise ValueError("invalid_signed_ST_boat_or_course")
        raw=entry["official_st_raw"]
        cls=entry["display_class"]
        value=entry["signed_st_seconds_decimal_string"]
        if type(raw) is not str or type(cls) is not str:
            raise ValueError("invalid_signed_ST_display")
        try:
            if cls=="F" and FLAGGED_ST.fullmatch(raw) and raw[0]=="F":
                v=Decimal("-"+raw[1:])
                f+=1
            elif cls=="L" and FLAGGED_ST.fullmatch(raw) and raw[0]=="L":
                if value is not None:
                    raise ValueError("L_seconds_must_remain_uninterpreted")
                l+=1
                v=None
            elif cls=="normal" and NUMERIC_ST.fullmatch(raw):
                v=Decimal(raw)
            else:
                raise ValueError("signed_ST_original_lexeme_class_mismatch")
            if v is not None and (type(value) is not str
                    or Decimal(value)!=v
                    or value!=str(v)):
                raise ValueError("signed_ST_numeric_value_not_bound_to_display")
        except InvalidOperation as exc:
            raise ValueError("signed_ST_numeric_invalid") from exc
        rows.append(v)
    if (set(e["exhibition_course_only"] for e in entries)!=BOATS
            or signed["flag_F_count"]!=f or signed["flag_L_count"]!=l
            or signed["numeric_display_count"]!=6-f-l
            or signed["signed_numeric_available_for_all_six"] is not (l==0)):
        raise ValueError("signed_ST_flags_or_courses_inconsistent")
    if l:
        raise ValueError("L_flag_no_unambiguous_numeric_seconds")
    # Pinned #1698 accepts -0.5..1.0 s; never clip large F values.
    out=[float(v) for v in rows]
    if not all(math.isfinite(x) and -0.5<=x<=1.0 for x in out):
        raise ValueError("signed_ST_outside_pinned_1698_feature_range")
    return out


def signed_F_four_mode_math(signed_feature, national_rates, exhibition_times,
                            scenarios, mode_weights, conditional_callback,
                            *, study_id=STUDY_ID):
    """Four complete 120-board research lenses; no official or time certification.

    The F-aware caller must separately validate official source timestamps,
    racer registrations and identity. Calling this pure function is NOT a
    prospective prediction, accuracy measurement, or first Git receipt.
    """
    if study_id!=STUDY_ID or not callable(conditional_callback):
        raise ValueError("independent_F_feature_study_or_pinned_1698_callback_required")
    st=_signed_vector(signed_feature)
    if (type(national_rates) is not list or len(national_rates)!=6
            or any(type(x) not in (int,float) or not math.isfinite(x)
                   or not 0<x<=10 for x in national_rates)):
        raise ValueError("six_racelist_national_rates_required_unattested")
    if (type(exhibition_times) is not list or len(exhibition_times)!=6
            or any(type(x) not in (int,float) or not math.isfinite(x)
                   or not 5<=x<=10 for x in exhibition_times)):
        raise ValueError("six_official_exhibition_times_required_unattested")
    if type(scenarios) is not dict or not scenarios or set(scenarios)-SCENARIOS:
        raise ValueError("signed_four_mode_scenario_names_invalid")
    if type(mode_weights) is not dict or set(mode_weights)!=MODES_SET:
        raise ValueError("signed_four_modes_require_four_declared_weights")
    for key,value in scenarios.items():
        if type(value) is not dict or set(value)!={"head_log_shifts","position_coefficients"}:
            raise ValueError("signed_four_mode_scenario_contract_invalid")
        coeff=value["position_coefficients"]
        if type(coeff) is not dict or not coeff or set(coeff)-FIELDS:
            raise ValueError("signed_four_mode_only_observed_features")
        for v in coeff.values():
            if type(v) is not dict or set(v)!={"second","third"}:
                raise ValueError("signed_four_mode_position_coefficients_invalid")
        for w in mode_weights.values():
            if type(w) is not dict or set(w)!=set(scenarios):
                raise ValueError("signed_four_mode_worlds_not_identical")
    base=probabilities(national_rates)
    entries=signed_feature["exhibition_st_by_boat"]
    evidence={"boats":[{
        "boat":i,
        "exhibition_st_s":st[i-1],
        "exhibition_time_s":exhibition_times[i-1],
        "entry_course":entries[i-1]["exhibition_course_only"],
    } for i in range(1,7)],"context":{}}
    boards={}
    activated={}
    for scenario in sorted(scenarios):
        plan=scenarios[scenario]
        prior=hypothetical_head_board(
            base,plan["head_log_shifts"],
            study_id=study_id+"_HEAD_"+scenario.upper())
        coeffs=plan["position_coefficients"]
        active={key for key,pair in coeffs.items()
                if pair["second"]!=0 or pair["third"]!=0}
        response=conditional_callback(prior["ranked_board"],evidence,coeffs,
            study_id+"_PAIR_"+scenario.upper())
        boards[scenario]=_conditional_result(
            response,prior["ranked_board"],active)
        activated[scenario]=sorted(active)
    digests=None
    modes={}
    for mode in MODES:
        mixed=compose_scenario_research(boards,mode_weights[mode])
        if (mixed["formal"] is not False or mixed["promotion_allowed"] is not False
                or mixed["forecast_usable"] is not False
                or mixed["probabilities_calibrated"] is not False):
            raise ValueError("signed_four_mode_promoted_provenance_forbidden")
        current=mixed["scenario_board_sha256"]
        if digests is None:
            digests=current
        if current!=digests:
            raise ValueError("signed_four_mode_scenarios_changed_between_modes")
        selected=mixed["existing_four_mode_selector_on_mixture"][mode]["tickets"]
        if len(selected)!=BUDGETS[mode]:
            raise ValueError("signed_four_mode_ticket_budget_mismatch")
        modes[mode]={
            "tickets":selected,
            "top1":selected[0]["combo"],
            "full_120_mixture_sha256":mixed["mixed_120_board_sha256"],
        }
    return {
        "schema":SCHEMA,"study_id":study_id,
        "status":"math_only_unregistered_future_forecast",
        "race_code":signed_feature["race_code"],
        "signed_feature_vector_sha256":signed_feature["vector_sha256"],
        "unattested_six_national_rates":list(national_rates),
        "unattested_six_exhibition_times":list(exhibition_times),
        "scenario_weights_and_coefficients_fixed_by_caller_not_yet_registered":True,
        "scenario_120_boards":digests,
        "active_features_by_scenario":activated,
        "four_mode_hypothetical_tickets":modes,
        "all_mode_tickets":dict(BUDGETS),
        "official_same_race_racelist_rate_source_independently_verified":False,
        "official_first_remote_receipt_verified":False,
        "candidate_created":False,
        "candidate_first_remote_receipt_verified":False,
        "model_math_executed":True,
        "model_probabilities_calibrated":False,
        "eligible_for_prior_600":False,
        "eligible_for_future_600":False,
        "outcomes_read":False,
        "formal":False,"betting_recommendation":False,
        "accuracy_improvement_proven":False,"production_changed":False,
        "promotion_allowed":False,
        "warning":"Standalone math test ONLY, not a predeadline authenticated candidate.",
    }

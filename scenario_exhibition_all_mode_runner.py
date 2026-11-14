"""Research-only all-mode scenario runner using the existing #1698 lab contract.

No #1698 implementation is copied here: an injected conditional callback
must satisfy that Draft's contract. #1710's projected exhibition values are
caller-supplied structural inputs, not authenticated current official data.
Head shifts, second/third coefficients and scenario weights are explicit,
UNCALIBRATED experiment hypotheses. No live prediction, result read or I/O.
"""
import copy
import hashlib
import json
import math
import re

from research_model import probabilities
from scenario_first_head_research import hypothetical_head_board
from scenario_four_mode_bridge import (
    SCENARIOS, _valid_board, compose_scenario_research,
)

HEX = re.compile(r"[0-9a-f]{64}\Z")
ID = re.compile(r"EXPLORATORY_ONLY_[A-Z0-9_]{4,46}\Z")
# #1698 unregistered lab now accepts actual 5–10s exhibition time.
# These remain hypothetical effects, not calibrated importance.
FIELDS = frozenset({"exhibition_st_s", "exhibition_time_s", "entry_course"})
MISSING = frozenset({
    "actual_entry_course", "motor_2ren_pct", "wind_speed_mps",
    "wind_from_true_deg", "start_heading_true_deg",
    "wave_height_cm", "tide_station", "tide_height_cm", "tide_phase",
    "two_course_escape_assist_rate", "two_course_wall_rate",
})
BLOCKED = frozenset({"result", "finish_order", "winning_ticket",
                     "payout", "post_race_weather", "final_entry_course"})
PAIR_SCHEMA = "SCENARIO_OBSERVED_BEFOREINFO_ODDS_PAIR_RESEARCH_V1"
PAIR_EXTRA_KEYS = frozenset({
    "source_original_zip_sha256",
    "racelist_original_missing",
    "source_pair_only_no_new_forecast_receipt",
    "weather_observation_clock_unverified",
})

PROJECTION_KEYS = frozenset({
    "schema", "race_code", "source_sha256", "normalized_source_sha256",
    "exhibition_features_by_boat", "exhibition_features_sha256",
    "structural_source_to_candidate_order", "structural_raw_semantic_replay_reported",
    "missing_research_features", "feature_values_imputed",
    "exhibition_is_actual_final_entry", "raw_http_origin_independently_attested",
    "replay_callback_authenticity_independently_proven",
    "candidate_first_remote_receipt_verified",
    "model_consumed_these_features_verified",
    "all_scenario_effect_coefficients_calibrated", "formal",
    "accuracy_effect_proven", "promotion_allowed", "production_changed",
})


def _projected(projection):
    # The two-source original is an EXPLICITLY SEPARATE research-only input:
    # no invented racelist SHA, no pretended three-source replay/forecast.
    pair_only = type(projection) is dict and projection.get("schema") == PAIR_SCHEMA
    expected_keys = PROJECTION_KEYS | PAIR_EXTRA_KEYS if pair_only else PROJECTION_KEYS
    if (type(projection) is not dict
            or set(projection) != expected_keys
            or projection.get("schema") not in (
                PAIR_SCHEMA if pair_only else "SCENARIO_EXHIBITION_PROJECTION_RESEARCH_V1",
            )
            or projection.get("formal") is not False
            or projection.get("production_changed") is not False
            or projection.get("promotion_allowed") is not False
            or projection.get("exhibition_is_actual_final_entry") is not False
            or projection.get("raw_http_origin_independently_attested") is not False
            or projection.get("replay_callback_authenticity_independently_proven") is not False
            or projection.get("candidate_first_remote_receipt_verified") is not False
            or projection.get("model_consumed_these_features_verified") is not False
            or projection.get("feature_values_imputed") is not False
            or projection.get("structural_source_to_candidate_order") is not (not pair_only)
            or projection.get("all_scenario_effect_coefficients_calibrated") is not False
            or projection.get("accuracy_effect_proven") is not False
            or projection.get("structural_raw_semantic_replay_reported") is not (not pair_only)
            or set(projection) & BLOCKED):
        raise ValueError("unsafe_or_unmatched_official_projection")
    code = projection.get("race_code")
    if (type(code) is not str or not re.fullmatch(r"20[0-9]{10}", code)
            or not 1 <= int(code[8:10]) <= 24
            or not 1 <= int(code[10:12]) <= 12):
        raise ValueError("invalid_race_identity")
    digests = projection.get("source_sha256")
    required_digest_keys = (
        {"beforeinfo", "odds120"} if pair_only else
        {"racelist", "beforeinfo", "odds120"}
    )
    if (type(digests) is not dict or set(digests) != required_digest_keys
            or any(type(x) is not str or not HEX.fullmatch(x)
                   for x in digests.values())
            or type(projection.get("normalized_source_sha256")) is not str
            or not HEX.fullmatch(projection["normalized_source_sha256"])):
        raise ValueError("projection_missing_original_fingerprints")
    if pair_only and (
        type(projection.get("source_original_zip_sha256")) is not str
        or not HEX.fullmatch(projection["source_original_zip_sha256"])
        or projection.get("racelist_original_missing") is not True
        or projection.get("source_pair_only_no_new_forecast_receipt") is not True
        or projection.get("weather_observation_clock_unverified") is not True
    ):
        raise ValueError("partial_official_source_must_fail_closed_without_racelist")
    missing = projection.get("missing_research_features")
    if (type(missing) is not list
            or any(type(value) is not str for value in missing)
            or not MISSING.issubset(set(missing))):
        raise ValueError("missing_features_not_explicit")
    boats = projection.get("exhibition_features_by_boat")
    if type(boats) is not list or len(boats) != 6:
        raise ValueError("exact_six_exhibition_boats_required")
    digest = hashlib.sha256(json.dumps(
        boats, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")).hexdigest()
    if (type(projection["exhibition_features_sha256"]) is not str
            or not HEX.fullmatch(projection["exhibition_features_sha256"])
            or digest != projection["exhibition_features_sha256"]):
        raise ValueError("exhibition_projection_vector_digest_mismatch")
    by_boat = {}
    for row in boats:
        if (type(row) is not dict
                or set(row) != {
                    "boat", "registration_id", "exhibition_course_only",
                    "exhibition_time_s", "exhibition_st_s", "exhibition_tilt"
                } or type(row["boat"]) is not int
                or row["boat"] not in range(1, 7)
                or row["boat"] in by_boat
                or type(row["registration_id"]) is not str
                or not re.fullmatch(r"[0-9]{4,6}", row["registration_id"])
                or type(row["exhibition_course_only"]) is not int
                or row["exhibition_course_only"] not in range(1, 7)):
            raise ValueError("invalid_or_duplicate_exhibition_boat")
        for name, low, high in (
            ("exhibition_time_s", 0.0, 20.0),
            ("exhibition_st_s", -1.0, 2.0),
            ("exhibition_tilt", -5.0, 5.0),
        ):
            val = row[name]
            if (type(val) not in (int, float)
                    or not math.isfinite(val) or not low <= val <= high):
                raise ValueError("invalid_" + name)
        by_boat[row["boat"]] = row
    if (set(by_boat) != set(range(1, 7))
            or len({row["registration_id"] for row in by_boat.values()}) != 6
            or set(row["exhibition_course_only"] for row in by_boat.values())
            != set(range(1, 7))):
        raise ValueError("exhibition_roster_not_six_distinct")
    return [
        {"boat": i,
         "exhibition_time_s": by_boat[i]["exhibition_time_s"],
         "exhibition_st_s": by_boat[i]["exhibition_st_s"],
         # This is PRE-RACE EXHIBITION entry by boat, never final actual entry.
         "exhibition_course_only": by_boat[i]["exhibition_course_only"]}
        for i in range(1, 7)
    ]


def _config(plans, study_id):
    if type(study_id) is not str or not ID.fullmatch(study_id):
        raise ValueError("new_independent_exploratory_study_id_required")
    if type(plans) is not dict or not plans or set(plans) - SCENARIOS:
        raise ValueError("unrecognized_scenario_plan")
    for name, plan in plans.items():
        if (type(plan) is not dict or set(plan) !=
                {"weight", "head_log_shifts", "position_coefficients"}):
            raise ValueError("scenario_plan_contract_invalid")
        weight = plan["weight"]
        if (type(weight) not in (int, float)
                or not math.isfinite(weight) or not 0 <= weight <= 1):
            raise ValueError("invalid_scenario_weight")
        coeffs = plan["position_coefficients"]
        if type(coeffs) is not dict or not coeffs or set(coeffs) - FIELDS:
            raise ValueError("only_available_exhibition_features_allowed")
        for pos in coeffs.values():
            if (type(pos) is not dict or set(pos) != {"second", "third"}
                    or any(type(x) not in (int, float) or
                           not math.isfinite(x) or not -2 <= x <= 2
                           for x in pos.values())):
                raise ValueError("unvalidated_position_coefficient_shape")
    if not math.isclose(sum(plan["weight"] for plan in plans.values()),
                        1.0, abs_tol=1e-10):
        raise ValueError("scenario_weights_not_normalized")


def _conditional_result(response, prior, active):
    if (type(response) is not dict
            or response.get("status") !=
                "unregistered_hypothesis_numeric_sensitivity_only"
            or response.get("formal") is not False
            or response.get("calibrated_probabilities") is not False
            or response.get("verified_predeadline_official_inputs") is not False
            or response.get("verified_candidate_first_remote_receipt") is not False
            or response.get("confirmed_results_read") is not False
            or response.get("production_changed") is not False
            or response.get("promotion_allowed") is not False
            or response.get("model_improvement_proven") is not False
            or response.get("active_features") != sorted(active)):
        raise ValueError("conditional_lab_contract_or_provenance_invalid")
    values = _valid_board(response.get("ranked_board"))
    before = _valid_board(prior)
    for head in range(1, 7):
        a = math.fsum(p for t, p in before.items() if t[0] == head)
        b = math.fsum(p for t, p in values.items() if t[0] == head)
        if not math.isclose(a, b, rel_tol=0, abs_tol=1e-12):
            raise ValueError("conditional_lab_changed_head_probability")
    return sorted(values.items(), key=lambda item: (-item[1], item[0]))


def _compute_exhibition_scenario_boards(projection, six_national_rates, plans,
                                        conditional_lab_callback, *, study_id):
    """Validate once, compute each distinct scenario board once; no mode-specific weights here."""
    boats = _projected(projection)
    _config(plans, study_id)
    if not callable(conditional_lab_callback):
        raise ValueError("existing_1698_conditional_lab_callback_required")
    base = probabilities(six_national_rates)  # unchanged main baseline
    # Pass exhibition ST, time and course; course is a PRE-RACE proxy, not
    # independently observed final entry or a two-course wall statistic.
    # The pinned #1698 callback consumes a feature only for nonzero coefficients.
    evidence = {"boats": [{"boat": b["boat"],
                           "exhibition_st_s": b["exhibition_st_s"],
                           "exhibition_time_s": b["exhibition_time_s"],
                           "entry_course": b["exhibition_course_only"]}
                          for b in boats], "context": {}}
    boards = {}
    activated_by_scenario = {}
    for name in sorted(plans):
        plan = plans[name]
        first = hypothetical_head_board(
            base, plan["head_log_shifts"],
            study_id=study_id + "_HEAD_" + name.upper())
        if (first["formal"] is not False
                or first["promotion_allowed"] is not False):
            raise ValueError("untrusted_head_probability_step")
        coeffs = plan["position_coefficients"]
        active = {
            key for key, p in coeffs.items()
            if p["second"] != 0 or p["third"] != 0
        }
        activated_by_scenario[name] = sorted(active)
        conditioned = conditional_lab_callback(
            copy.deepcopy(first["ranked_board"]), copy.deepcopy(evidence),
            copy.deepcopy(coeffs),
            study_id + "_PAIR_" + name.upper())
        boards[name] = _conditional_result(
            conditioned, first["ranked_board"], active)
    return boards, activated_by_scenario


def run_exhibition_scenario_lab(projection, six_national_rates, plans,
                                conditional_lab_callback, *, study_id):
    """Compute one isolated complete four-mode scenario hypothesis.

    Pass #1698's experimental_conditional_board as callback only after
    separately reviewing that Draft. This module never imports its file.
    Rates and candidate source clocks are not independently authenticated.
    """
    boards, activated_by_scenario = _compute_exhibition_scenario_boards(
        projection, six_national_rates, plans, conditional_lab_callback,
        study_id=study_id)
    mixed = compose_scenario_research(
        boards, {name: plans[name]["weight"] for name in plans})
    return {
        "schema": "SCENARIO_ALL_MODES_EXHIBITION_LAB_V1",
        "race_code": projection["race_code"],
        "study_id": study_id,
        "referenced_projection_source_sha256": dict(projection["source_sha256"]),
        "projection_normalized_source_sha256": projection["normalized_source_sha256"],
        "mode_result": mixed,
        "feature_fields_passed_to_conditional_lab": sorted(FIELDS),
        "feature_fields_actually_activated_by_scenario": activated_by_scenario,
        "projection_features_present_but_not_scored": [
            "exhibition_tilt",
            *([] if any("entry_course" in fields for fields in
                       activated_by_scenario.values()) else ["exhibition_course_only"]),
        ],
        "entry_course_input_semantics": "synthetic_projection_exhibition_only_not_final_actual_entry",
        "exhibition_course_proxy_used_in_hypothesis": any(
            "entry_course" in fields for fields in activated_by_scenario.values()),
        "two_course_wall_feature_or_final_entry_used": False,
        "exhibition_time_s_status": "available_for_explicit_hypothesis_only",
        "feature_values_from_projection_only": True,
        "national_rates_predeadline_original_independently_verified": False,
        "conditional_callback_module_identity_independently_verified": False,
        "conditional_callback_result_blind_independently_verified": False,
        "actual_official_exhibition_consumption_independently_replayed": False,
        "actual_entry_wind_tide_motor_or_wall_used": False,
        "scenario_weights_calibrated": False,
        "model_probabilities_calibrated": False,
        "formal": False,
        "forecast_usable": False,
        "production_changed": False,
        "promotion_allowed": False,
    }

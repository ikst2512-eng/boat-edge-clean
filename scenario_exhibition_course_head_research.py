"""Separate UNREGISTERED exhibition-course holder study for Issue #1708.

The frozen #1710 protocol defines head shifts in BOAT order. This experiment
tests a DIFFERENT hypothesis: interpret each shift as a COURSE hypothesis
and assign it to the boat observed in that *exhibition* course. It never
edits frozen coefficients, rewrites historical predictions, or establishes
actual final race entry. Caller-supplied #1692 K summary is checked for
same-race athlete/venue/time identity but NOT original-K authenticated.
"""
import base64
import binascii
from datetime import date
import hashlib
import json
import math
from pathlib import Path
import re

from research_model import probabilities
from scenario_first_head_research import hypothetical_head_board
from scenario_exhibition_all_mode_runner import _projected, _conditional_result
from scenario_future_three_original_gateway import validate_audited_source_pairing
from scenario_official_racelist_rates import extract_six_official_racelist_rates
from scenario_four_mode_bridge import BUDGETS, compose_scenario_research, _valid_board
from scenario_future_local_candidate_handoff import _git_blob_sha1
from scenario_escape_prior_first_head_sensitivity import (
    FROZEN_1710_PROTOCOL_BLOB, HISTORY_FIELDS, HISTORY_SCHEMA, K92_ZIP_SHA256,
    _finite, _strict_count,
)

STUDY = "EXPLORATORY_ONLY_EXHIBITION_COURSE_HOLDER_HEAD_V1"
SCHEMA = "EXHIBITION_COURSE_HOLDER_HEAD_RESEARCH_V1"
WORLDS = ("escape_wall", "two_sashi", "third_attack", "outer_benefit")
PROTOCOL_PATH = "research/four_mode_triple_source_forward_protocol_20261110.json"


def _frozen_protocol():
    original = (Path(__file__).resolve().parent / PROTOCOL_PATH).read_bytes()
    if _git_blob_sha1(original) != FROZEN_1710_PROTOCOL_BLOB:
        raise ValueError("course_holder_frozen_1710_protocol_changed")
    protocol = json.loads(original)
    plans = protocol["scenario_hypotheses"]
    weights = protocol["mode_weights"]
    if (set(plans) != set(WORLDS)
            or set(weights) != set(BUDGETS)
            or any(set(row) != set(WORLDS) for row in weights.values())
            or any(not math.isclose(sum(row.values()), 1.0, abs_tol=1e-12)
                   for row in weights.values())):
        raise ValueError("course_holder_frozen_protocol_shape_invalid")
    return plans, weights


def _linked_sources(audit, source_bundle, candidate, projection):
    lineage = validate_audited_source_pairing(
        audit, source_bundle, candidate, projection)
    # This checks only the input consistency of the independently written
    # auditor, not that the claimed HTTP observations are authentic.
    _projected(projection)
    rows = projection["exhibition_features_by_boat"]
    by_course = {r["exhibition_course_only"]: r for r in rows}
    if (len(by_course) != 6
            or set(by_course) != set(range(1, 7))
            or [r["boat"] for r in rows] != list(range(1, 7))):
        raise ValueError("course_holder_six_course_permutation_invalid")
    try:
        raw = base64.b64decode(
            source_bundle["originals"]["racelist"]["raw_base64"],
            validate=True)
    except (KeyError, TypeError, ValueError, binascii.Error) as exc:
        raise ValueError("course_holder_racelist_original_unreadable") from exc
    if hashlib.sha256(raw).hexdigest() != lineage["source_sha256_claims"]["racelist"]:
        raise ValueError("course_holder_original_sha_mismatch")
    racers = extract_six_official_racelist_rates(raw)
    registration_ids = [x["registration_id"] for x in racers["boats"]]
    if registration_ids != [x["registration_id"] for x in rows]:
        raise ValueError("course_holder_original_registration_mismatch")
    return lineage, rows, by_course, racers


def _joined_history(history, lineage, rows, by_course):
    """Structural identity checks only. The K statistics are NOT raw replayed."""
    code = lineage["race_code"]
    if (type(history) is not dict or set(history) != HISTORY_FIELDS
            or history.get("schema") != HISTORY_SCHEMA
            or history.get("race_code") != code
            or history.get("venue_code") != code[8:10]
            or history.get("official_K_replay_zip_sha256_claim") != K92_ZIP_SHA256
            or any(history.get(key) is not False for key in (
                "training_used_outcomes_after_target",
                "official_source_receipt_independently_authenticated",
                "exhibition_is_final_race_entry",
                "outcomes_from_target_race_read"))):
        raise ValueError("course_holder_history_identity_or_source_claim_invalid")
    try:
        last = date.fromisoformat(history["historic_training_end_date_jst"])
        race_day = date.fromisoformat(
            f"{code[:4]}-{code[4:6]}-{code[6:8]}")
    except (TypeError, ValueError) as exc:
        raise ValueError("course_holder_history_date_invalid") from exc
    if not date(2026, 8, 1) <= last <= date(2026, 9, 30) or last >= race_day:
        raise ValueError("course_holder_history_lookahead_or_out_of_window")
    roster = history["exhibition_entry_roster_by_boat"]
    expected = [{
        "boat": row["boat"], "registration": row["registration_id"],
        "exhibition_course": row["exhibition_course_only"]
    } for row in rows]
    if roster != expected:
        raise ValueError("course_holder_history_six_roster_mismatch")
    holder = by_course[1]
    if history["C1_athlete_registration"] != holder["registration_id"]:
        raise ValueError("course_holder_history_wrong_C1_athlete")
    n = _strict_count(history["national_training_race_count"], "national_denominator")
    k = _strict_count(history["national_training_C1_escape_count"], "national_numerator")
    vn = _strict_count(history["venue_training_race_count"], "venue_denominator")
    vk = _strict_count(history["venue_training_C1_escape_count"], "venue_numerator")
    athlete_n = _strict_count(history["C1_athlete_training_race_count"], "athlete_denominator")
    residual = _finite(history["C1_athlete_venue_centered_residual_sum"],
                       "athlete_residual", low=-athlete_n, high=athlete_n)
    if n < 100 or k > n or vn < 10 or vk > vn or vn > n or athlete_n > n:
        raise ValueError("course_holder_history_denominator_invalid")
    # Not allowed to pass a caller-claimed residual into forecast weights.
    return {
        "exhibition_course1_boat": holder["boat"],
        "exhibition_course1_athlete": holder["registration_id"],
        "history_training_end_jst": last.isoformat(),
        "history_claimed_national_denominator": n,
        "history_claimed_venue_denominator": vn,
        "history_claimed_athlete_denominator": athlete_n,
        "history_claimed_residual": residual,
        "history_used_in_numeric_head_scores": False,
        "official_K_original_replayed_here": False,
        "independent_historical_receipt_verified": False,
    }


def prepare_course_holder_head_study(audit, source_bundle, candidate,
                                     projection, history):
    """Return source-matched RESEARCH head boards for the actual exhibition holder.

    Full 120-ticket boards preserve P(second,third | first) from the frozen
    BASELINE here; the optional #1698 conditional lab is executed separately.
    """
    lineage, rows, by_course, racers = _linked_sources(
        audit, source_bundle, candidate, projection)
    joined = _joined_history(history, lineage, rows, by_course)
    plans, weights = _frozen_protocol()
    baseline = probabilities(racers["national_rates"])
    before = _valid_board(baseline)
    mapped_vectors, heads = {}, {}
    for world in WORLDS:
        original = plans[world]["head_log_shifts"]
        if (type(original) is not list or len(original) != 6
                or any(type(v) not in (int, float) or
                       not math.isfinite(v) or not -6 <= v <= 6
                       for v in original)):
            raise ValueError("course_holder_invalid_frozen_head_coefficients")
        # Interpret the same frozen six numbers as hypothetical COURSE
        # coefficients, not as fixed BOAT coefficients; this is new science.
        mapped = [original[row["exhibition_course_only"] - 1] for row in rows]
        mapped_vectors[world] = mapped
        heads[world] = hypothetical_head_board(
            baseline, mapped, study_id=STUDY+"_HEAD_"+world.upper())
    return {
        "schema": SCHEMA, "study_id": STUDY,
        "race_code": lineage["race_code"],
        "source_lineage": lineage,
        "history_source_join": joined,
        "frozen_protocol_blob_sha1": FROZEN_1710_PROTOCOL_BLOB,
        "original_frozen_hypothesis_unmodified": True,
        "exhibition_course_to_boat": {
            str(course): by_course[course]["boat"] for course in range(1, 7)},
        "frozen_head_coefficients_mapped_by_exhibition_course": mapped_vectors,
        "head_models": heads,
        "scenario_weights": weights,
        "national_rates_from_same_racelist_original": racers["national_rates"],
        "source_projection_sha256": projection["exhibition_features_sha256"],
        "history_counts_applied_to_head_or_world_weights": False,
        "exhibition_not_actual_final_race_entry": True,
        "original_K_history_replayed_and_verified": False,
        "independent_first_remote_forecast_receipt_verified": False,
        "pre_registered_new_candidate": False,
        "new_pilot_count": 0,
        "new_confirmation_count": 0,
        "formal": False, "calibrated": False,
        "accuracy_improvement_proven": False,
        "production_changed": False, "promotion_allowed": False,
        "results_read": False,
    }


def run_course_holder_four_mode_sensitivity(study, projection,
                                             conditional_callback):
    """Reuse pinned #1698 conditional callback for all 4 hypothetical worlds.

    This cannot register a candidate, score races or modify live output.
    """
    if (type(study) is not dict or study.get("schema") != SCHEMA
            or study.get("study_id") != STUDY
            or study.get("formal") is not False
            or study.get("production_changed") is not False
            or study.get("promotion_allowed") is not False
            or study.get("results_read") is not False
            or study.get("pre_registered_new_candidate") is not False
            or study.get("frozen_protocol_blob_sha1") != FROZEN_1710_PROTOCOL_BLOB
            or study.get("source_projection_sha256") != projection.get(
                "exhibition_features_sha256")
            or study.get("race_code") != projection.get("race_code")
            or not callable(conditional_callback)):
        raise ValueError("course_holder_sensitivity_untrusted_preparation")
    _projected(projection)
    plans, weights = _frozen_protocol()
    if weights != study["scenario_weights"]:
        raise ValueError("course_holder_modified_mode_weights")
    rows = projection["exhibition_features_by_boat"]
    if {str(r["exhibition_course_only"]): r["boat"] for r in rows} != (
            study["exhibition_course_to_boat"]):
        raise ValueError("course_holder_changed_entry_after_preparation")
    # The handoff is caller-owned research data. Do not trust a copied or
    # edited first-place board even when its declared vector is unchanged.
    recalculated_baseline = probabilities(
        study["national_rates_from_same_racelist_original"])
    for world in WORLDS:
        vector = [plans[world]["head_log_shifts"][
            r["exhibition_course_only"] - 1] for r in rows]
        if vector != study["frozen_head_coefficients_mapped_by_exhibition_course"][world]:
            raise ValueError("course_holder_changed_head_vector")
        expected = hypothetical_head_board(
            recalculated_baseline, vector,
            study_id=STUDY+"_HEAD_"+world.upper())
        prior = study["head_models"][world]
        if (prior["ranked_board"] != expected["ranked_board"]
                or prior["hypothesis_first_mass"] != expected["hypothesis_first_mass"]
                or prior["head_hypothesis_sha256"] != expected["head_hypothesis_sha256"]):
            raise ValueError("course_holder_tampered_first_head_board")
    evidence = {"boats": [{
        "boat": r["boat"], "entry_course": r["exhibition_course_only"],
        "exhibition_st_s": r["exhibition_st_s"],
        "exhibition_time_s": r["exhibition_time_s"]
    } for r in rows], "context": {}}
    boards = {}
    for world in WORLDS:
        prior = study["head_models"][world]["ranked_board"]
        coeffs = plans[world]["position_coefficients"]
        active = {k for k, v in coeffs.items()
                  if v["second"] != 0 or v["third"] != 0}
        out = conditional_callback(
            prior, evidence, coeffs, STUDY+"_PAIR_"+world.upper())
        boards[world] = _conditional_result(out, prior, active)
    modes = {}
    for mode, budgets in BUDGETS.items():
        aggregate = compose_scenario_research(boards, weights[mode])
        selection = aggregate["existing_four_mode_selector_on_mixture"][mode]
        if len(selection["tickets"]) != budgets:
            raise ValueError("course_holder_mode_budget_changed")
        modes[mode] = {
            "tickets": selection["tickets"],
            "top1": selection["tickets"][0]["combo"],
            "board_sha256": aggregate["mixed_120_board_sha256"],
        }
    return {
        "schema": "EXHIBITION_COURSE_HOLDER_FOUR_MODE_SENSITIVITY_V1",
        "study_id": STUDY, "race_code": study["race_code"],
        "modes": modes,
        "head_holder_by_exhibition_course": dict(
            study["exhibition_course_to_boat"]),
        "frozen_1698_callback_supplied_by_caller_not_authenticated_here": True,
        "forecast_usable": False, "formal": False, "calibrated": False,
        "independent_first_remote_receipt_verified": False,
        "registered_pilot_count": 0, "registered_confirmation_count": 0,
        "results_read": False, "production_changed": False,
        "accuracy_improvement_proven": False, "promotion_allowed": False,
    }

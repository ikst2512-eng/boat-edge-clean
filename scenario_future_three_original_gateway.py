"""Future-only research: cross-check #1713 triple auditor against #1710 math.

CALLER must use the existing independently reviewed raw semantic replay from
#1693, existing triple auditor from #1713, and pinned #1698 conditional math.
This module NEVER captures official sources, reimplements their parsers,
publishes a forecast, reads outcomes, or declares the source certified.

Even a self-consistent three-source *report* does not independently prove
the HTTP origin, source-to-model execution, first Git remote receipt, or
prospective accuracy. Output is a RESEARCH CONTRAST ONLY.
"""
import base64
import binascii
import hashlib
import json
import math
import re
from datetime import datetime, timedelta

from scenario_official_exhibition_projection import project_exhibition_research
from scenario_official_racelist_rates import extract_six_official_racelist_rates
from scenario_mode_specific_exhibition_end_to_end import (
    evaluate_exhibition_mode_lenses, MODES, BUDGETS,
)

STUDY = "EXPLORATORY_ONLY_FUTURE_TRIPLE_SCENARIO_RESEARCH"

def _canonical_sha256(value):
    """Stable content identity only; NOT a trusted timestamp or remote receipt."""
    return hashlib.sha256(json.dumps(
        value, sort_keys=True, ensure_ascii=False,
        separators=(",", ":"), allow_nan=False).encode("utf-8")).hexdigest()

MIN_DAY = "20261111"  # Prior Nov 9/10 retrospective replays are NEVER future candidates.
CHECKS = frozenset({
    "racecard_original_hash_verified", "racecard_six_registrations",
    "racer_registration_ids_match", "racecard_received_by_t12",
    "beforeinfo_received_by_t12", "beforeinfo_six_unique_boats",
    "exhibition_six_courses", "exhibition_times_six", "tilt_six",
    "start_exhibition_six", "odds_120", "odds_received_by_t12",
})
REPORT_KEYS = frozenset({
    "race_code", "official_deadline_jst", "cutoff_jst",
    "racelist_received_jst", "beforeinfo_received_jst",
    "odds_received_jst", "latest_original_received_jst",
    "t12_receipt_margin_seconds", "registrations_by_lane",
    "exhibition_course_to_boat", "three_originals_hash_verified",
    "component_checks", "missing_components",
    "all_research_components_observed_by_t12",
    "final_race_entry_verified", "full_t12_source_certified",
    "t12_eligible", "forecast_usable",
})
BOAT_KEYS = {str(i) for i in range(1, 7)}
RESULT_KEYS = {
    "finish_order", "winning_ticket", "confirmed_result", "winner",
    "confirmed_at_jst", "payout", "post_race_weather", "result",
}


def _jst(value):
    if type(value) is not str:
        raise ValueError("research_source_clock_missing")
    try:
        when = datetime.fromisoformat(value)
    except (ValueError, OverflowError) as exc:
        raise ValueError("research_source_clock_invalid") from exc
    if when.utcoffset() != timedelta(hours=9):
        raise ValueError("research_source_clock_not_JST")
    return when


def validate_audited_source_pairing(audit, bundle, candidate, projection):
    """Validate independently built triple report + raw-replayed projection.

    This verifies *consistency* with caller inputs, not the caller's remote
    credentials, official origin or first-remote Git commit.
    """
    if (type(audit) is not dict or set(audit) != REPORT_KEYS
            or type(bundle) is not dict or type(candidate) is not dict
            or type(projection) is not dict
            or set(audit) & RESULT_KEYS
            or set(bundle) & RESULT_KEYS
            or set(candidate) & RESULT_KEYS):
        raise ValueError("three_original_audit_contract_or_outcome_invalid")
    checks = audit["component_checks"]
    if (type(checks) is not dict or set(checks) != CHECKS
            or any(v is not True for v in checks.values())
            or audit["three_originals_hash_verified"] is not True
            or audit["all_research_components_observed_by_t12"] is not True
            or audit["missing_components"] != []
            or any(audit[k] is not False for k in (
                "final_race_entry_verified", "full_t12_source_certified",
                "t12_eligible", "forecast_usable"))):
        raise ValueError("three_original_source_incomplete_or_forged_formal")
    code = audit["race_code"]
    if (type(code) is not str or not re.fullmatch(r"20[0-9]{10}", code)
            or code[:8] < MIN_DAY
            or code != bundle.get("race_code")
            or code != candidate.get("race_code")
            or code != projection.get("race_code")):
        raise ValueError("not_future_independent_same_race")
    deadline, cutoff, generated = (
        _jst(audit["official_deadline_jst"]),
        _jst(audit["cutoff_jst"]),
        _jst(candidate.get("generated_at_jst")),
    )
    if (deadline.strftime("%Y%m%d") != code[:8]
            or cutoff != deadline - timedelta(minutes=12)
            or bundle.get("deadline_jst") != deadline.isoformat()
            or candidate.get("deadline_jst") != deadline.isoformat()
            or generated.date() != deadline.date()
            or not generated < cutoff):
        raise ValueError("wrong_deadline_or_late_candidate")
    receipt_fields = {
        "racelist": "racelist_received_jst",
        "beforeinfo": "beforeinfo_received_jst",
        "odds120": "odds_received_jst",
    }
    originals = bundle.get("originals")
    if (type(originals) is not dict or set(originals) != set(receipt_fields)):
        raise ValueError("source_bundle_missing_three_originals")
    received = []
    for kind, stamp_field in receipt_fields.items():
        claim = _jst(audit[stamp_field])
        source = _jst(originals[kind].get("received_at_jst"))
        if (claim != source or claim.date() != deadline.date()
                or not source < generated or not source < cutoff):
            raise ValueError("source_receipt_not_aligned_with_projection_generation")
        received.append(source)
    latest = max(received)
    margin = audit["t12_receipt_margin_seconds"]
    if (latest != _jst(audit["latest_original_received_jst"])
            or type(margin) not in (float, int)
            or not math.isfinite(margin)
            or margin <= 0
            or not math.isclose(margin, (cutoff - latest).total_seconds(),
                                rel_tol=0, abs_tol=1e-6)):
        raise ValueError("three_original_latest_clock_or_margin_mismatch")

    ids, courses = audit["registrations_by_lane"], audit["exhibition_course_to_boat"]
    if (type(ids) is not dict or set(ids) != BOAT_KEYS
            or type(courses) is not dict or set(courses) != BOAT_KEYS
            or set(courses.values()) != BOAT_KEYS
            or any(type(x) is not str for x in list(ids.values()) + list(courses.values()))):
        raise ValueError("three_original_six_identity_or_exhibition_entry_incomplete")
    p_boats = projection.get("exhibition_features_by_boat")
    if (type(p_boats) is not list or len(p_boats) != 6
            or any(type(row) is not dict for row in p_boats)):
        raise ValueError("projection_six_athletes_missing")
    for row in p_boats:
        boat = str(row.get("boat"))
        course = str(row.get("exhibition_course_only"))
        if (boat not in BOAT_KEYS or course not in BOAT_KEYS
                or row.get("registration_id") != ids[boat]
                or courses[course] != boat):
            raise ValueError("three_original_projection_identity_or_entry_mismatch")
    digests = projection.get("source_sha256")
    expected = bundle.get("normalized_source_claim", {}).get("source_sha256")
    if (type(digests) is not dict or set(digests) != set(receipt_fields)
            or digests != expected
            or any(type(v) is not str or not re.fullmatch(r"[0-9a-f]{64}", v)
                   for v in digests.values())):
        raise ValueError("projection_source_digest_not_triple")
    return {
        "race_code": code,
        "cutoff_jst": cutoff.isoformat(),
        "latest_three_original_receipt_claim_jst": latest.isoformat(),
        "source_sha256_claims": dict(digests),
        "projection_sha256": projection["normalized_source_sha256"],
        "auditor_component_count": len(CHECKS),
        "registrations_matched_six": True,
        "exhibition_entry_permutation_matched": True,
        "raw_HTTP_origin_independently_authenticated": False,
        "separate_auditor_code_identity_independently_pinned": False,
        "initial_remote_candidate_receipt_verified": False,
        "formal": False,
    }


def run_future_triple_experiment(audit, source_bundle, candidate,
                                 raw_replay_callback, rates,
                                 scenarios, mode_weights, conditional_callback):
    # The existing #1693 raw replayer is required before the first 4-mode call.
    # The output must remain unregistered as a prospective accuracy sample.
    if (type(rates) is not list or len(rates) != 6
            or any(type(x) not in (int, float) or
                   not math.isfinite(x) or not 0 < x < 20 for x in rates)):
        raise ValueError("six_predeadline_national_rates_required")
    projection = project_exhibition_research(
        source_bundle, candidate, raw_replay_callback)
    source_check = validate_audited_source_pairing(
        audit, source_bundle, candidate, projection)
    # The six win rates MUST be parsed from the same archived racelist HTML,
    # not silently accepted from an old V2 CSV, caller guess or a neutral
    # fallback. Projection has already checked this raw source SHA via the
    # injected #1693 semantic replayer and all three source/cutoff claims.
    original = source_bundle["originals"]["racelist"]
    try:
        html = base64.b64decode(original["raw_base64"], validate=True)
    except (ValueError, binascii.Error, KeyError, TypeError) as exc:
        raise ValueError("unreadable_official_racelist_original") from exc
    if hashlib.sha256(html).hexdigest() != source_check["source_sha256_claims"]["racelist"]:
        raise ValueError("national_rate_source_not_same_official_original")
    rate_audit = extract_six_official_racelist_rates(html)
    if (rate_audit["national_rates"] != rates
            or [row["registration_id"] for row in rate_audit["boats"]] !=
            [row["registration_id"] for row in projection["exhibition_features_by_boat"]]):
        raise ValueError("six_national_win_rates_or_registration_not_from_official_racelist")
    math_out = evaluate_exhibition_mode_lenses(
        projection, rate_audit["national_rates"], scenarios, mode_weights,
        conditional_callback, study_id=STUDY)
    if (math_out["race_code"] != source_check["race_code"]
            or math_out["formal"] is not False
            or math_out["promotion_allowed"] is not False
            or math_out["forecast_usable"] is not False
            or math_out["first_candidate_remote_receipt_verified"] is not False
            or math_out["outcomes_read_by_adapter"] is not False
            or math_out["new_formal_pilot_races"] != 0
            or math_out["new_formal_confirmation_races"] != 0):
        raise ValueError("unregistered_candidate_or_forged_probability_certificate")
    rows = {}
    for mode in MODES:
        tickets = math_out["four_mode_research_tickets"][mode]["tickets"]
        if len(tickets) != BUDGETS[mode]:
            raise ValueError("mode_budget_drift")
        rows[mode] = {
            "tickets": tickets,
            "top1": tickets[0]["combo"],
            "research_board_sha256": math_out["four_mode_research_tickets"][mode][
                "distinct_120_mixture_digest"],
        }
    # Bind the actual six source-derived rates, original HTTP hashes, ST
    # projection, uncalibrated hypotheses, generation claim, ranked tickets,
    # and complete-board checksums. Replaying from the SAME inputs must yield
    # identical content IDs; changing any of them must change the ID. This
    # is not independent first remote Git acceptance or preregistration.
    input_digest = _canonical_sha256({
        "race_code": source_check["race_code"],
        "source_original_sha256": source_check["source_sha256_claims"],
        "source_normalized_sha256": projection["normalized_source_sha256"],
        "source_exhibition_vector_sha256": projection["exhibition_features_sha256"],
        "candidate_generation_self_reported_jst": candidate["generated_at_jst"],
        "national_win_rates": rate_audit["national_rates"],
        "scenarios": scenarios,
        "mode_weights": mode_weights,
    })
    ranked_digest = _canonical_sha256({
        "input_digest_sha256": input_digest,
        "modes": rows,
        "individual_scenario_board_sha256": math_out["scenario_board_sha256"],
    })
    return {
        "schema": "FUTURE_THREE_ORIGINAL_FOUR_MODE_RESEARCH_GATEWAY_V1",
        "study_id": STUDY,
        "race_code": source_check["race_code"],
        "source_lineage_preflight": source_check,
        "model_input_content_sha256_research_only": input_digest,
        "four_mode_ranked_output_content_sha256_research_only": ranked_digest,
        "source_to_candidate_remote_receipt_proven": False,
        "six_national_win_rates_from_same_original_html": rate_audit["national_rates"],
        "six_local_win_rates_from_same_original_html": rate_audit["local_rates"],
        "six_average_ST_from_same_original_html_not_scored": rate_audit["average_st"],
        "national_win_rate_from_official_original_structurally_verified": True,
        "official_racelist_HTTP_authenticity_independently_verified": False,
        "hypothesis_signature_sha256": hashlib.sha256(json.dumps(
            {"scenarios":scenarios, "weights":mode_weights},
            sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest(),
        "research_mode_tickets": rows,
        "official_triple_source_auditor_reported_complete": True,
        "candidate_source_consumption_structurally_replayed": True,
        "official_data_real_or_independently_authenticated": False,
        "hypotheses_frozen_in_prospective_registration": False,
        "candidate_remote_first_receipt_verified": False,
        "eligible_for_existing_1693_600_races": False,
        "eligible_for_new_300_plus_300_races": False,
        "formal": False,
        "forecast_usable": False,
        "calibrated_probabilities": False,
        "accuracy_improvement_proven": False,
        "production_changed": False,
        "promotion_allowed": False,
        "results_read": False,
    }

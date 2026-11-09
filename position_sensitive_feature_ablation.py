"""Unregistered #1698 research: same-race four-mode conditional feature ablation.

The frozen six-rate selector, original V2 forecasts and preregistered 300+300
study are never written. No result, payout, live/official source or
performance score is read. Do NOT pass these exploratory outputs to UI.
"""
import hashlib
import json

from clean_four_modes import rank_modes
from position_sensitive_conditional_decomposition import compare_conditional_decomposition
from research_model import probabilities
from four_mode_position_sensitive_shadow import shadow_probabilities
from position_sensitive_conditioned_lab import (
    experimental_conditional_board, inspect_feature_readiness, _params,
)

TOPS = (1, 3, 5, 10)
MODES = {"narrow": 5, "hit": 10, "balance": 16, "hole": 22}
LABEL = "UNREGISTERED_SECOND_THIRD_FEATURE_ABLATION_V1"


def _digest(rates, evidence, coefficients, study_id):
    # Fingerprint is LOCAL supplied bytes in a stable serialization; a digest
    # alone is NOT source authenticity or proof of a pre-T12 first receipt.
    payload = json.dumps({
        "rates": rates, "evidence": evidence,
        "coefficients": coefficients, "study_id": study_id,
    }, ensure_ascii=False, sort_keys=True, allow_nan=False, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _modes(rows):
    result = rank_modes(rows)
    for mode, budget in MODES.items():
        if len(result[mode]["tickets"]) != budget:
            raise ValueError("frozen_mode_ticket_budget_drift")
    return {mode: [x["combo"] for x in result[mode]["tickets"]] for mode in MODES}


def _mode_compare(before, after):
    report = {}
    for mode, budget in MODES.items():
        a, b = before[mode], after[mode]
        if len(a) != budget or len(b) != budget or len(set(a)) != budget or len(set(b)) != budget:
            raise ValueError("mode_budget_or_duplicate_invalid")
        measures = {}
        for k in TOPS:
            if k > budget:
                measures[str(k)] = {
                    "applicable": False,
                    "reason": "mode_budget_below_requested_topk",
                }
                continue
            old, new = a[:k], b[:k]
            retained = len(set(old) & set(new))
            measures[str(k)] = {
                "applicable": True,
                "ordered_rank_changed": old != new,
                "membership_changed": retained != k,
                "retained_tickets": retained,
                "replaced_tickets": k - retained,
                "no_accuracy_inference": True,
            }
        report[mode] = {
            "original_top1": a[0],
            "candidate_top1": b[0],
            "top1_changed": a[0] != b[0],
            "top1_first_boat_changed": a[0][0] != b[0][0],
            "topk": measures,
        }
    return report


def audit_feature_ablation(national_win_rates, evidence, coefficients, study_id):
    """Compare same supplied race V2 -> frozen position selector -> feature lab.

    Caller supplied features are UNTRUSTED; report explicitly cannot show
    real-race correctness. No automatic parameter search or odds weighting.
    """
    # Reject hostile/outcome-bearing structures and invalid rates before
    # deriving any side-by-side output.
    original = _modes(probabilities(national_win_rates))
    frozen_rows = shadow_probabilities(national_win_rates)
    frozen = _modes(frozen_rows)
    params = _params(coefficients, study_id)
    candidate = experimental_conditional_board(
        frozen_rows, evidence, coefficients, study_id)
    enhanced = _modes(candidate["ranked_board"])
    active = candidate["active_features"]
    readiness = inspect_feature_readiness(evidence)
    if not set(active).issubset(readiness["structurally_present_features"]):
        raise ValueError("feature_readiness_mismatch")
    removal = {}
    for field in active:
        remainder = {k: v for k, v in params.items() if k != field}
        if not remainder:
            remainder = {field: {"second": 0.0, "third": 0.0}}
        without = experimental_conditional_board(
            frozen_rows, evidence, remainder, study_id)
        removal[field] = {
            "without_feature_vs_with_all": _mode_compare(
                _modes(without["ranked_board"]), enhanced),
            "interpretation": (
                "mechanical_leave_one_out_sensitivity_not_causal_effect_"
                "or_validated_accuracy"),
        }
    return {
        "schema": LABEL,
        "status": "synthetic_or_untrusted_input_only_unregistered_ablation",
        "study_id": study_id,
        "input_fingerprint_sha256_self_supplied": _digest(
            national_win_rates, evidence, coefficients, study_id),
        "available_features_structural_only": readiness["structurally_present_features"],
        "missing_or_invalid_features": readiness["missing_or_invalid_features"],
        "used_features_with_nonzero_coefficients": active,
        "unused_features_are_not_applied": True,
        "original_v2_vs_frozen_six_rate": _mode_compare(original, frozen),
        "frozen_six_rate_vs_exploratory_features": _mode_compare(frozen, enhanced),
        "original_v2_vs_exploratory_features": _mode_compare(original, enhanced),
        "leave_one_feature_out": removal,
        "frozen_to_experimental_position_decomposition": compare_conditional_decomposition(
            frozen_rows, candidate["ranked_board"]),
        "frozen_top1_by_mode": {m: frozen[m][0] for m in MODES},
        "experimental_top1_by_mode": {m: enhanced[m][0] for m in MODES},
        "ticket_budgets": MODES.copy(),
        "same_race_original_and_candidate": True,
        "official_source_authenticated": False,
        "official_six_and_odds120_before_t12_verified": False,
        "candidate_first_remote_receipt_verified": False,
        "confirmed_outcomes_read": False,
        "topk_hit_rate_measured": False,
        "roi_measured": False,
        "calibration_measured": False,
        "formal": False,
        "model_improvement_proven": False,
        "promotion_allowed": False,
        "production_changed": False,
        "note": (
            "All TopK changes mean ticket membership/rank turnover, NOT hits, "
            "ROI, or reliability. The fixed #1698 300+300 selector and "
            "original archives remain unchanged. New coefficients need their "
            "own preregistered future evaluation and official source chain."
        ),
    }

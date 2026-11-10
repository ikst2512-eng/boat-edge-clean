"""Research-only: six-boat exhibition -> four separate scenario-weighted modes.

This joins (1) #1710's already tested official-exhibition *structural*
projection, (2) existing #1698 conditional 2nd/3rd callback, (3) existing
#1710 head hypotheses and scenario mixer, and (4) a predeclared explicit
weight map for EACH mode. The scenario boards are identical across modes;
only their declared scenario weights differ. That makes it impossible to
smuggle per-mode overrides or forced ticket exclusion into this adapter.

Important: neither the projection nor the caller's weights are certified as
official, calibrated or predictive. This is never a site/live selector.
"""
import copy
import re

from scenario_exhibition_all_mode_runner import run_exhibition_scenario_lab
from scenario_mode_specific_lens_research import MODES, BUDGETS

SCHEMA = "SCENARIO_MODE_SPECIFIC_EXHIBITION_END_TO_END_RESEARCH_V1"
STUDY = re.compile(r"EXPLORATORY_ONLY_[A-Z0-9_]{4,46}\Z")


def evaluate_exhibition_mode_lenses(projection, national_rates, scenario_hypotheses,
                                   mode_weights, conditional_callback, *, study_id):
    """All four lenses compute real mathematical rankings, not proven forecasts.

    Every scenario's head effects and 2nd/3rd feature coefficients are
    identical across modes. Per-mode evidence hypotheses may only alter the
    *relative weights* of those same scenario distributions. Never decrease
    a ticket merely because it was selected in another mode.
    """
    if (type(study_id) is not str or STUDY.fullmatch(study_id) is None
            or type(scenario_hypotheses) is not dict
            or not scenario_hypotheses or type(mode_weights) is not dict
            or set(mode_weights) != set(MODES)):
        raise ValueError("unregistered_study_or_incomplete_mode_hypotheses")
    scenarios = set(scenario_hypotheses)
    for key, hypothesis in scenario_hypotheses.items():
        if (type(hypothesis) is not dict
                or set(hypothesis) != {"head_log_shifts", "position_coefficients"}):
            raise ValueError("scenario_hypothesis_wrong_contract:" + str(key))
    for mode, weights in mode_weights.items():
        if type(weights) is not dict or set(weights) != scenarios:
            raise ValueError("all_mode_scenario_weights_must_cover_same_worlds:" + mode)
    if not callable(conditional_callback):
        raise ValueError("actual_existing_1698_callback_required")

    results = {}
    scenario_source_digests = None
    source_digest = None
    feature_digest = None
    for mode in MODES:
        plans = {
            key: {**copy.deepcopy(scenario_hypotheses[key]),
                  "weight": mode_weights[mode][key]}
            for key in scenario_hypotheses
        }
        out = run_exhibition_scenario_lab(
            copy.deepcopy(projection), copy.deepcopy(national_rates),
            plans, conditional_callback, study_id=study_id)
        mixed = out.get("mode_result")
        if (type(mixed) is not dict
                or out.get("formal") is not False
                or out.get("promotion_allowed") is not False
                or out.get("forecast_usable") is not False
                or out.get("production_changed") is not False
                or out.get("actual_official_exhibition_consumption_independently_replayed") is not False
                or out.get("national_rates_predeadline_original_independently_verified") is not False
                or out.get("conditional_callback_module_identity_independently_verified") is not False
                or out.get("conditional_callback_result_blind_independently_verified") is not False
                or out.get("model_probabilities_calibrated") is not False
                or mixed.get("formal") is not False
                or mixed.get("promotion_allowed") is not False
                or mixed.get("forecast_usable") is not False):
            raise ValueError("unexpected_upstream_verified_or_promoted_claim")
        if out.get("race_code") != projection.get("race_code"):
            raise ValueError("race_identity_changed_between_lenses")
        digests = mixed.get("scenario_board_sha256")
        if (type(digests) is not dict or set(digests) != scenarios
                or (scenario_source_digests is not None and
                    digests != scenario_source_digests)):
            raise ValueError("scenario_board_changed_across_modes")
        if scenario_source_digests is None:
            scenario_source_digests = dict(digests)
        if (source_digest is not None and
                out.get("referenced_projection_source_sha256") != source_digest):
            raise ValueError("original_source_sha_changed_between_lenses")
        if source_digest is None:
            source_digest = out.get("referenced_projection_source_sha256")
        if (feature_digest is not None and
                out.get("projection_normalized_source_sha256") != feature_digest):
            raise ValueError("feature_projection_sha_changed_between_lenses")
        if feature_digest is None:
            feature_digest = out.get("projection_normalized_source_sha256")
        selected = mixed["existing_four_mode_selector_on_mixture"][mode]["tickets"]
        if (type(selected) is not list or len(selected) != BUDGETS[mode]
                or any(type(row) is not dict
                       or type(row.get("combo")) is not str
                       or type(row.get("p")) not in (int, float)
                       for row in selected)
                or len({t["combo"] for t in selected}) != BUDGETS[mode]):
            raise ValueError("invalid_mode_ticket_budget_after_scenario_mix")
        results[mode] = {
            "top1": selected[0]["combo"],
            "tickets": selected,
            "scenario_weights_hypotheses": mixed["scenario_weights_hypotheses"],
            "distinct_120_mixture_digest": mixed["mixed_120_board_sha256"],
            "source_exhibition_features_structurally_projected": True,
            "official_original_receipt_authenticated": False,
            "model_hypotheses_calibrated": False,
        }

    pairs = {}
    for i, a in enumerate(MODES):
        for b in MODES[i + 1:]:
            first = {row["combo"] for row in results[a]["tickets"]}
            second = {row["combo"] for row in results[b]["tickets"]}
            pairs[a + "__" + b] = {
                "same_top1": results[a]["top1"] == results[b]["top1"],
                "shared_ticket_count": len(first & second),
                "smaller_mode_overlap_fraction": len(first & second) /
                    min(BUDGETS[a], BUDGETS[b]),
                "no_forced_nonoverlap": True,
            }
    return {
        "schema": SCHEMA,
        "status": "measured_exhibition_projection_unverified_four_mode_lenses",
        "study_id": study_id,
        "race_code": projection["race_code"],
        "source_sha256_claims_not_independently_authenticated": source_digest,
        "normalized_source_sha256_claim": feature_digest,
        "scenario_boards_identical_across_modes": True,
        "scenario_board_sha256": scenario_source_digests,
        "four_mode_research_tickets": results,
        "pairwise_same_race_overlap": pairs,
        "distinct_top1_mode_tickets": len({x["top1"] for x in results.values()}),
        "weights_from_race_features_independently_calibrated": False,
        "official_exhibition_http_receipts_independently_verified": False,
        "official_same_race_racelist_exhibition_odds120_verified": False,
        "actual_model_feature_consumption_remotely_attested": False,
        "first_candidate_remote_receipt_verified": False,
        "outcomes_read_by_adapter": False,
        "new_formal_pilot_races": 0,
        "new_formal_confirmation_races": 0,
        "forecast_usable": False,
        "formal": False,
        "promotion_allowed": False,
        "production_changed": False,
        "warning": (
            "Input projection and scenario weights are unauthenticated "
            "research hypotheses. End-to-end structural computations are NOT "
            "official T-12 receipt, first-remote proof, accuracy, or a basis "
            "to alter live tickets. Mode differences reflect only declared "
            "scenario weights; identical weights may legitimately overlap."
        ),
    }

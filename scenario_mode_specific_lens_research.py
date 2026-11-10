"""Unregistered #1710 MODE-SPECIFIC scenario lens experiment (never live).

Current production and earlier #1710 rank ALL 4 modes from ONE 120-board,
which mathematically forces narrow top5 inside hit top10. This reuses the
existing scenario mixer for each mode with explicitly supplied, potentially
different *predeclared* scenario weights; there is NO overlap penalty, ticket
deletion, automatic diversification or invented evidence/coefficients.

All scenario boards and weights are caller-supplied hypotheses, not measured
pre-T12 official features. NEVER interpret distinct tickets as better picks.
"""
import re

from scenario_four_mode_bridge import compose_scenario_research

MODES = ("narrow", "hit", "balance", "hole")
BUDGETS = {"narrow": 5, "hit": 10, "balance": 16, "hole": 22}
SCHEMA = "SCENARIO_MODE_SPECIFIC_LENS_RESEARCH_V1"
ID = re.compile(r"EXPLORATORY_ONLY_[A-Z0-9_]{4,70}\Z")


def compare_mode_specific_lenses(scenario_boards, weights_by_mode, *, study_id):
    """Four declared evidence-conditioned hypotheses, NOT a live selector."""
    if (type(study_id) is not str or ID.fullmatch(study_id) is None
            or type(scenario_boards) is not dict
            or type(weights_by_mode) is not dict
            or set(weights_by_mode) != set(MODES)):
        raise ValueError("mode_specific_study_or_all_four_weights_missing")
    if not scenario_boards:
        raise ValueError("no_scenario_boards")
    # Reuse #1710's normalizer and exact unchanged rank_modes for every lens.
    # This returns failure if ANY mode lacks required sources or has invalid
    # weight normalization; do not produce partial/wrong-mode predictions.
    outputs = {}
    for mode in MODES:
        weights = weights_by_mode[mode]
        if (type(weights) is not dict
                or set(weights) != set(scenario_boards)):
            raise ValueError("scenario_weights_missing_or_extra:" + mode)
        mixed = compose_scenario_research(scenario_boards, weights)
        if (mixed.get("formal") is not False
                or mixed.get("promotion_allowed") is not False
                or mixed.get("forecast_usable") is not False
                or mixed.get("source_feature_provenance_independently_verified") is not False
                or mixed.get("verified_official_six_exhibition_and_120_odds") is not False):
            raise ValueError("unexpected_upstream_provenance_claim")
        selected = mixed["existing_four_mode_selector_on_mixture"][mode]["tickets"]
        if (type(selected) is not list or len(selected) != BUDGETS[mode]
                or any(type(row) is not dict
                       or type(row.get("combo")) is not str
                       or type(row.get("p")) not in (float, int)
                       for row in selected)
                or len({row["combo"] for row in selected}) != BUDGETS[mode]):
            raise ValueError("invalid_mode_specific_ticket_budget")
        outputs[mode] = {
            "hypothesized_scenario_weights": mixed["scenario_weights_hypotheses"],
            "mixture_sha256": mixed["mixed_120_board_sha256"],
            "tickets": selected,
            "top1": selected[0]["combo"],
            "selection_reuses_existing_rank_modes": True,
            "official_predeadline_scenario_features_verified": False,
            "probabilities_calibrated": False,
        }

    pairs = {}
    for i, a in enumerate(MODES):
        for b in MODES[i + 1:]:
            aa = [x["combo"] for x in outputs[a]["tickets"]]
            bb = [x["combo"] for x in outputs[b]["tickets"]]
            shared = len(set(aa) & set(bb))
            pairs[a + "__" + b] = {
                "same_top1": aa[0] == bb[0],
                "shared_tickets": shared,
                "share_of_smaller_mode": shared / min(BUDGETS[a], BUDGETS[b]),
                "forced_nonoverlap": False,
            }
    return {
        "schema": SCHEMA, "study_id": study_id,
        "status": "unregistered_mode_specific_scenario_hypotheses_only",
        "four_modes": outputs,
        "pairwise_overlap_diagnostics": pairs,
        "distinct_top1_mode_tickets": len(
            {out["top1"] for out in outputs.values()}),
        "different_modes_are_NOT_required_to_have_different_tickets": True,
        "same_weights_can_legitimately_produce_same_top1": True,
        "same_120_board_for_all_modes_is_not_required": True,
        "source_scenario_board_origin_authenticated": False,
        "official_beforeinfo_exhibition_and_odds120_verified": False,
        "wind_tide_motor_entry_or_wall_measured_from_official_source": False,
        "candidate_first_remote_pre_t12_receipt_verified": False,
        "coefficient_calibration_or_hit_rate_proven": False,
        "payout_or_finish_read_by_this_function": False,
        "formal": False, "forecast_usable": False,
        "betting_recommendation": False,
        "production_changed": False, "promotion_allowed": False,
        "warning": (
            "This does not change live forecast or saved archives. "
            "Separate per-mode scenario weights must be generated and "
            "preregistered from actual predeadline race evidence; this "
            "experiment supplies NONE. Distinct outputs are neither "
            "required nor proof of predictive improvement."
        ),
    }

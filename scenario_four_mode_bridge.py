"""All-mode scenario probability bridge — isolated research only.

Consumes scenario-specific, COMPLETE 120-ticket probability boards produced
by upstream evidence-aware models. Does not compute/claim real wind, tide,
entry, wall, exhibition or motor effects; those belong to upstream #1692,
#1694 and experimental #1698. No source collection, results, official odds,
I/O, schedule, deployment or saved-forecast mutation.
"""
from hashlib import sha256
from itertools import permutations
import json
import math

from clean_four_modes import rank_modes

MODES = ("narrow", "hit", "balance", "hole")
BUDGETS = {"narrow": 5, "hit": 10, "balance": 16, "hole": 22}
TICKETS = frozenset(permutations(range(1, 7), 3))
SCENARIOS = frozenset({
    "escape_wall",       # one-course escape with two-course wall
    "two_sashi",         # two-course sashi
    "third_attack",      # third-course attack/makuri-sashi
    "fourth_cado",       # fourth-course kado attack
    "outer_benefit",     # fifth/sixth boat benefits from inside attack
    "deep_entry",        # changed entry/deep inside; research only
})
ATTACK_OR_BENEFIT = frozenset({"third_attack", "fourth_cado", "outer_benefit"})


def _valid_board(board):
    if type(board) not in (list, tuple) or len(board) != 120:
        raise ValueError("full_120_scenario_board_required")
    pairs = {}
    for row in board:
        if type(row) not in (list, tuple) or len(row) != 2:
            raise ValueError("invalid_scenario_row")
        ticket, value = row
        if (type(ticket) not in (tuple, list)
                or len(ticket) != 3
                or any(type(x) is not int for x in ticket)
                or tuple(ticket) not in TICKETS):
            raise ValueError("invalid_scenario_ticket")
        if (type(value) not in (float, int)
                or not math.isfinite(value) or value < 0):
            raise ValueError("invalid_scenario_probability")
        key = tuple(ticket)
        if key in pairs:
            raise ValueError("duplicate_scenario_ticket")
        pairs[key] = float(value)
    if set(pairs) != TICKETS or not math.isclose(
        sum(pairs.values()), 1.0, abs_tol=1e-9
    ):
        raise ValueError("scenario_probability_mass_invalid")
    return pairs


def _digest(board):
    payload = [[list(ticket), round(board[ticket], 15)]
               for ticket in sorted(TICKETS)]
    return sha256(json.dumps(payload, separators=(",", ":")).encode()).hexdigest()


def compose_scenario_research(scenario_boards, scenario_weights):
    """Join already-modeled race scenarios without asserting input authenticity.

    Weights are REQUIRED research hypotheses (not trained/calibrated). Every
    positively weighted scenario must bring a complete 120-way distribution.
    Refuse outcome/payout/odds keys or implicit weights. No default weight.
    """
    if type(scenario_boards) is not dict or type(scenario_weights) is not dict:
        raise ValueError("scenario_maps_required")
    names = set(scenario_boards)
    if (not names or names != set(scenario_weights)
            or names - SCENARIOS):
        raise ValueError("scenario_name_or_weight_mismatch")
    weights = {}
    for name, weight in scenario_weights.items():
        if (type(weight) not in (int, float)
                or not math.isfinite(weight) or weight < 0 or weight > 1):
            raise ValueError("invalid_scenario_weight")
        weights[name] = float(weight)
    if not math.isclose(sum(weights.values()), 1.0, abs_tol=1e-10):
        raise ValueError("scenario_weights_must_sum_one")
    boards = {name: _valid_board(scenario_boards[name]) for name in names}
    combined = {
        ticket: math.fsum(weights[name] * boards[name][ticket]
                          for name in sorted(names))
        for ticket in TICKETS
    }
    if not math.isclose(sum(combined.values()), 1.0, abs_tol=1e-9):
        raise ValueError("mixture_probability_mass_invalid")
    ranked = sorted(combined.items(), key=lambda row: (-row[1], row[0]))
    modes = rank_modes(ranked)  # SAME existing selector: 5 / 10 / 16 / 22.
    if {mode: len(rows["tickets"]) for mode, rows in modes.items()} != BUDGETS:
        raise ValueError("existing_mode_count_contract_changed")

    def contribution(ticket, scenario):
        return weights.get(scenario, 0.0) * boards[scenario][ticket] if scenario in boards else 0.0

    favorites = {ticket for ticket, _ in ranked[:10]}
    attack_weight = sum(weights.get(name, 0.0) for name in ATTACK_OR_BENEFIT)
    # This is a SEPARATE hole research selector, not the original
    # 11..32 positional hole selector. It uses scenario support, not odds.
    hole_candidates = []
    if attack_weight > 0:
        for ticket, p in ranked:
            if ticket in favorites:
                continue
            contributors = {
                name: contribution(ticket, name)
                for name in ATTACK_OR_BENEFIT if name in boards
            }
            support = sum(contributors.values())
            if support <= 0:
                continue
            leading = max(contributors, key=lambda name: (contributors[name], name))
            hole_candidates.append({
                "combo": "-".join(map(str, ticket)),
                "model_score_pct": round(p * 100, 5),
                "attack_benefit_support": support,
                "scenario": leading,
            })
        hole_candidates.sort(key=lambda row: (
            -row["attack_benefit_support"],
            -row["model_score_pct"], row["combo"]))
        hole_candidates = hole_candidates[:22]

    top10 = []
    for ticket, p in ranked[:10]:
        leading = max(sorted(names), key=lambda name: contribution(ticket, name))
        top10.append({
            "combo": "-".join(map(str, ticket)),
            "model_score_pct": round(p * 100, 5),
            "largest_scenario_contributor": leading,
        })

    return {
        "schema": "ALL_MODE_SCENARIO_BRIDGE_EXPLORATORY_V1",
        "status": "result_blind_synthetic_or_unattested_scenario_mixture",
        "scenario_weights_hypotheses": {name: weights[name] for name in sorted(names)},
        "scenario_board_sha256": {name: _digest(boards[name]) for name in sorted(names)},
        "mixed_120_board_sha256": _digest(combined),
        "top10_reference": top10,
        "existing_four_mode_selector_on_mixture": modes,
        "separate_scenario_hole_research": {
            "status": ("hypothesis_candidates" if attack_weight > 0
                       else "unavailable_no_attack_or_benefit_scenario"),
            "tickets": hole_candidates,
            "official_odds_used": False,
            "expected_value_claim": False,
        },
        "mode_ticket_budgets": dict(BUDGETS),
        "source_feature_provenance_independently_verified": False,
        "verified_official_six_exhibition_and_120_odds": False,
        "first_remote_receipt_verified": False,
        "scenario_weights_calibrated": False,
        "probabilities_calibrated": False,
        "confirmed_results_read": False,
        "formal": False,
        "forecast_usable": False,
        "betting_recommendation": False,
        "production_changed": False,
        "model_improvement_proven": False,
        "promotion_allowed": False,
    }

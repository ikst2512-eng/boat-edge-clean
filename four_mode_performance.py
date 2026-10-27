"""Verified four-mode simulated-bet performance. No wagering or fabricated results."""
from __future__ import annotations
from datetime import datetime
from verification_pipeline import valid_ticket

MODE_NAMES = ("hit", "balance", "hole", "narrow")
BUDGET_MIN, BUDGET_MAX, UNIT = 5000, 10000, 100


def allocate(tickets, budget_yen=5000):
    """Allocate a full user-selected race budget in 100-yen units."""
    if type(budget_yen) is not int or not BUDGET_MIN <= budget_yen <= BUDGET_MAX or budget_yen % UNIT:
        raise ValueError("budget_must_be_5000_to_10000_in_100_yen_steps")
    if not isinstance(tickets, list) or not tickets or len(tickets) > 100:
        raise ValueError("invalid_tickets")
    combos = [t["combo"] if isinstance(t, dict) else t for t in tickets]
    if len(combos) != len(set(combos)) or not all(valid_ticket(x) for x in combos):
        raise ValueError("invalid_tickets")
    units, remainder = divmod(budget_yen // UNIT, len(combos))
    if units == 0:
        raise ValueError("too_many_tickets")
    return {combo: (units + (1 if i < remainder else 0)) * UNIT for i, combo in enumerate(combos)}


def evaluate_archive(archive, result, payout_per_100_yen, budget_yen=5000, proof_verified=False):
    """Score only independently verified pre-deadline archives and official results.

    proof_verified must come from a first-Git-add immutable-bytes audit, not the archive itself.
    """
    if not proof_verified:
        raise ValueError("first_add_proof_required")
    if not isinstance(archive, dict) or archive.get("schema") != "CLEAN_FOUR_MODES_PREDEADLINE_V1":
        raise ValueError("forecast_schema")
    race = archive.get("race_code")
    if not isinstance(race, str) or len(race) != 12 or not race.isdigit():
        raise ValueError("race_code")
    saved = datetime.fromisoformat(archive["generated_at_jst"])
    deadline = datetime.fromisoformat(archive["deadline_jst"])
    if saved.utcoffset() is None or deadline.utcoffset() is None or saved >= deadline:
        raise ValueError("not_frozen_before_deadline")
    if result.get("race_code") != race or result.get("status") != "confirmed":
        raise ValueError("unconfirmed_result")
    order = result.get("finish_order")
    if (not isinstance(order, list) or len(order) != 3
        or any(type(n) is not int or n not in range(1, 7) for n in order)
        or len(set(order)) != 3):
        raise ValueError("invalid_finish_order")
    winning = "-".join(map(str, order))
    if type(payout_per_100_yen) is not int or payout_per_100_yen < 100:
        raise ValueError("official_payout_required")
    modes = archive.get("modes", {})
    if not isinstance(modes, dict) or set(modes) != set(MODE_NAMES):
        raise ValueError("four_modes_required")
    out = {}
    for mode in MODE_NAMES:
        stakes = allocate(modes[mode]["tickets"], budget_yen)
        hit = winning in stakes
        returned = stakes.get(winning, 0) * payout_per_100_yen // 100
        out[mode] = {"hit": hit, "budget_yen": budget_yen, "return_yen": returned,
                     "profit_yen": returned - budget_yen, "winning_ticket": winning}
    return {"race_code": race, "verified": True, "budget_yen": budget_yen, "modes": out}


def aggregate(records):
    """Never include invalid, unverified or pending races in the denominator."""
    records = list(records)
    out = {}
    for mode in MODE_NAMES:
        complete = [r["modes"][mode] for r in records
                    if r.get("verified") is True and mode in r.get("modes", {})]
        invested = sum(x["budget_yen"] for x in complete)
        returned = sum(x["return_yen"] for x in complete)
        hits = sum(x["hit"] is True for x in complete)
        out[mode] = {"sample_races": len(complete), "hits": hits,
                     "actual_hit_rate_pct": round(100 * hits / len(complete), 2) if complete else None,
                     "actual_roi_pct": round(100 * returned / invested, 2) if invested else None,
                     "invested_yen": invested, "return_yen": returned,
                     "profit_yen": returned-invested, "verified_only": True}
    return out

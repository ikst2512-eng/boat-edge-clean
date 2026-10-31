"""Shared fixed-stake allocation for verified research selection."""
from verification_pipeline import valid_ticket

BUDGET_MIN, BUDGET_MAX, UNIT = 5000, 10000, 100


def allocate(tickets, budget_yen=5000):
    """Allocate the requested race budget in 100-yen units."""
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

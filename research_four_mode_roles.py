"""Research-only four-mode ticket selection with explicit role and odds requirements.

Not used by the production forecast API or archived predeadline forecasts.
The odds-aware hole mode fails closed when contemporaneous odds are unavailable.
"""
import math

CAPS = {"narrow": 5, "hit": 12, "balance": 15, "hole": 20}
TARGETS = {"hit": 0.60, "balance": 0.50, "hole": 0.125, "narrow": 0.40}

def research_modes(prob_rows, odds=None):
    rows = [("-".join(map(str, ticket)), float(p)) for ticket, p in prob_rows]
    if len(rows) != 120 or len({combo for combo, _ in rows}) != 120 or abs(sum(p for _, p in rows)-1) > 1e-6:
        raise ValueError("invalid_probability_board")
    if any(not math.isfinite(p) or p < 0 for _, p in rows):
        raise ValueError("invalid_probability")
    ordered = sorted(rows, key=lambda x: (-x[1], x[0]))
    # The existing balance diversity heuristic is the published baseline.
    result = {}
    for mode, choices in (("narrow", ordered[:5]), ("hit", ordered[:CAPS["hit"]])):
        result[mode] = {"tickets": [{"combo": c, "p": round(p * 100, 5)} for c,p in choices],
                        "max_tickets": CAPS[mode], "selection": "model_probability",
                        "estimated_coverage_pct": round(100 * sum(p for _,p in choices),2),
                        "target_hit_rate_pct": 100 * TARGETS[mode],
                        "target_proven": False}
    # Balance preserves the alternative-first/second-place ordering without peeking at results.
    by_combo = dict(rows)
    # The production target may stop early. Build an independent, 15-pick diverse ranking.
    remaining = dict(rows)
    diverse = []
    while remaining and len(diverse) < CAPS["balance"]:
        firsts = {c[0] for c in diverse}
        pairs = {c[:3] for c in diverse}
        pick = max(remaining, key=lambda c: (remaining[c] * (1 + (0.30 if c[0] not in firsts else 0)
                         + (0.15 if c[:3] not in pairs else 0)), -int(c[0]),-int(c[2]),-int(c[4])))
        diverse.append(pick)
        del remaining[pick]
    result["balance"] = {"tickets": [{"combo":c, "p": round(by_combo[c]*100,5)} for c in diverse],
                         "max_tickets":CAPS["balance"], "selection":"branch_diversity",
                         "estimated_coverage_pct":round(100*sum(by_combo[c] for c in diverse),2),
                         "target_hit_rate_pct":50.0,"target_proven":False}
    if odds is None:
        result["hole"] = {"tickets": [], "max_tickets":CAPS["hole"],
                          "selection":"unavailable_without_timestamped_odds",
                          "status":"odds_required", "target_hit_rate_pct":12.5, "target_proven":False}
        return result
    if not isinstance(odds, dict) or set(odds) != set(by_combo):
        raise ValueError("complete_odds_board_required")
    if any(type(v) not in (float,int) or not math.isfinite(v) or v <= 1 for v in odds.values()):
        raise ValueError("invalid_odds")
    # Descriptive EV only: model probabilities are uncalibrated.
    candidates = sorted(rows, key=lambda x: (-x[1]*odds[x[0]],-odds[x[0]],x[0]))
    # Do not label probability-only tickets as verified high-return selections.
    selections = candidates[:CAPS["hole"]]
    result["hole"] = {"tickets":[{"combo":c,"p":round(p*100,5),"odds":odds[c],
                                    "estimated_ev":round(p*odds[c],5)} for c,p in selections],
                      "max_tickets":CAPS["hole"], "selection":"uncalibrated_expected_value",
                      "status":"research_only_not_a_betting_signal",
                      "target_hit_rate_pct":12.5,"target_proven":False}
    return result

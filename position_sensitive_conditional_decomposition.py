"""Pure mathematical audit of P(2nd | 1st) and P(3rd | 1st, 2nd).

This reports input sensitivity only. It never reads outcomes, official sources
or payouts and never changes the frozen head marginal or mode selector.
"""
from position_sensitive_conditioned_lab import _board

SCHEMA = "POSITION_SENSITIVE_CONDITIONAL_DECOMPOSITION_RESEARCH_V1"


def _conditionals(rows):
    board = _board(rows)
    first_masses = {
        h: sum(p for (a, _, _), p in board.items() if a == h)
        for h in range(1, 7)
    }
    by_second, by_third = {}, {}
    for h in range(1, 7):
        for s in range(1, 7):
            if s == h:
                continue
            m2 = sum(p for (a, b, _), p in board.items() if a == h and b == s)
            if not 0 < m2 < first_masses[h]:
                raise ValueError("invalid_conditional_second_mass")
            by_second[(h, s)] = m2 / first_masses[h]
            for t in range(1, 7):
                if t in (h, s):
                    continue
                by_third[(h, s, t)] = board[(h, s, t)] / m2
        if abs(sum(by_second[(h, s)] for s in range(1, 7) if s != h) - 1.0) > 1e-12:
            raise ValueError("conditional_second_not_normalized")
        for s in range(1, 7):
            if s == h:
                continue
            if abs(sum(by_third[(h, s, t)] for t in range(1, 7)
                       if t not in (h, s)) - 1.0) > 1e-12:
                raise ValueError("conditional_third_not_normalized")
            for t in range(1, 7):
                if t in (h, s):
                    continue
                reconstructed = first_masses[h] * by_second[(h, s)] * by_third[(h, s, t)]
                if abs(reconstructed - board[(h, s, t)]) > 1e-14:
                    raise ValueError("conditional_reconstruction_drift")
    return first_masses, by_second, by_third


def compare_conditional_decomposition(before, after):
    """Mechanically inspect sequential conditional probabilities in 120 tickets.

    Head probability must be unchanged. This cannot assess predictive quality
    or infer the effects of unavailable evidence.
    """
    hm0, ps0, pt0 = _conditionals(before)
    hm1, ps1, pt1 = _conditionals(after)
    if any(abs(hm0[h] - hm1[h]) > 1e-12 for h in hm0):
        raise ValueError("first_boat_probability_mass_drift")
    second = {}
    third = {}
    for h in range(1, 7):
        ss = [s for s in range(1, 7) if s != h]
        best0 = min(ss, key=lambda s: (-ps0[(h, s)], s))
        best1 = min(ss, key=lambda s: (-ps1[(h, s)], s))
        second[str(h)] = {
            "first_mass_preserved": True,
            "first_boat_mass": hm1[h],
            "top_second_before": best0,
            "top_second_after": best1,
            "top_second_changed": best0 != best1,
            "second_probabilities_before": {
                str(s): ps0[(h, s)] for s in ss},
            "second_probabilities_after": {
                str(s): ps1[(h, s)] for s in ss},
        }
        for s in ss:
            ts = [t for t in range(1, 7) if t not in (h, s)]
            t0 = min(ts, key=lambda t: (-pt0[(h, s, t)], t))
            t1 = min(ts, key=lambda t: (-pt1[(h, s, t)], t))
            third[f"{h}-{s}"] = {
                "top_third_before": t0,
                "top_third_after": t1,
                "top_third_changed": t0 != t1,
                "third_probabilities_before": {
                    str(t): pt0[(h, s, t)] for t in ts},
                "third_probabilities_after": {
                    str(t): pt1[(h, s, t)] for t in ts},
            }
    return {
        "schema": SCHEMA,
        "status": "same_supplied_race_conditional_probability_math_only",
        "head_mass_preserved_for_all_six": True,
        "max_abs_second_probability_delta": max(
            abs(ps0[k] - ps1[k]) for k in ps0),
        "max_abs_third_probability_delta": max(
            abs(pt0[k] - pt1[k]) for k in pt0),
        "heads_with_top_second_changed": sum(
            x["top_second_changed"] for x in second.values()),
        "head_second_pairs_with_top_third_changed": sum(
            x["top_third_changed"] for x in third.values()),
        "second_given_head": second,
        "third_given_head_and_second": third,
        "outcome_accuracy_measured": False,
        "inputs_official_and_predeadline_verified": False,
        "model_improvement_proven": False,
        "formal": False,
        "promotion_allowed": False,
        "production_changed": False,
    }

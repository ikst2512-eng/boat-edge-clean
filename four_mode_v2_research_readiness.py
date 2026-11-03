"""Read-only, evidence-gated V2 research summary; never certifies production accuracy.

Consumes only the existing immutable-archive shadow audit. No forecasts are
generated, modified or ranked here. Previous V1 exploration informed the
shadow candidate, so this is not a preregistered independent holdout.
"""
import json
from math import comb
from four_mode_v2_predeclared_shadow import evaluate, PAIRS, PAIR_OUTCOMES

MIN_PAIRED = 100
MIN_DAYS = 3
MIN_DISCORDANT = 20
MIN_MATURE_RESULT_COVERAGE = 0.90


def paired_one_sided_pvalue(gained, lost):
    """Exact conditional sign-test tail P(X >= gained | discordant, p=0.5)."""
    if any(type(x) is not int or x < 0 for x in (gained, lost)):
        raise ValueError("invalid_discordances")
    n = gained + lost
    if n == 0:
        return None
    return sum(comb(n, k) for k in range(gained, n + 1)) / 2**n


def summarize(raw):
    if raw.get("formal") is not False or raw.get("independent_remote_first_seen_verified") is not False:
        raise ValueError("unexpected_evidence_promotion")
    groups = raw.get("groups", {})
    if not isinstance(groups, dict):
        raise ValueError("invalid_groups")
    totals = {
        "saved_forecasts": 0, "paired_results": 0, "pending_results": 0,
        "matured_comparable": 0,
        "matured_modes": {m: {f"top{n}": 0 for n in (3, 5, 10)}
                          for m in ("narrow", "hit", "balance", "hole")},
        "before_deadline": 0, "within_60m_after_deadline": 0,
        "over_60m_after_deadline": 0, "applied": 0,
        "gained_top3": 0, "lost_top3": 0,
        "baseline": {f"top{n}": 0 for n in (3, 5, 10)},
        "candidate": {f"top{n}": 0 for n in (3, 5, 10)},
        "modes": {m: {f"top{n}": 0 for n in (3, 5, 10)}
                  for m in ("narrow", "hit", "balance", "hole")},
        "paired_modes": {f"{a}_vs_{b}": {f"top{n}": {o: 0 for o in PAIR_OUTCOMES}
                         for n in (3, 5, 10)} for a,b in PAIRS},
    }
    completed_days = 0
    for date, row in sorted(groups.items()):
        if len(date) != 8 or not date.isdecimal():
            raise ValueError("invalid_date")
        c = row["comparable"]
        p = row["pending_results"]
        saved = row["forecast_files"]
        if any(type(x) is not int or x < 0 for x in (c, p, saved, row["applied"],
                                                    row["gained_top3"], row["lost_top3"])):
            raise ValueError("invalid_count")
        matured = row["matured_comparable"]
        if type(matured) is not int or not 0 <= matured <= c:
            raise ValueError("invalid_matured_comparable")
        if c + p > saved or row["applied"] > c:
            raise ValueError("inconsistent_count")
        completed_days += int(c > 0)
        totals["matured_comparable"] += matured
        for key, value in (("saved_forecasts", saved), ("paired_results", c),
                           ("pending_results", p), ("applied", row["applied"]),
                           ("gained_top3", row["gained_top3"]), ("lost_top3", row["lost_top3"])):
            totals[key] += value
        phases = row["pending_by_deadline"]
        if sum(phases.values()) != p:
            raise ValueError("pending_phase_mismatch")
        for key in ("before_deadline", "within_60m_after_deadline", "over_60m_after_deadline"):
            if type(phases.get(key)) is not int or phases[key] < 0:
                raise ValueError("invalid_pending_phase")
            totals[key] += phases[key]
        for n in (3, 5, 10):
            k = f"top{n}"
            for group in ("baseline", "candidate"):
                val = row[group][k]
                if type(val) is not int or not 0 <= val <= c:
                    raise ValueError("invalid_topn")
                totals[group][k] += val
            for mode in totals["modes"]:
                val = row["modes"][mode][k]
                if type(val) is not int or not 0 <= val <= c:
                    raise ValueError("invalid_mode_topn")
                totals["modes"][mode][k] += val
                mature_hits = row["matured_modes"][mode][k]
                if type(mature_hits) is not int or not 0 <= mature_hits <= matured:
                    raise ValueError("invalid_matured_topn")
                if mature_hits > val:
                    raise ValueError("mature_hits_exceed_all_hits")
                totals["matured_modes"][mode][k] += mature_hits
        for left, right in PAIRS:
            key = f"{left}_vs_{right}"
            for n in (3, 5, 10):
                flag = f"top{n}"
                pair = row["paired_modes"][key][flag]
                if (set(pair) != set(PAIR_OUTCOMES)
                        or any(type(v) is not int or v < 0 for v in pair.values())
                        or sum(pair.values()) != c):
                    raise ValueError("invalid_paired_mode_partition")
                if pair["both"] + pair["left_only"] != row["modes"][left][flag]:
                    raise ValueError("paired_left_mismatch")
                if pair["both"] + pair["right_only"] != row["modes"][right][flag]:
                    raise ValueError("paired_right_mismatch")
                for outcome in PAIR_OUTCOMES:
                    totals["paired_modes"][key][flag][outcome] += pair[outcome]
        if row["candidate"]["top10"] != row["baseline"]["top10"]:
            raise ValueError("membership_violation")
        if row["candidate"]["top3"] - row["baseline"]["top3"] != row["gained_top3"] - row["lost_top3"]:
            raise ValueError("discordance_mismatch")
        if row["gained_top3"] + row["lost_top3"] > row["applied"]:
            raise ValueError("impossible_discordances")
    n = totals["paired_results"]
    gains = totals["gained_top3"]
    losses = totals["lost_top3"]
    if n != raw.get("v2_comparable", 0):
        raise ValueError("paired_total_mismatch")
    # Coverage is a diagnostic for selection bias, NOT a claim the result
    # provider must have published a result within the first hour.
    mature_denom = totals["matured_comparable"] + totals["over_60m_after_deadline"]
    mature_coverage = (totals["matured_comparable"] / mature_denom
                       if mature_denom else None)
    missing_overdue = totals["over_60m_after_deadline"]
    # Sensitivity envelope under the explicit scenario that all currently
    # unresolved overdue races eventually produce a valid finish order.
    # These are not confidence intervals, official hit-rate bounds, or
    # empirical evidence about the missing outcomes.
    mature_sensitivity = {}
    for mode, counts in totals["matured_modes"].items():
        mature_sensitivity[mode] = {}
        for label, hits in counts.items():
            mature_sensitivity[mode][label] = {
                "confirmed_mature_hits": hits,
                "unresolved_overdue": missing_overdue,
                "scenario_denominator": mature_denom,
                "all_missing_miss_rate": (round(hits / mature_denom, 6)
                                           if mature_denom else None),
                "all_missing_hit_rate": (round((hits + missing_overdue) / mature_denom, 6)
                                          if mature_denom else None),
            }
    reasons = []
    if mature_coverage is None or mature_coverage < MIN_MATURE_RESULT_COVERAGE:
        reasons.append("insufficient_mature_result_coverage")
    if n < MIN_PAIRED:
        reasons.append("fewer_than_100_paired_races")
    if completed_days < MIN_DAYS:
        reasons.append("fewer_than_3_distinct_evaluation_days")
    if gains + losses < MIN_DISCORDANT:
        reasons.append("fewer_than_20_discordant_top3_races")
    if totals["candidate"]["top5"] < totals["baseline"]["top5"]:
        reasons.append("candidate_top5_worse")
    pvalue = paired_one_sided_pvalue(gains, losses)
    if pvalue is None or pvalue > 0.025:
        reasons.append("no_strong_paired_top3_evidence")
    # Sufficient exploratory evidence can never replace independently attested
    # first publication and a completely untouched future evaluation period.
    reasons.append("independent_first_publication_not_verified")
    reasons.append("independent_untouched_holdout_not_verified")
    return {
        "status": "research_only_not_production_eligible",
        "model_version": raw.get("model_version"),
        "protocol": raw.get("protocol"),
        "formal": False, "production_promotion_allowed": False,
        "total": totals, "evaluation_days": completed_days,
        "top3_net_gain": gains - losses,
        "paired_top3_one_sided_pvalue": pvalue,
        "comparable_denominator": n,
        "mature_outcome_denominator": mature_denom,
        "overdue_missingness_sensitivity": mature_sensitivity,
        "sensitivity_assumption": "All unresolved overdue cases eventually have valid finish orders; not verified.",
        "mature_result_coverage": round(mature_coverage, 6) if mature_coverage is not None else None,
        "mature_coverage_diagnostic_threshold": MIN_MATURE_RESULT_COVERAGE,
        "blocking_reasons": reasons,
        "excluded": raw.get("excluded", {}),
        "evaluated_at_jst": raw.get("evaluated_at_jst"),
    }


if __name__ == "__main__":
    print("V2_RESEARCH_READINESS=" + json.dumps(summarize(evaluate()), sort_keys=True))

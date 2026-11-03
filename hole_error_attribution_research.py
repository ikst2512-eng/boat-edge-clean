"""Research-only attribution of missed hole tickets to head, second pair, or third.

All candidate sets are computed from source forecasts BEFORE confirmed outcomes
are opened. Existing locked candidate selectors are imported unchanged.
This is retrospective diagnosis, never an independent holdout or a tuning gate.
"""
import hashlib
import json
from collections import Counter
from pathlib import Path

from four_mode_archive_api import archived_four_modes
from four_mode_frozen_diagnostic import compare_race
from four_mode_historical_cohort import run as cohort_run
from hole_third_choice_research import POLICIES, TOPS, national_rates, variants


def failure_class(tickets, winning_ticket):
    """Attribute a missed exacta/trifecta to the first missing prefix."""
    if winning_ticket in tickets:
        return "hit"
    head, second, _ = winning_ticket.split("-")
    if head not in {t.split("-")[0] for t in tickets}:
        return "first_head_absent"
    if (head, second) not in {tuple(t.split("-")[:2]) for t in tickets}:
        return "second_pair_absent"
    return "third_boat_absent"


def inspect(codes, root):
    root = Path(root)
    unavailable = Counter()
    reasons = {p: Counter() for p in POLICIES}
    gains = {p: {f"top{k}": {"gained": 0, "lost": 0, "hits": 0}
                 for k in TOPS} for p in POLICIES}
    pair_recovery = {p: Counter() for p in POLICIES[1:]}
    rows = []
    for code in codes:
        status, archive = archived_four_modes(code, root)
        if status != 200:
            unavailable["invalid_archive"] += 1
            continue
        # Selection is fully completed without any confirmed finish information.
        chosen = variants(archive, national_rates(code, root))
        baseline = chosen["baseline"]
        if any(chosen[p][:5] != baseline[:5] or len(chosen[p]) != 10
               for p in POLICIES):
            raise ValueError("selector_top5_or_budget_changed")
        donor = {ticket["combo"] for mode in ("hit", "balance")
                 for ticket in archive["modes"][mode]["tickets"]}
        result = compare_race(code, root)
        if result.get("status") != "historical_comparison_only":
            unavailable["result_unconfirmed"] += 1
            continue
        winning = result["winning_ticket"]
        base_cause = failure_class(baseline, winning)
        reason_by_policy = {}
        flags = {}
        for p in POLICIES:
            picks = chosen[p]
            reason = failure_class(picks, winning)
            reason_by_policy[p] = reason
            reasons[p][reason] += 1
            flags[p] = {f"top{k}": winning in picks[:k] for k in TOPS}
            for k in TOPS:
                key = f"top{k}"
                now = flags[p][key]
                before = flags["baseline"][key] if p != "baseline" else now
                bucket = gains[p][key]
                bucket["hits"] += int(now)
                bucket["gained"] += int(now and not before)
                bucket["lost"] += int(before and not now)
            if p != "baseline" and base_cause == "second_pair_absent":
                bucket = pair_recovery[p]
                bucket["baseline_missing_pair"] += 1
                bucket["pair_added"] += int(reason in ("hit", "third_boat_absent"))
                bucket["third_still_wrong"] += int(reason == "third_boat_absent")
                bucket["full_ticket_added"] += int(reason == "hit")
                bucket["winner_in_donor_tickets"] += int(winning in donor)
                bucket["winner_pair_in_donor_tickets"] += int(
                    any(tuple(t.split("-")[:2]) == tuple(winning.split("-")[:2])
                        for t in donor))
        rows.append({"race_code": code, "baseline_failure": base_cause,
                     "failure_by_policy": reason_by_policy, "flags": flags})
    for p in POLICIES:
        for k in TOPS:
            bucket = gains[p][f"top{k}"]
            bucket["net"] = bucket["gained"] - bucket["lost"]
            if k <= 5 and (bucket["gained"] or bucket["lost"]):
                raise ValueError("top5_performance_changed")
    return {"comparable": len(rows), "unavailable": dict(unavailable),
            "miss_reasons": {p: dict(reasons[p]) for p in POLICIES},
            "missing_pair_recovery": {p: dict(pair_recovery[p])
                                      for p in POLICIES[1:]},
            "topn": gains, "rows": rows}


def run(root=None):
    root = Path(root) if root is not None else Path(__file__).resolve().parent
    cohort = cohort_run(root=root, limit=120)
    if cohort.get("status") != "historical_research_only":
        return {"status": "historical_cohort_unavailable", "formal": False}
    older = sorted(code for code in cohort["cohort_codes"] if code[:8] < "20261103")
    already_seen = sorted(path.stem for path in
                          (root / "four_mode_forecasts").glob("20261103????.json")
                          if not path.is_symlink())
    return {"schema": "HOLE_PAIR_THIRD_ERROR_ATTRIBUTION_V1",
            "status": "retrospective_diagnostic_only",
            "formal": False, "independent_holdout": False,
            "prospective_validation": False,
            "independent_first_receipt_verified": False,
            "production_forecast_changed": False,
            "selector_changed": False,
            "older_cohort_sha256": hashlib.sha256(
                "\n".join(older).encode()).hexdigest(),
            "groups": {"previously_inspected_history": inspect(older, root),
                       "nov03_already_inspected": inspect(already_seen, root)},
            "warning": "Retrospective, repeatedly inspected outcomes only. "
                       "Head, pair and third misses are attribution, not "
                       "independent evidence of accuracy improvement."}


if __name__ == "__main__":
    print(json.dumps(run(), ensure_ascii=False, sort_keys=True))

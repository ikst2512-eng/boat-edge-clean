"""Frozen-period, result-blind *venue-only* scenario mixture historical holdout.

August–September official-K postrace records train a 120-course-finish
probability board. October is an untouched historical test period. The
October *prediction builder* receives ONLY the venue code, never October
finishes, winning method, actual entry, ST, wind, motor or payout.

This is NOT a live pre-deadline candidate: historical eligibility requires
six actual-course finishers and cannot be known as such before a race.
Course labels are actual POSTRACE courses; mapping these numbers to boat
tickets before a future race is not certified. No odds/ROI, no production use.
"""
from collections import Counter, defaultdict
from datetime import date
from hashlib import sha256
from itertools import permutations
import json
import math
import random

from scenario_official_K_attack_benefit_holdout import GROUPS, _group

STUDY = "RETROSPECTIVE_ONLY_K92_VENUE_SCENARIO_OCT2026_V1"
TICKETS = tuple(permutations(range(1, 7), 3))
TOPS = (1, 3, 5, 10)
GROUP_FIRST = {
    "one_escape": {1},
    "three_makuri": {3}, "three_makuri_sashi": {3}, "three_other_win": {3},
    "four_makuri": {4}, "four_makuri_sashi": {4}, "four_other_win": {4},
    "five_makuri_sashi": {5}, "five_other_win": {5},
    "all_other": {1, 2, 6},
}
# Fixed, transparent hypotheses: not tuned on October.
VENUE_GROUP_PRIOR_N = 40
GROUP_TAIL_PRIOR_N = 20
DIRECT_TICKET_PSEUDOCOUNT = 1
BOOTSTRAP_SEED = 1710
BOOTSTRAP_REPS = 1000


def _validate_record(record, *, training):
    if type(record) is not dict or record.get("no_causal_attack_observed") is not True:
        raise ValueError("not_a_retrospective_finished_race")
    day, venue = record.get("day"), record.get("venue")
    if (type(day) is not str or len(day) != 8 or not day.isdigit()
            or type(venue) is not str or len(venue) != 2 or not venue.isdigit()
            or not 1 <= int(venue) <= 24):
        raise ValueError("race_day_and_venue_required")
    try:
        d = date.fromisoformat(day[:4] + "-" + day[4:6] + "-" + day[6:8])
    except ValueError as exc:
        raise ValueError("invalid_calendar_date") from exc
    if d.year != 2026 or d.month not in ((8, 9) if training else (10,)):
        raise ValueError("period_leakage_or_date_drift")
    finish = record.get("actual_course_finish")
    if (type(finish) is not tuple or len(finish) != 6
            or set(finish) != set(range(1, 7))
            or any(type(x) is not int for x in finish)):
        raise ValueError("six_actual_course_labels_required")
    group = record.get("group")
    if (group not in GROUPS or finish[0] not in GROUP_FIRST[group]
            or group != _group(finish[0], record.get("method"))):
        raise ValueError("winner_method_group_course_mismatch")
    return venue, day, group, finish[:3]


def fit_aug_sep(records):
    """Only fixed Aug–Sep historical training outcome records are accepted."""
    if type(records) is not list or not records:
        raise ValueError("nonempty_training_records_required")
    venue_groups, groups, group_tails, direct = defaultdict(Counter), Counter(), defaultdict(Counter), Counter()
    for record in records:
        venue, _, group, ticket = _validate_record(record, training=True)
        venue_groups[venue][group] += 1
        groups[group] += 1
        group_tails[group][ticket] += 1
        direct[ticket] += 1
    n = len(records)
    group_prior = {g: (groups[g] + 1) / (n + len(GROUPS)) for g in GROUPS}
    if not math.isclose(sum(group_prior.values()), 1, abs_tol=1e-12):
        raise ValueError("group_mass_broken")
    base = {t: (direct[t] + DIRECT_TICKET_PSEUDOCOUNT) /
            (n + len(TICKETS) * DIRECT_TICKET_PSEUDOCOUNT)
            for t in TICKETS}
    group_given_ticket = {
        g: {t: (group_tails[g][t] + GROUP_TAIL_PRIOR_N / size) /
            (groups[g] + GROUP_TAIL_PRIOR_N)
            for t in TICKETS if t[0] in GROUP_FIRST[g]}
        for g in GROUPS
        for size in [len([t for t in TICKETS if t[0] in GROUP_FIRST[g]])]
    }
    if any(not math.isclose(sum(b.values()), 1, abs_tol=1e-12)
           for b in group_given_ticket.values()):
        raise ValueError("tail_mass_broken")
    # The trained object has NO target-period outcomes.
    fingerprint = sha256(json.dumps({
        "n": n, "group_counts": dict(groups), "direct": {
            "-".join(map(str, t)): direct[t] for t in TICKETS
        }, "by_venue": {k: dict(v) for k,v in sorted(venue_groups.items())},
    }, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return {
        "n": n, "group_prior": group_prior,
        "venue_groups": {v: dict(c) for v,c in venue_groups.items()},
        "base": base, "conditional_tails": group_given_ticket,
        "frozen_training_sha256": fingerprint,
        "contains_october_labels": False,
        "predictions_use_actual_final_entry": False,
    }


def predict_at_venue(fit, venue):
    """Input surface deliberately accepts only a pre-race-known venue code.

    No option for target method, outcome, actual entry, comments or odds.
    """
    if (type(venue) is not str or len(venue) != 2 or not venue.isdigit()
            or not 1 <= int(venue) <= 24):
        raise ValueError("venue_code_required_not_target_result")
    vg = fit["venue_groups"].get(venue, {})
    v_n = sum(vg.values())
    weights = {
        g: (vg.get(g, 0) + VENUE_GROUP_PRIOR_N * fit["group_prior"][g])
        / (v_n + VENUE_GROUP_PRIOR_N)
        for g in GROUPS
    }
    proposed = {
        ticket: math.fsum(weights[g] *
                          fit["conditional_tails"][g].get(ticket, 0)
                          for g in GROUPS)
        for ticket in TICKETS
    }
    if (not math.isclose(sum(proposed.values()), 1, abs_tol=1e-10)
            or min(proposed.values()) <= 0):
        raise ValueError("venue_scenario_board_invalid")
    return {
        "baseline_global": fit["base"],
        "venue_scenario": proposed,
        "scenario_weights": weights,
        "venue_from_input_only": venue,
        "result_or_target_method_consumed": False,
        "final_entry_consumed": False,
        "model_is_calibrated": False,
    }


def _metrics_init():
    return {"n": 0, "sum_logloss": 0., "sum_brier": 0.,
            **{f"top{k}": 0 for k in TOPS}}


def _summarize(metric):
    if not metric["n"]:
        return {"n": 0, "logloss": None, "brier120": None,
                **{f"top{k}_pct": None for k in TOPS}}
    n = metric["n"]
    return {"n": n, "logloss": round(metric["sum_logloss"] / n, 7),
            "brier120": round(metric["sum_brier"] / n, 7),
            **{f"top{k}_pct": round(metric[f"top{k}"] / n * 100, 4)
               for k in TOPS}}


def score_october_holdout(fit, records, *, expected_oct_n=None):
    """Assess fixed fitted venue-only board; result inspected AFTER prediction."""
    if type(records) is not list or not records:
        raise ValueError("nonempty_october_records_required")
    if expected_oct_n is not None and len(records) != expected_oct_n:
        raise ValueError("october_cohort_size_changed")
    combined = {m: _metrics_init() for m in ("baseline_global", "venue_scenario")}
    by_group = {g: {m: _metrics_init() for m in combined} for g in GROUPS}
    top_gained_lost = {k: {"gained":0, "lost":0, "both":0, "neither":0} for k in TOPS}
    day_deltas = defaultdict(lambda: {"n":0, "sum_loss_delta":0.})
    # First obtain the only allowed pre-event input; labels are processed only
    # after both predictions have already been built.
    for record in records:
        venue = record.get("venue") if type(record) is dict else None
        pred = predict_at_venue(fit, venue)
        _, day, group, actual = _validate_record(record, training=False)
        hits = {}
        losses = {}
        for name in combined:
            board = pred[name]
            ranked = sorted(TICKETS, key=lambda t: (-board[t], t))
            p = board[actual]
            loss = -math.log(p)
            brier = 1.0 - 2 * p + math.fsum(x * x for x in board.values())
            losses[name] = loss
            hits[name] = {k: actual in ranked[:k] for k in TOPS}
            for bag in (combined[name], by_group[group][name]):
                bag["n"] += 1
                bag["sum_logloss"] += loss
                bag["sum_brier"] += brier
                for k in TOPS:
                    bag[f"top{k}"] += int(hits[name][k])
        for k in TOPS:
            a = hits["baseline_global"][k]
            b = hits["venue_scenario"][k]
            status = "both" if a and b else "gained" if b else "lost" if a else "neither"
            top_gained_lost[k][status] += 1
        day_deltas[day]["n"] += 1
        day_deltas[day]["sum_loss_delta"] += (
            losses["venue_scenario"] - losses["baseline_global"])
    if expected_oct_n == 4382 and len(day_deltas) != 31:
        raise ValueError("october_day_cohort_drift")
    rng = random.Random(BOOTSTRAP_SEED)
    days = sorted(day_deltas)
    draws = []
    for _ in range(BOOTSTRAP_REPS):
        sample = [days[rng.randrange(len(days))] for __ in days]
        total_n = sum(day_deltas[d]["n"] for d in sample)
        draws.append(sum(day_deltas[d]["sum_loss_delta"] for d in sample) / total_n)
    draws.sort()
    lo = draws[int(.025 * (BOOTSTRAP_REPS - 1))]
    hi = draws[int(.975 * (BOOTSTRAP_REPS - 1))]
    logdelta = (combined["venue_scenario"]["sum_logloss"] -
                combined["baseline_global"]["sum_logloss"]) / len(records)
    baseline_summary = _summarize(combined["baseline_global"])
    candidate_summary = _summarize(combined["venue_scenario"])
    historical_checks = {
        f"top{k}_nonregression":
            combined["venue_scenario"][f"top{k}"] >=
            combined["baseline_global"][f"top{k}"]
        for k in TOPS
    }
    # Not "significant" merely because the tiny point estimate is negative.
    historical_checks["paired_logloss_upper95_below_zero"] = hi < 0
    historical_checks["paired_brier120_nonregression"] = (
        candidate_summary["brier120"] <= baseline_summary["brier120"])
    historical_checks["known_before_deadline_actual_entry"] = False
    historical_checks["independent_T12_first_remote_receipt"] = False
    historical_checks["300_plus_300_prospective_pass"] = False
    historical_checks["preregistered_before_future_predictions"] = False
    return {
        "study_id": STUDY,
        "frozen_adoption_gate": {
            "checks": historical_checks,
            "all_checks_passed": all(historical_checks.values()),
            "reason": ("historical_only_and_prospective_evidence_missing"
                       if not all(historical_checks.values()) else "review_required"),
            "model_switch_allowed": False,
        },
        "train_n": fit["n"], "historical_holdout_oct_n": len(records),
        "train_aggregate_sha256": fit["frozen_training_sha256"],
        "feature_used_before_october_outcome": ["venue_code_only"],
        "method_used_at_prediction_time": False,
        "actual_entry_used_at_prediction_time": False,
        "baselines": {k: _summarize(v) for k,v in combined.items()},
        "by_actual_winner_method_stratum_for_diagnostics_only": {
            g: {k: _summarize(v) for k,v in by_group[g].items()} for g in GROUPS
        },
        "head_to_head_topk": top_gained_lost,
        "paired_logloss_delta_candidate_minus_baseline": round(logdelta, 7),
        "paired_day_bootstrap_logloss_delta95": [round(lo, 7), round(hi, 7)],
        "candidate_better_on_historical_oct_logloss": logdelta < 0,
        "prospective_accuracy_established": False,
        "true_predeadline_eligibility_known": False,
        "postrace_actual_courses_used_as_120_order_labels": True,
        "beforeinfo_meeting_comments_motor_used": False,
        "future_prediction_allowed": False,
        "production_changed": False,
        "promotion_allowed": False,
    }


def run_frozen_october_study(source_zip):
    from scenario_official_K_attack_benefit_holdout import analyze_official_K_92day
    original = analyze_official_K_92day(source_zip, return_internal_records=True)
    rows = original["internal_retrospective_records_only"]
    if (original["train_n"], original["historical_october_n"]) != (8919, 4382):
        raise ValueError("frozen_training_period_size_changed")
    fit = fit_aug_sep(rows["train_aug_sep"])
    result = score_october_holdout(
        fit, rows["historical_holdout_oct"], expected_oct_n=4382)
    result["source_zip_sha256"] = original["source_zip_sha256"]
    result["official_K_days_verified"] = original["official_K_days_verified"]
    result["clean_cohort"] = original["clean_six_finishers"]
    return result

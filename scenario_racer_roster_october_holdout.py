"""Read-only official-K Aug/Sep -> October BOAT-ticket racer-ability holdout.

Baseline: TRAIN-only drawn-boat head and conditional second/third frequencies.
Candidate: same conditional tail, with 6 registered racers' TRAIN-only
historical win residual over the DRAWN-BOAT baseline. Both models use boat
numbers, not postrace actual course, when emitting a 120-ticket prediction.

No October outcomes, method, wind, actual entry, ST, or payouts in the predictor.
The K original is POSTRACE: roster is retrospectively identified and cannot
certify actual predeadline roster receipt. Only research, no model promotion.
"""
from collections import Counter, defaultdict
from datetime import date
from hashlib import sha256
from itertools import permutations
import json
import math
import random

STUDY = "HISTORICAL_ONLY_K92_RACER_ROSTER_OCTOBER_HEAD_RESIDUAL_V1"
TICKETS = tuple(permutations(range(1, 7), 3))
BOATS = tuple(range(1, 7))
TOPS = (1, 3, 5, 10)
BASE_HEAD_PRIOR_PER_BOAT = 10
TAIL_PRIOR_PER_TICKET = 1
ATHLETE_EXPECTED_WIN_PRIOR = 8
BOOTSTRAP_SEED = 171002
BOOTSTRAP_REPS = 1200


def _validate_record(r, *, training):
    if (type(r) is not dict
            or r.get("no_causal_attack_observed") is not True
            or r.get("roster_was_extracted_from_postrace_K_not_a_predeadline_receipt") is not True):
        raise ValueError("historical_verified_shape_required")
    day = r.get("day")
    if type(day) is not str or len(day) != 8 or not day.isdigit():
        raise ValueError("historical_day_invalid")
    try:
        when = date.fromisoformat(f"{day[:4]}-{day[4:6]}-{day[6:8]}")
    except ValueError as exc:
        raise ValueError("historical_date_invalid") from exc
    if when.year != 2026 or when.month not in ((8, 9) if training else (10,)):
        raise ValueError("historic_training_october_leak_or_holdout_date")
    roster = r.get("historical_boat_to_registration")
    finish = r.get("historical_boat_finish_6")
    if (type(roster) is not tuple or len(roster) != 6
            or any(type(x) is not str or len(x) != 4 or not x.isdigit()
                   for x in roster)
            or len(set(roster)) != 6):
        raise ValueError("historical_six_unique_registration_roster_required")
    if (type(finish) is not tuple or len(finish) != 6
            or any(type(v) is not int for v in finish)
            or set(finish) != set(BOATS)):
        raise ValueError("historical_six_boat_finish_order_invalid")
    # Only validation after the predictor has run on the six-boat roster.
    course_finish = r.get("actual_course_finish")
    if (type(course_finish) is not tuple or len(course_finish) != 6
            or set(course_finish) != set(BOATS)):
        raise ValueError("historical_real_course_finish_invalid")
    venue = r.get("venue")
    if type(venue) is not str or len(venue) != 2 or not venue.isdigit() or not 1 <= int(venue) <= 24:
        raise ValueError("historical_venue_invalid")
    return day, roster, finish[:3]


def fit_aug_sep(records):
    if type(records) is not list or len(records) == 0:
        raise ValueError("train_records_required")
    head = Counter()
    joint = Counter()
    for r in records:
        _, _, ticket = _validate_record(r, training=True)
        head[ticket[0]] += 1
        joint[ticket] += 1
    n = len(records)
    prior_head = {
        b: (head[b] + BASE_HEAD_PRIOR_PER_BOAT) /
        (n + len(BOATS) * BASE_HEAD_PRIOR_PER_BOAT)
        for b in BOATS
    }
    joint_conditional = {
        ticket: (joint[ticket] + TAIL_PRIOR_PER_TICKET) /
        (head[ticket[0]] + 20 * TAIL_PRIOR_PER_TICKET)
        for ticket in TICKETS
    }
    assert all(math.isclose(
        sum(joint_conditional[t] for t in TICKETS if t[0] == b), 1,
        abs_tol=1e-12) for b in BOATS)
    racer_stats = defaultdict(lambda: {"starts": 0, "wins": 0, "expected_wins": 0.,
                                      "training_win_methods": Counter()})
    for r in records:
        _, roster, ticket = _validate_record(r, training=True)
        for b in BOATS:
            racer = racer_stats[roster[b-1]]
            racer["starts"] += 1
            racer["wins"] += int(ticket[0] == b)
            racer["expected_wins"] += prior_head[b]
        winning_reg = roster[ticket[0]-1]
        racer_stats[winning_reg]["training_win_methods"][r["group"]] += 1
    if sum(x["wins"] for x in racer_stats.values()) != n:
        raise ValueError("training_winners_not_conserved")
    if sum(x["starts"] for x in racer_stats.values()) != n * 6:
        raise ValueError("training_athlete_starts_not_conserved")
    athlete = {
        reg: {
            "starts": data["starts"],
            "wins": data["wins"],
            "expected_wins": data["expected_wins"],
            "style_wins_training_only": dict(data["training_win_methods"]),
            # Defined by no result labels other than Aug/Sep completed races.
            "head_multiplier": (data["wins"] + ATHLETE_EXPECTED_WIN_PRIOR) /
                               (data["expected_wins"] + ATHLETE_EXPECTED_WIN_PRIOR)
        } for reg, data in racer_stats.items()
    }
    fingerprint = sha256(json.dumps({
        "n": n,
        "head": {str(b): head[b] for b in BOATS},
        "tails": {"-".join(map(str, t)): joint[t] for t in TICKETS},
        "racer": {reg: [v["starts"], v["wins"], round(v["expected_wins"], 8)]
                  for reg, v in sorted(athlete.items())},
        "pseudo": [BASE_HEAD_PRIOR_PER_BOAT,
                   TAIL_PRIOR_PER_TICKET, ATHLETE_EXPECTED_WIN_PRIOR],
    }, separators=(",", ":"), sort_keys=True).encode()).hexdigest()
    return {
        "prior_head": prior_head,
        "conditional_tail_given_head": joint_conditional,
        "athlete": athlete,
        "train_n": n,
        "train_athlete_count": len(athlete),
        "train_athlete_start_count": n * 6,
        "frozen_training_sha256": fingerprint,
        "training_october_outcomes_consumed": False,
        "actual_target_course_used": False,
    }


def predict_from_boat_roster(fit, roster):
    """Only six BOAT-ORDER registration IDs are accepted (no method/entry)."""
    if (type(roster) is not tuple or len(roster) != 6
            or any(type(x) is not str or len(x) != 4 or not x.isdigit()
                   for x in roster) or len(set(roster)) != 6):
        raise ValueError("boat_order_six_registrations_required")
    base_head = fit["prior_head"]
    weighted = {}
    known = 0
    for b in BOATS:
        row = fit["athlete"].get(roster[b-1])
        if row is not None:
            known += 1
        weight = row["head_multiplier"] if row else 1.0
        weighted[b] = base_head[b] * weight
    denom = math.fsum(weighted.values())
    if not denom or not math.isfinite(denom):
        raise ValueError("racer_head_denominator_invalid")
    adjusted_head = {b: weighted[b] / denom for b in BOATS}
    base_board = {t: base_head[t[0]] * fit["conditional_tail_given_head"][t]
                  for t in TICKETS}
    racer_board = {t: adjusted_head[t[0]] * fit["conditional_tail_given_head"][t]
                   for t in TICKETS}
    if any(not math.isclose(sum(board.values()), 1, abs_tol=1e-10)
           or min(board.values()) <= 0 for board in (base_board, racer_board)):
        raise ValueError("forecast_board_invalid")
    return {
        "global_boat_baseline": base_board,
        "racer_prior_head_only": racer_board,
        "global_head": dict(base_head),
        "racer_head": adjusted_head,
        "racer_coverage": known,
        "input_fields": ("boat_number", "registration_id"),
        "current_race_outcome_used": False,
        "current_race_actual_course_used": False,
        "current_race_winning_method_used": False,
        "historical_athlete_style_used_in_score": False,
        "trained_with_october": False,
        "qualified_as_real_T12_forecast": False,
    }


def _stats():
    return {"n": 0, "log": 0., "brier": 0., "head_log": 0., "head_brier": 0.,
            **{f"top{k}": 0 for k in TOPS}}


def _final_stats(v):
    n = v["n"]
    if n <= 0:
        return None
    return {
        "n": n, "logloss": round(v["log"] / n, 7),
        "brier120": round(v["brier"] / n, 7),
        "head_logloss": round(v["head_log"] / n, 7),
        "head_brier6": round(v["head_brier"] / n, 7),
        **{f"top{k}_pct": round(100*v[f"top{k}"]/n, 4) for k in TOPS},
    }


def score_october_holdout(fit, records, *, expected_oct_n=None):
    if type(records) is not list or not records:
        raise ValueError("october_rows_required")
    if expected_oct_n is not None and len(records) != expected_oct_n:
        raise ValueError("october_holdout_size_mismatch")
    modelnames = ("global_boat_baseline", "racer_prior_head_only")
    totals = {name: _stats() for name in modelnames}
    gainloss = {k: Counter() for k in TOPS}
    coverage = Counter()
    days = defaultdict(lambda: {"n": 0, "delta_log": 0.})
    for record in records:
        if type(record) is not dict:
            raise ValueError("historical_row_required")
        # Strictly result-blind prediction: only the preregistration roster,
        # NOT the record dictionary, is passed to the scoring emitter.
        before_result = predict_from_boat_roster(
            fit, record.get("historical_boat_to_registration"))
        day, _, ticket = _validate_record(record, training=False)
        coverage[before_result["racer_coverage"]] += 1
        candidate_hit = {}
        individual_losses = {}
        for name in modelnames:
            board = before_result[name]
            hvec = (before_result["global_head"] if name == "global_boat_baseline"
                    else before_result["racer_head"])
            log = -math.log(board[ticket])
            brier = 1 - 2*board[ticket] + math.fsum(x*x for x in board.values())
            headloss = -math.log(hvec[ticket[0]])
            hbrier = 1 - 2*hvec[ticket[0]] + math.fsum(x*x for x in hvec.values())
            top = sorted(TICKETS, key=lambda t: (-board[t], t))
            bucket = totals[name]
            bucket["n"] += 1
            bucket["log"] += log
            bucket["brier"] += brier
            bucket["head_log"] += headloss
            bucket["head_brier"] += hbrier
            candidate_hit[name] = {}
            for k in TOPS:
                flag = ticket in top[:k]
                bucket[f"top{k}"] += int(flag)
                candidate_hit[name][k] = flag
            individual_losses[name] = log
        for k in TOPS:
            a = candidate_hit[modelnames[0]][k]
            b = candidate_hit[modelnames[1]][k]
            key = "both" if a and b else "gained" if b else "lost" if a else "neither"
            gainloss[k][key] += 1
        days[day]["n"] += 1
        days[day]["delta_log"] += individual_losses[modelnames[1]] - individual_losses[modelnames[0]]
    if expected_oct_n == 4382 and len(days) != 31:
        raise ValueError("october_day_count_mismatch")
    daykeys = sorted(days)
    rng = random.Random(BOOTSTRAP_SEED)
    bootstrap = []
    for _ in range(BOOTSTRAP_REPS):
        sampled = [daykeys[rng.randrange(len(daykeys))] for _ in daykeys]
        denom = sum(days[d]["n"] for d in sampled)
        bootstrap.append(sum(days[d]["delta_log"] for d in sampled) / denom)
    bootstrap.sort()
    confidence = [
        round(bootstrap[int(.025*(BOOTSTRAP_REPS-1))], 7),
        round(bootstrap[int(.975*(BOOTSTRAP_REPS-1))], 7)]
    summaries = {name: _final_stats(value) for name, value in totals.items()}
    delta = (totals[modelnames[1]]["log"] - totals[modelnames[0]]["log"]) / len(records)
    blocked = {
        "top5_nonregression": totals[modelnames[1]]["top5"] >= totals[modelnames[0]]["top5"],
        "top10_nonregression": totals[modelnames[1]]["top10"] >= totals[modelnames[0]]["top10"],
        "logloss_upper95_below_zero": confidence[1] < 0,
        "official_predeadline_roster_and_feature_receipt": False,
        "independent_remote_first_add": False,
        "prospective_300_plus_300": False,
        "explicit_user_switch_approval": False,
    }
    return {
        "study_id": STUDY,
        "historical_training": "2026-08-01/2026-09-30",
        "historical_holdout": "2026-10-01/2026-10-31",
        "train_n": fit["train_n"],
        "october_holdout_n": len(records),
        "train_racer_count": fit["train_athlete_count"],
        "train_athlete_starts": fit["train_athlete_start_count"],
        "train_only_sha256": fit["frozen_training_sha256"],
        "predicted_ticket_type": "boat_number_based_120_trifecta_not_actual_course",
        "pre_race_knowable_fields_only": ["boat_number", "registration_id", "prior_aug_sep_results"],
        "postrace_source_receipt_not_predeadline_certified": True,
        "racer_training_coverage_histogram": dict(sorted(coverage.items())),
        "models": summaries,
        "topk_gained_lost": {k: dict(gainloss[k]) for k in TOPS},
        "logloss_delta_racer_minus_baseline": round(delta, 7),
        "paired_day_bootstrap_logloss_delta95": confidence,
        "adoption_guard": {
            "checks": blocked,
            "all_pass": all(blocked.values()),
            "model_switch_allowed": False,
        },
        "winning_methods_used_only_for_training_style_audit_not_scoring": True,
        "no_future_october_labels_as_features": True,
        "source_is_historical_postrace_K_not_independent_T12": True,
        "suppress_prospective_accuracy_claim": True,
        "production_changed": False,
        "promotion_allowed": False,
    }


def replay_from_K92(source_zip):
    from scenario_official_K_attack_benefit_holdout import analyze_official_K_92day
    original = analyze_official_K_92day(source_zip, return_internal_records=True)
    x = original["internal_retrospective_records_only"]
    if (original["train_n"], original["historical_october_n"]) != (8919, 4382):
        raise ValueError("frozen_K92_cohort_changed")
    trained = fit_aug_sep(x["train_aug_sep"])
    result = score_october_holdout(trained, x["historical_holdout_oct"], expected_oct_n=4382)
    result["official_K_source_sha256"] = original["source_zip_sha256"]
    result["K_92days_original_SHA_checked"] = original["official_K_days_verified"] == 92
    return result

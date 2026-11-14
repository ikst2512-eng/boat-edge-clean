"""Historical holdout of three PREDECLARED conditional 2nd/3rd alternatives.

This adapter reuses exact #1710 K92 extraction and the previously accepted
racer-head prior. August -> September PILOT selection; August+September ->
October HISTORICAL CONFIRMATION. October has been analyzed by other #1710
studies: it is NOT a genuinely untouched prospective holdout.

Prediction APIs receive six registration IDs IN BOAT ORDER, not the result,
actual entry course, winner method, race-time weather, or future receipt.
The trained latent winning-method mixture is NOT an observed attacking attempt
and does not certify 2C walls or beneficiaries. Research only; never deploy.
"""
from collections import Counter, defaultdict
from datetime import date
from hashlib import sha256
from itertools import permutations
import json
import math
import random

from scenario_racer_roster_october_holdout import (
    fit_aug_sep as fit_existing_head, predict_from_boat_roster,
    _validate_record as validate_historical,
    TICKETS, BOATS, TOPS,
)

STUDY_ID = "HISTORICAL_ONLY_K92_TAIL_STYLE_COMPARISON_V1"
METHODS = ("逃げ", "差し", "まくり", "まくり差し", "抜き", "恵まれ")
ALTERNATIVES = (
    "head_only",
    "head_athlete_tail",
    "head_latent_style",
    "head_style_and_athlete_tail",
)
ALL_MODELS = ("global_boat",) + ALTERNATIVES
STYLE_PRIOR_WINS = 20
WORLD_TAIL_PRIOR_RACES = 30
POSITION_PRIOR_EXPECTED = 10
BOOTSTRAP_SEED = 171021
BOOTSTRAP_N = 1000
METRICS = ("top1", "top3", "top5", "top10")


def _month(r):
    day = r.get("day")
    if type(day) is not str or len(day) != 8 or not day.isdigit():
        raise ValueError("invalid_historical_day")
    try:
        d = date.fromisoformat(day[:4]+"-"+day[4:6]+"-"+day[6:8])
    except ValueError as exc:
        raise ValueError("invalid_historical_date") from exc
    if d.year != 2026 or d.month not in (8, 9, 10):
        raise ValueError("historical_92day_period_required")
    return d.month


def _clean_record(r, allowed_months):
    if type(r) is not dict or _month(r) not in allowed_months:
        raise ValueError("period_leakage_or_wrong_holdout_window")
    # Borrow the frozen historical roster/race membership contract. It
    # validates actual-courses only as POSTRACE outcome labels.
    day, roster, ticket = validate_historical(
        r, training=(_month(r) in (8, 9)))
    method = r.get("method")
    if method not in METHODS:
        raise ValueError("winner_method_not_in_official_K_types")
    if r.get("group") is None:
        raise ValueError("postrace_group_missing")
    return day, roster, ticket, method


def fit_training(records, allowed_months):
    """No target-period records may enter fitted statistics; fail closed."""
    allowed_months = tuple(allowed_months)
    if allowed_months not in ((8,), (8, 9)):
        raise ValueError("only_aug_or_aug_sep_training_window")
    if type(records) is not list or not records:
        raise ValueError("training_nonempty_required")
    for r in records:
        _clean_record(r, allowed_months)
    head_fit = fit_existing_head(records)
    base_board = predict_from_boat_roster(
        head_fit, tuple(str(i) for i in range(9001, 9007)))["global_boat_baseline"]
    second_base = {b: sum(base_board[t] for t in TICKETS if t[1] == b)
                   for b in BOATS}
    third_base = {b: sum(base_board[t] for t in TICKETS if t[2] == b)
                  for b in BOATS}
    athlete_positions = defaultdict(lambda: [0, 0, 0, 0., 0.])
    by_head_method = Counter()
    by_head_method_pair = Counter()
    by_athlete_method = defaultdict(Counter)
    total_athlete_wins = Counter()
    methods_by_head = defaultdict(Counter)
    for r in records:
        _, roster, ticket, method = _clean_record(r, allowed_months)
        h, s, t = ticket
        methods_by_head[h][method] += 1
        by_head_method[(h, method)] += 1
        by_head_method_pair[(h, method, s, t)] += 1
        by_athlete_method[roster[h-1]][method] += 1
        total_athlete_wins[roster[h-1]] += 1
        for b, reg in enumerate(roster, 1):
            item = athlete_positions[reg]
            item[0] += 1
            item[1] += int(b == s)
            item[2] += int(b == t)
            item[3] += second_base[b]
            item[4] += third_base[b]
    # Independent roles: athlete position effects are shrunk toward no change.
    multipliers = {
        reg: (
            (value[1] + POSITION_PRIOR_EXPECTED) /
            (value[3] + POSITION_PRIOR_EXPECTED),
            (value[2] + POSITION_PRIOR_EXPECTED) /
            (value[4] + POSITION_PRIOR_EXPECTED)
        ) for reg, value in athlete_positions.items()
    }
    head_n = Counter(r["historical_boat_finish_6"][0] for r in records)
    world_p = {
        h: {
            m: (methods_by_head[h][m] + 1)/(head_n[h] + len(METHODS))
            for m in METHODS
        } for h in BOATS
    }
    # CONDITIONAL on a BOAT being 1st, not conditioned on the unknown
    # target's actual winning method. Each trained world has a normalized
    # 20-pair distribution; sparse worlds back off to frozen P(pair|head).
    tail_by_world = {}
    for h in BOATS:
        for m in METHODS:
            n = by_head_method[(h, m)]
            world = {}
            for _, s, t in (x for x in TICKETS if x[0] == h):
                world[(s, t)] = (
                    by_head_method_pair[(h, m, s, t)] +
                    WORLD_TAIL_PRIOR_RACES *
                    head_fit["conditional_tail_given_head"][(h, s, t)]
                )/(n + WORLD_TAIL_PRIOR_RACES)
            if not math.isclose(sum(world.values()), 1, abs_tol=1e-11):
                raise ValueError("world_tail_probability_mass_changed")
            tail_by_world[(h, m)] = world
    # All style estimates come from PREVIOUS winning races; no target method.
    # Do not store per-head style in a flattened reg-only dict. A racer
    # racing at a different DRAW needs a different world prior.
    athlete_method_count = {reg: dict(v) for reg,v in by_athlete_method.items()}
    fingerprint = sha256(json.dumps({
        "head_training_sha": head_fit["frozen_training_sha256"],
        "train_n": len(records),
        "allowed_months": list(allowed_months),
        "methods_by_head": {str(h): dict(v) for h,v in methods_by_head.items()},
        "head_method_pair": {
            "-".join(map(str,k)): count
            for k,count in sorted(by_head_method_pair.items())
        },
        "athlete_positions": {reg: values for reg,values in sorted(athlete_positions.items())},
        "athlete_method": {reg: dict(v) for reg,v in sorted(by_athlete_method.items())},
        "fixed_hypotheses": [STYLE_PRIOR_WINS,WORLD_TAIL_PRIOR_RACES,
                             POSITION_PRIOR_EXPECTED]
    }, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return {
        "head": head_fit, "tail_by_world": tail_by_world,
        "method_p_by_head": world_p, "athlete_method": athlete_method_count,
        "athlete_wins": dict(total_athlete_wins),
        "tail_multipliers": multipliers, "n":len(records),
        "training_window": allowed_months,
        "train_fingerprint_sha256":fingerprint,
        "method_target_consumed":False, "target_result_used_in_fitting":False,
        "target_actual_course_consumed":False,
    }


def predict_120(fit, registration_ids):
    """Six registered IDs in 1..6 BOAT order; no race/outcome argument."""
    old = predict_from_boat_roster(fit["head"], registration_ids)
    base = old["global_boat_baseline"]
    head = old["racer_head"]
    head_only = old["racer_prior_head_only"]
    style_tail = {}
    ability_tail = {}
    both_tail = {}
    for h in BOATS:
        winner_reg = registration_ids[h-1]
        training_wins = fit["athlete_wins"].get(winner_reg, 0)
        style_count = fit["athlete_method"].get(winner_reg, {})
        mix = {
            method: (style_count.get(method,0) + STYLE_PRIOR_WINS *
                     fit["method_p_by_head"][h][method]) /
                    (training_wins + STYLE_PRIOR_WINS)
            for method in METHODS
        }
        if not math.isclose(sum(mix.values()),1,abs_tol=1e-11):
            raise ValueError("winner_style_mass_changed")
        raw_ability = {}
        raw_style = {}
        raw_both = {}
        for _, second, third in (row for row in TICKETS if row[0] == h):
            b2, b3 = registration_ids[second-1], registration_ids[third-1]
            m2 = fit["tail_multipliers"].get(b2,(1.,1.))[0]
            m3 = fit["tail_multipliers"].get(b3,(1.,1.))[1]
            base_conditional = fit["head"]["conditional_tail_given_head"][(h,second,third)]
            style_conditional = math.fsum(
                mix[method] * fit["tail_by_world"][(h,method)][(second,third)]
                for method in METHODS)
            tail = (second,third)
            raw_ability[tail] = base_conditional*m2*m3
            raw_style[tail] = style_conditional
            raw_both[tail] = style_conditional*m2*m3
        for raw,dest in ((raw_ability,ability_tail),
                         (raw_style,style_tail),(raw_both,both_tail)):
            total = math.fsum(raw.values())
            if total <= 0 or not math.isfinite(total):
                raise ValueError("conditional_tail_denominator_invalid")
            for (second,third),score in raw.items():
                dest[(h,second,third)] = head[h] * score / total
    models = {
        "global_boat":base,
        "head_only":head_only,
        "head_athlete_tail":ability_tail,
        "head_latent_style":style_tail,
        "head_style_and_athlete_tail":both_tail,
    }
    for name,board in models.items():
        if (len(board)!=120 or min(board.values())<=0 or
                not math.isclose(math.fsum(board.values()),1,abs_tol=1e-10)):
            raise ValueError("invalid_120_board:"+name)
    return {
        "boards":models, "head":head,
        "racer_coverage":old["racer_coverage"],
        "predictor_consumed":("boat_order_registration_ids", "historical_train_only"),
        "target_method_consumed":False,
        "target_result_consumed":False,
        "target_actual_course_consumed":False,
        "calibration_confirmed":False,
    }


def _empty():
    return {"n":0,"logloss":0.,"tail_logloss":0.,"brier120":0.,
            **{f"top{k}":0 for k in TOPS}}


def _rounded(v):
    n=v["n"]
    if n==0:
        return None
    return {
        "n":n,
        "logloss":round(v["logloss"]/n,7),
        "tail_logloss":round(v["tail_logloss"]/n,7),
        "brier120":round(v["brier120"]/n,7),
        **{f"top{k}_pct":round(v[f"top{k}"]/n*100,4) for k in TOPS},
    }


def evaluate(fit, records, test_month, *, strata=False):
    if test_month not in (9,10) or type(records) is not list or not records:
        raise ValueError("invalid_holdout_period_or_empty")
    totals = {name:_empty() for name in ALL_MODELS}
    strata_summary = defaultdict(lambda: {name:_empty() for name in ALL_MODELS})
    compare = {name:{k:Counter() for k in TOPS} for name in ALTERNATIVES[1:]}
    by_day = defaultdict(lambda: {name:{"n":0,"log":0.,"tail":0.} for name in ALTERNATIVES[1:]})
    days = Counter()
    coverage = Counter()
    # This loop never passes a result row to the predictor.
    for record in records:
        if type(record) is not dict or _month(record)!=test_month:
            raise ValueError("holdout_outcome_period_leakage")
        forecast=predict_120(fit,record.get("historical_boat_to_registration"))
        day,roster,ticket,method=_clean_record(record,(test_month,))
        head=ticket[0]
        days[day]+=1
        coverage[forecast["racer_coverage"]]+=1
        row_hits={}
        row_losses={}
        for name,board in forecast["boards"].items():
            p=board[ticket]
            head_p=math.fsum(board[k] for k in TICKETS if k[0]==head)
            log=-math.log(p)
            tail=-math.log(p/head_p)
            bs=1-2*p+math.fsum(x*x for x in board.values())
            ranked=sorted(TICKETS,key=lambda t:(-board[t],t))
            row_hits[name]={}
            for bag in (totals[name],strata_summary[method][name]):
                bag["n"]+=1
                bag["logloss"]+=log
                bag["tail_logloss"]+=tail
                bag["brier120"]+=bs
                for k in TOPS:
                    flag=ticket in ranked[:k]
                    bag[f"top{k}"]+=int(flag)
                    row_hits[name][k]=flag
            row_losses[name]=(log,tail)
        for name in ALTERNATIVES[1:]:
            by_day[day][name]["n"]+=1
            by_day[day][name]["log"]+=row_losses[name][0]-row_losses["head_only"][0]
            by_day[day][name]["tail"]+=row_losses[name][1]-row_losses["head_only"][1]
            for k in TOPS:
                a,b=row_hits["head_only"][k],row_hits[name][k]
                case="both" if a and b else "gained" if b else "lost" if a else "neither"
                compare[name][k][case]+=1
    sorted_days=sorted(days)
    if test_month==10 and len(sorted_days)!=31:
        raise ValueError("october_day_universe_changed")
    if test_month==9 and len(sorted_days)!=30:
        raise ValueError("september_day_universe_changed")
    summary={name:_rounded(row) for name,row in totals.items()}
    intervals={}
    for index,name in enumerate(ALTERNATIVES[1:]):
        rng=random.Random(BOOTSTRAP_SEED+index)
        sims={"log":[],"tail":[]}
        for _ in range(BOOTSTRAP_N):
            sample=[sorted_days[rng.randrange(len(sorted_days))]
                    for __ in sorted_days]
            denom=sum(by_day[day][name]["n"] for day in sample)
            for target in sims:
                sims[target].append(
                    sum(by_day[day][name][target] for day in sample)/denom)
        intervals[name]={
            field:[round(vals[int(.025*(BOOTSTRAP_N-1))],7),
                   round(vals[int(.975*(BOOTSTRAP_N-1))],7)]
            for field,vals in ((key, sorted(v)) for key,v in sims.items())
        }
    out={
        "prediction_month":test_month,
        "n":len(records),
        "distinct_days":len(sorted_days),
        "models":summary,
        "paired_vs_head_only":{
            name:{
                "delta_logloss":round(summary[name]["logloss"]-summary["head_only"]["logloss"],7),
                "delta_tail_logloss":round(summary[name]["tail_logloss"]-summary["head_only"]["tail_logloss"],7),
                "day_block_bootstrap95":intervals[name],
                "topk_gained_lost":{
                    f"top{k}":dict(compare[name][k]) for k in TOPS
                }
            } for name in ALTERNATIVES[1:]
        },
        "racer_coverage":dict(sorted(coverage.items())),
        "winner_method_postrace_diagnostic_only":
            ({method:{name:_rounded(m[name]) for name in ALL_MODELS}
               for method,m in sorted(strata_summary.items())} if strata else None),
        "method_used_at_prediction":False,
        "target_actual_course_used_at_prediction":False,
        "outcomes_consumed_before_forecast":False,
    }
    return out


def select_from_september(report):
    if report.get("prediction_month") != 9:
        raise ValueError("selection_must_be_september_only")
    base=report["models"]["head_only"]
    statuses={}
    for name in ALTERNATIVES[1:]:
        v=report["models"][name]
        paired=report["paired_vs_head_only"][name]
        checks={
            "top5_nonregression":v["top5_pct"]>=base["top5_pct"],
            "top10_nonregression":v["top10_pct"]>=base["top10_pct"],
            "joint_tail_logloss_improved":v["tail_logloss"]<base["tail_logloss"],
            "paired_tail_CI_upper_below_zero":
                paired["day_block_bootstrap95"]["tail"][1]<0,
        }
        statuses[name]={"checks":checks,"eligible":all(checks.values())}
    qualified=[name for name in ALTERNATIVES[1:] if statuses[name]["eligible"]]
    chosen=(min(qualified,key=lambda name:
                (report["models"][name]["tail_logloss"],name))
            if qualified else None)
    return {
        "pilot_month":"2026-09",
        "chosen_candidate":chosen,
        "rejected_or_inconclusive":{
            name:statuses[name] for name in ALTERNATIVES[1:]
        },
        "chosen_from_october":False,
        "criterion_predefined_before_testing_october_in_this_run":True,
        "formal_preregistration_before_historical_October":False,
    }


def run_official_K92_study(archive):
    from scenario_official_K_attack_benefit_holdout import analyze_official_K_92day
    x=analyze_official_K_92day(archive,return_internal_records=True)
    rows=x["internal_retrospective_records_only"]
    train=rows["train_aug_sep"]
    august=[r for r in train if _month(r)==8]
    september=[r for r in train if _month(r)==9]
    october=rows["historical_holdout_oct"]
    if (len(train),len(october))!=(8919,4382):
        raise ValueError("official_K_frozen_cohort_drift")
    f_aug=fit_training(august,(8,))
    sept=evaluate(f_aug,september,9)
    decision=select_from_september(sept)
    f_aug_sep=fit_training(train,(8,9))
    oct_result=evaluate(f_aug_sep,october,10,strata=True)
    selected=decision["chosen_candidate"]
    selected_oct=(oct_result["paired_vs_head_only"][selected] if selected else None)
    selected_metrics=(oct_result["models"][selected] if selected else None)
    head=oct_result["models"]["head_only"]
    if selected is None:
        historical_decision="NO_TAIL_MODEL_QUALIFIED_IN_SEPTEMBER_PILOT"
    else:
        tests={
            "top1_nonregression":selected_metrics["top1_pct"]>=head["top1_pct"],
            "top3_nonregression":selected_metrics["top3_pct"]>=head["top3_pct"],
            "top5_nonregression":selected_metrics["top5_pct"]>=head["top5_pct"],
            "top10_nonregression":selected_metrics["top10_pct"]>=head["top10_pct"],
            "full_logloss_CI_upper_below_zero":
                selected_oct["day_block_bootstrap95"]["log"][1]<0,
            "tail_logloss_CI_upper_below_zero":
                selected_oct["day_block_bootstrap95"]["tail"][1]<0,
        }
        historical_decision=(
            "HISTORICAL_ONLY_TAIL_CHALLENGER_QUALIFIED_FOR_FUTURE_SHADOW"
            if all(tests.values())
            else "TAIL_CHALLENGER_FAILED_OCTOBER_NONREGRESSION_OR_STABILITY")
    return {
        "study_id":STUDY_ID,
        "official_zip_sha256":x["source_zip_sha256"],
        "verified_days":x["official_K_days_verified"],
        "raw_races":x["original_raw_races"],
        "six_clean":x["clean_six_finishers"],
        "august_training_n":len(august),
        "september_pilot_n":len(september),
        "aug_sep_training_n":len(train),
        "october_historical_confirmation_n":len(october),
        "august_fit_sha256":f_aug["train_fingerprint_sha256"],
        "aug_sep_fit_sha256":f_aug_sep["train_fingerprint_sha256"],
        "september_pilot":sept,
        "selection":decision,
        "october_historical_confirmation":oct_result,
        "selected_october_paired":selected_oct,
        "historical_decision":historical_decision,
        "historical_october_previously_analyzed_by_other_studies":True,
        "postrace_eligibility_and_roster_not_independently_T12_proven":True,
        "actual_race_entry_only_postrace_historical":True,
        "attack_attempts_or_wall_events_directly_observed":False,
        "target_winning_method_in_predictor":False,
        "head_priors_production_approved":False,
        "prospective_300_plus_300_validated":False,
        "same_race_legacy_V127_V133_head_to_head":False,
        "automatic_model_switch_authorized":False,
        "production_changed":False,
        "promotion_allowed":False,
    }

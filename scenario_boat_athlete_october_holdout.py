"""Retrospective official K92 BOAT-ticket study: venue vs pre-known player identity.

Strict Aug-Sep training -> October historical holdout. For each October
evaluation race, predictor sees ONLY venue and boat-ordered athlete IDs, not
finish position, actual course, winning method, weather or odds. Those IDs
originate in AFTER-RACE official K; pre-deadline roster identity is NOT
independently certified. Finisher eligibility is itself post-event, hence this
is research, not a prospective accuracy result or V133 comparison.

Does not rewrite/preregister existing #1692/#1698/#1710 models or any
original race/prediction. Existing frozen K parser is imported in CI by SHA.
"""
from collections import Counter, defaultdict
from datetime import date, timedelta
from hashlib import sha256
from itertools import permutations
from math import exp, fsum, log, isclose
from pathlib import Path
from zipfile import ZipFile
import json
import random
import re

from scenario_official_K_attack_benefit_holdout import _record

ID="RETROSPECTIVE_ONLY_K92_BOAT_ROSTER_ATHLETE_OCT2026_V1"
K_SHA="c668f545bae54f8148616315e307ed2a2b04a77a0cb8abf88bf3ea078749ce8e"
TICKETS=tuple(permutations(range(1,7),3))
TOPS=(1,3,5,10)
VENUE_PSEUDO_N=120
ATHLETE_SHRINK_N=15
ATHLETE_POSITION_SHIFTS=(4.0,2.0,1.0)
BOOTSTRAP_SEED=1710
BOOTSTRAP_REPS=1000
REG=re.compile(r"\d{4}\Z")
CANONICAL_COUNTS=(14249,13815,13301,8919,4382)


def _validate(row, is_training):
    if type(row) is not dict or set(row)!={"day","venue","roster","ticket"}:
        raise ValueError("boat_study_record_shape")
    day=row["day"]
    if type(day) is not str or not re.fullmatch(r"2026(?:08|09|10)\d{2}",day):
        raise ValueError("boat_study_period")
    try:
        d=date.fromisoformat(day[:4]+"-"+day[4:6]+"-"+day[6:8])
    except ValueError as exc:
        raise ValueError("boat_study_calendar") from exc
    if (is_training and d.month not in (8,9)) or (not is_training and d.month!=10):
        raise ValueError("boat_study_label_split")
    if (type(row["venue"]) is not str or not re.fullmatch("0[1-9]|1[0-9]|2[0-4]",row["venue"])
            or type(row["roster"]) is not tuple or len(row["roster"])!=6
            or len(set(row["roster"]))!=6 or
            any(type(a) is not str or not REG.fullmatch(a) for a in row["roster"])
            or type(row["ticket"]) is not tuple or row["ticket"] not in TICKETS):
        raise ValueError("boat_study_roster_ticket")
    return row


def read_pinned_K(zipfile):
    """Full byte evidence: verify SHA of 92 raw and decompressed daily files."""
    from research_official_k_one_day_compare import RACE, parse_k, unpack_lha
    from research_official_k_c2_escape_conditional_92day import (
        verify_original_zip, race_outcome)
    source=Path(zipfile)
    if verify_original_zip(source)!=K_SHA:
        raise ValueError("boat_K_zip_SHA_drift")
    raw_count=pair_count=clean_count=0
    allrows={"train":[],"historical_october":[]}
    daily=[]
    dates=[(date(2026,8,1)+timedelta(days=i)).strftime("%Y%m%d") for i in range(92)]
    with ZipFile(source) as z:
        if z.testzip() is not None or len(z.namelist())!=len(set(z.namelist())):
            raise ValueError("boat_K_zip_archive_corrupt")
        manifest=json.loads(z.read("official_k_full_92day_reconciliation.json"))
        rows=manifest.get("results",[])
        if (manifest.get("study_period")!="2026-08-01/2026-10-31"
                or len(rows)!=92 or len({x.get("day") for x in rows})!=92):
            raise ValueError("boat_K_92day_manifest_incomplete")
        by_day={x["day"]:x for x in rows}
        if set(by_day)!=set(dates):
            raise ValueError("boat_K_92day_manifest_day_drift")
        for day in dates:
            original=z.read("official_k_full_92_raw/k"+day[2:]+".lzh")
            osh=sha256(original).hexdigest()
            if osh!=by_day[day]["official_K_sha256"]:
                raise ValueError("boat_K_raw_SHA_mismatch")
            plain=unpack_lha(original,day=day)
            psh=sha256(plain).hexdigest()
            if psh!=by_day[day]["decoded_sha256"]:
                raise ValueError("boat_K_plain_SHA_mismatch")
            k_text=plain.decode("cp932")
            n=sum(bool(RACE.match(line)) for line in k_text.splitlines())
            races=parse_k(k_text,day=day,expected_races=n,allow_unsettled=True)
            if len(races)!=by_day[day]["official_K_races"]:
                raise ValueError("boat_K_day_race_count")
            raw_count+=len(races)
            daily.append((day,osh,psh))
            period="train" if day[4:6] in ("08","09") else "historical_october"
            for race in races.values():
                if race_outcome(race) is None:
                    continue
                pair_count+=1
                classified=_record(race)
                if classified is None:
                    continue
                clean_count+=1
                entries=race["entries"]
                if ({e.get("boat") for e in entries}!=set(range(1,7))
                        or {e.get("status") for e in entries}!=
                        {f"{n:02d}" for n in range(1,7)}):
                    raise ValueError("boat_K_six_finishers_drift")
                ordered=sorted(entries,key=lambda e:e["boat"])
                roster=tuple(e["athlete_registration"] for e in ordered)
                by_place=sorted(entries,key=lambda e:e["status"])
                ticket=tuple(e["boat"] for e in by_place[:3])
                row={"day":day,"venue":race["venue"],"roster":roster,"ticket":ticket}
                _validate(row,period=="train")
                allrows[period].append(row)
    actual=(raw_count,pair_count,clean_count,len(allrows["train"]),
            len(allrows["historical_october"]))
    if actual!=CANONICAL_COUNTS:
        raise ValueError("boat_K_cohort_invariant:"+str(actual))
    return allrows,{"zip_sha256":K_SHA,"all_cohort_counts":actual,"verified_days":92,
        "daily_sha_fingerprint":sha256(json.dumps(daily,separators=(",",":")).encode()).hexdigest()}


def fit_training(records):
    if type(records) is not list or not records:
        raise ValueError("boat_train_nonempty")
    global_ticket=Counter()
    venue_ticket=defaultdict(Counter)
    venue_n=Counter()
    player=defaultdict(lambda:[0,0.,0.,0.])
    boat_position=defaultdict(Counter)
    for r in records:
        _validate(r,True)
        ticket=r["ticket"]
        global_ticket[ticket]+=1
        venue_ticket[r["venue"]][ticket]+=1
        venue_n[r["venue"]]+=1
        for position,boat in enumerate(ticket,1):
            boat_position[boat][position]+=1
    n=len(records)
    baseline={
        t:(global_ticket[t]+1)/(n+len(TICKETS))
        for t in TICKETS
    }
    boat_p={
        b:{j:boat_position[b][j]/n for j in (1,2,3)}
        for b in range(1,7)
    }
    for r in records:
        pos={b:j for j,b in enumerate(r["ticket"],1)}
        for b,athlete in enumerate(r["roster"],1):
            st=player[athlete]
            st[0]+=1
            for j in (1,2,3):
                st[j]+=int(pos.get(b)==j)-boat_p[b][j]
    return {"n":n,"base":baseline,"venue_counts":venue_ticket,
            "venue_n":venue_n,
            "player_delta":{p:tuple(s[j]/(s[0]+ATHLETE_SHRINK_N)
                                    for j in (1,2,3))
                            for p,s in player.items()},
            "train_roster_shas":sha256(json.dumps([
                (v["day"],v["venue"],v["roster"],v["ticket"]) for v in records],
                separators=(",",":")).encode()).hexdigest(),
            "never_trained_on_october":True}


def predict_boat120(fit,venue,roster):
    """Prediction API cannot be passed actual result, course, ST, or method."""
    if (type(venue) is not str or not re.fullmatch("0[1-9]|1[0-9]|2[0-4]",venue)
            or type(roster) is not tuple or len(roster)!=6
            or any(type(p) is not str or not REG.fullmatch(p) for p in roster)
            or len(set(roster))!=6):
        raise ValueError("boat_pred_venue_and_ordered_six_roster_required")
    vn=fit["venue_n"][venue]
    vc=fit["venue_counts"][venue]
    base=fit["base"]
    venue_board={t:(vc[t]+VENUE_PSEUDO_N*base[t])/
                  (vn+VENUE_PSEUDO_N) for t in TICKETS}
    player_delta=fit["player_delta"]
    by_boat=[player_delta.get(p,(0.,0.,0.)) for p in roster]
    athlete_raw={
        t:venue_board[t]*exp(fsum(
            ATHLETE_POSITION_SHIFTS[i]*by_boat[t[i]-1][i]
            for i in range(3)))
        for t in TICKETS
    }
    total=fsum(athlete_raw.values())
    athlete={t:v/total for t,v in athlete_raw.items()}
    if (not isclose(fsum(venue_board.values()),1,abs_tol=1e-10)
            or not isclose(fsum(athlete.values()),1,abs_tol=1e-10)
            or min(athlete.values())<=0):
        raise ValueError("boat_model_mass_invalid")
    return {
        "global_direct":base,
        "venue_direct":venue_board,
        "venue_plus_athlete":athlete,
    }


def _stats():
    return {"n":0,"logloss_sum":0.,"brier_sum":0.,
            **{f"top{k}":0 for k in TOPS}}


def _report(x):
    n=x["n"]
    return {
        "n":n,
        "logloss":round(x["logloss_sum"]/n,7),
        "brier120":round(x["brier_sum"]/n,7),
        **{f"top{k}":x[f"top{k}"] for k in TOPS},
        **{f"top{k}_pct":round(100*x[f"top{k}"]/n,4) for k in TOPS},
    }


def evaluate_october(fit,records,require_n=None):
    if type(records) is not list or not records or (require_n is not None and len(records)!=require_n):
        raise ValueError("boat_holdout_nonempty_and_pinned_n")
    names=("global_direct","venue_direct","venue_plus_athlete")
    metrics={p:_stats() for p in names}
    paired={com:{k:{"gained":0,"lost":0,"both":0,"neither":0} for k in TOPS}
            for com in ("athlete_vs_venue","athlete_vs_global")}
    days=defaultdict(lambda:{"n":0,"delta_logloss":0.})
    day_keys=set()
    predicted_cache={}
    for row in records:
        _validate(row,False)
        day,venue,ticket=row["day"],row["venue"],row["ticket"]
        day_keys.add(day)
        key=(venue,row["roster"])
        if key not in predicted_cache:
            predicted_cache[key]=predict_boat120(fit,venue,row["roster"])
        boards=predicted_cache[key]
        hits={}
        ls={}
        for name in names:
            scores=boards[name]
            ranking=sorted(TICKETS,key=lambda t:(-scores[t],t))
            p=scores[ticket]
            logloss=-log(p)
            brier=1.-2*p+fsum(q*q for q in scores.values())
            hits[name]={k:ticket in ranking[:k] for k in TOPS}
            ls[name]=logloss
            stat=metrics[name]
            stat["n"]+=1
            stat["logloss_sum"]+=logloss
            stat["brier_sum"]+=brier
            for k in TOPS:
                stat[f"top{k}"]+=int(hits[name][k])
        d=days[day]
        d["n"]+=1
        d["delta_logloss"]+=ls["venue_plus_athlete"]-ls["venue_direct"]
        for name,base in (("athlete_vs_venue","venue_direct"),
                          ("athlete_vs_global","global_direct")):
            for k in TOPS:
                a=hits["venue_plus_athlete"][k]
                b=hits[base][k]
                status="both" if a and b else "gained" if a else "lost" if b else "neither"
                paired[name][k][status]+=1
    if require_n==4382 and len(day_keys)!=31:
        raise ValueError("boat_october_days_changed")
    rng=random.Random(BOOTSTRAP_SEED)
    ds=sorted(day_keys)
    samples=[]
    for _ in range(BOOTSTRAP_REPS):
        sample=[ds[rng.randrange(len(ds))] for _ in ds]
        total=sum(days[d]["n"] for d in sample)
        samples.append(sum(days[d]["delta_logloss"] for d in sample)/total)
    samples.sort()
    ci=[round(samples[int(.025*(BOOTSTRAP_REPS-1))],7),
        round(samples[int(.975*(BOOTSTRAP_REPS-1))],7)]
    results={name:_report(stat) for name,stat in metrics.items()}
    old=results["venue_direct"]
    new=results["venue_plus_athlete"]
    deltas={f"top{k}_count":new[f"top{k}"]-old[f"top{k}"] for k in TOPS}
    deltas.update({
        "logloss":round(new["logloss"]-old["logloss"],7),
        "brier120":round(new["brier120"]-old["brier120"],7),
    })
    gate={
        "historical_top5_nonregression":deltas["top5_count"]>=0,
        "historical_top10_nonregression":deltas["top10_count"]>=0,
        "historical_logloss_day_bootstrap_upper_below_zero":ci[1]<0,
        "true_predeadline_roster_source_certified":False,
        "postrace_six_finishers_selection_known_preahead":False,
        "300_plus_300_future_independent_verified":False,
        "model_user_switch_approved":False,
    }
    return {
        "study_id":ID,"train_n":fit["n"],"holdout_n":len(records),
        "trained_on_october_labels":False,
        "input_used_for_october_prediction":["venue_code","boat_number","athlete_registration"],
        "not_prediction_inputs":["target_finish","target_actual_course","target_winning_method","target_wind","target_payout"],
        "baseline_definition":"all_three_models_evaluated_same_boat123_tickets",
        "models":results,"athlete_vs_venue_delta":deltas,
        "athlete_vs_venue_logloss_delta_day_bootstrap_95":ci,
        "paired_topn":paired,
        "historical_findings_not_prospective_accuracy":True,
        "historical_clean_six_finishers_selected_after_result":True,
        "target_athlete_roster_obtained_from_postrace_K_not_predeadline_attested":True,
        "source_to_model_same_race_forward_attested":False,
        "adoption_checks":gate,
        "production_adoption_allowed":False,
        "new_historical_prediction_originals_written":False,
        "model_coefficients_changed":False,
        "formal":False,
    }


def run_official_K_boat_holdout(path):
    data,evidence=read_pinned_K(path)
    fit=fit_training(data["train"])
    if fit["n"]!=8919:
        raise ValueError("boat_8919_train_cohort")
    report=evaluate_october(fit,data["historical_october"],require_n=4382)
    report["original_K_source"]=evidence
    report["train_row_fingerprint"]=fit["train_roster_shas"]
    return report

#!/usr/bin/env python3
"""Research-only historical official-K C1/C2 athlete identity chronology.

Aug-Sep frozen training -> October historical holdout; all actual entry courses
are POSTRACE. This is NOT a T-12 prospective forecast, causal wall estimate or
an approved feature. No prediction-source/main/UI/cron changes.
"""
from __future__ import annotations

import argparse
from collections import defaultdict, Counter
from datetime import date, timedelta
import hashlib
import json
import math
from pathlib import Path
import random
from zipfile import ZipFile

if __package__:
    from .research_official_k_one_day_compare import RACE, parse_k, unpack_lha
    from .research_official_k_c2_escape_conditional_92day import verify_original_zip, race_outcome
else:
    from research_official_k_one_day_compare import RACE, parse_k, unpack_lha
    from research_official_k_c2_escape_conditional_92day import verify_original_zip, race_outcome

FIELDS = ("c1_escape", "c2_sashi")
MODELS = ("global", "venue", "venue_plus_c1", "venue_plus_c2", "venue_plus_both")
VENUE_PRIOR_STRENGTH = 40
ATHLETE_RESIDUAL_SHRINK = 40
BOOTSTRAP_SEED = 1692
BOOTSTRAP_DAYS = 4000
MIN_P = .005

def pclip(p):
    return min(1-MIN_P, max(MIN_P, p))

def official_rows(artifact_path: Path):
    """Return only SHA-verified rows. Registration IDs never leave local calculations."""
    whole_sha = verify_original_zip(artifact_path)
    rows, by_day = [], []
    raw_races = c1_eligible = c1_wins = 0
    with ZipFile(artifact_path) as z:
        if z.testzip() is not None:
            raise ValueError("official_zip_member_crc")
        manifest = json.loads(z.read("official_k_full_92day_reconciliation.json"))
        if manifest.get("study_period") != "2026-08-01/2026-10-31":
            raise ValueError("source_period_drift")
        original = manifest.get("results", [])
        if len(original) != 92 or len({d["day"] for d in original}) != 92:
            raise ValueError("manifest_92days_required")
        primary = {d["day"]: d for d in original}
        for offset in range(92):
            day = (date(2026,8,1) + timedelta(days=offset)).strftime("%Y%m%d")
            if day not in primary:
                raise ValueError("missing_frozen_day:" + day)
            item = primary[day]
            raw = z.read("official_k_full_92_raw/k" + day[2:] + ".lzh")
            raw_sha = hashlib.sha256(raw).hexdigest()
            if raw_sha != item["official_K_sha256"]:
                raise ValueError("official_raw_sha_mismatch:" + day)
            decoded = unpack_lha(raw, day=day)
            decoded_sha = hashlib.sha256(decoded).hexdigest()
            if decoded_sha != item["decoded_sha256"]:
                raise ValueError("official_decoded_sha_mismatch:" + day)
            txt = decoded.decode("cp932")
            expected_races = sum(bool(RACE.match(line)) for line in txt.splitlines())
            races = parse_k(txt, day=day, expected_races=expected_races, allow_unsettled=True)
            if len(races) != item["official_K_races"]:
                raise ValueError("race_count_drift:" + day)
            raw_races += len(races)
            by_day.append({"day":day,"official_raw_lzh_sha256":raw_sha,
                           "decoded_text_sha256":decoded_sha})
            for r in races.values():
                c1 = [e for e in r["entries"] if e["course"] == 1]
                if len(c1) == 1 and c1[0]["status"] not in {"F","S0","S1","S2"}:
                    c1_eligible += 1
                    c1_wins += int(c1[0]["status"] == "01")
                binary = race_outcome(r)
                if binary is None:
                    continue
                by_course = {e["course"]: e for e in r["entries"]}
                first, second = by_course[1], by_course[2]
                by_boat = {e["boat"]: e for e in r["entries"]}
                reg1, reg2 = first["athlete_registration"], second["athlete_registration"]
                boat1, boat2 = by_boat[1], by_boat[2]
                boat1_reg, boat2_reg = boat1["athlete_registration"], boat2["athlete_registration"]
                if any(not isinstance(reg,str) or len(reg)!=4 or not reg.isdigit()
                       for reg in (reg1,reg2,boat1_reg,boat2_reg)):
                    raise ValueError("registration_missing_or_invalid:" + r["code"])
                rows.append({"day":day,"month":day[4:6],"venue":r["venue"],
                             "c1_registration":reg1,"c2_registration":reg2,
                             "boat1_registration":boat1_reg,"boat2_registration":boat2_reg,
                             "boat1_actual_course":boat1["course"],
                             "boat2_actual_course":boat2["course"],
                             "c1_escape":binary["c1_escapement"],
                             "c2_sashi":binary["c2_sashi"]})
    if (raw_races,c1_eligible,c1_wins,len(rows)) != (14249,14090,7811,13815):
        raise ValueError("official_c1_c2_cohort_invariant")
    if len({r["day"] for r in rows}) != 92:
        raise ValueError("eligible_days_not_92")
    return rows, whole_sha, by_day

def losses_for_target(training, holdout, target, identity_role="actual_course"):
    if target not in FIELDS:
        raise ValueError("unsupported_target")
    if identity_role == "actual_course":
        identity1, identity2 = "c1_registration", "c2_registration"
    elif identity_role == "boat_number":
        identity1, identity2 = "boat1_registration", "boat2_registration"
    else:
        raise ValueError("unsupported_identity_role")
    n = len(training)
    global_p = sum(r[target] for r in training)/n
    v = defaultdict(lambda: [0,0])
    for r in training:
        pair = v[r["venue"]]
        pair[0] += r[target]
        pair[1] += 1
    def venue_p(code):
        n_yes,n_all = v.get(code,(0,0))
        return (n_yes + VENUE_PRIOR_STRENGTH*global_p)/(n_all+VENUE_PRIOR_STRENGTH)

    # Train-only residuals relative to each race's smoothed train-venue prior.
    a1, a2 = defaultdict(lambda:[0.,0]), defaultdict(lambda:[0.,0])
    for r in training:
        residual = r[target]-venue_p(r["venue"])
        for store, key in ((a1,r[identity1]),(a2,r[identity2])):
            rec = store[key]
            rec[0] += residual
            rec[1] += 1

    # No test-set mutations of the train groups, including unseen athlete IDs.
    stats = {m:{"n":0, "bs":0., "ls":0., "p":0., "wins":0} for m in MODELS}
    by_day = defaultdict(lambda:{m:{"n":0,"bs":0.,"ls":0.} for m in MODELS})
    repeat1=repeat2=0
    for r in holdout:
        base=venue_p(r["venue"])
        key1,key2=r[identity1],r[identity2]
        repeat1 += int(key1 in a1)
        repeat2 += int(key2 in a2)
        residue1,n1=a1.get(key1,(0.,0))
        residue2,n2=a2.get(key2,(0.,0))
        correction1=residue1/(n1+ATHLETE_RESIDUAL_SHRINK)
        correction2=residue2/(n2+ATHLETE_RESIDUAL_SHRINK)
        pred={"global":global_p,"venue":base,
              "venue_plus_c1":base+correction1,
              "venue_plus_c2":base+correction2,
              "venue_plus_both":base+correction1+correction2}
        y=r[target]
        for model in MODELS:
            p=pclip(pred[model])
            b=(p-y)**2
            l=-(y*math.log(p)+(1-y)*math.log(1-p))
            s=stats[model];s["n"]+=1;s["bs"]+=b;s["ls"]+=l;s["p"]+=p;s["wins"]+=y
            t=by_day[r["day"]][model];t["n"]+=1;t["bs"]+=b;t["ls"]+=l

    out={"identity_role":identity_role,"training_n":len(training),"holdout_n":len(holdout),
         "training_target_rate":round(global_p,8),
         "distinct_c1_training_athletes":len(a1),
         "distinct_c2_training_athletes":len(a2),
         "holdout_c1_seen_in_train":repeat1,
         "holdout_c2_seen_in_train":repeat2,
         "models":{}}
    for model, s in stats.items():
        out["models"][model]={"n":s["n"],"brier":round(s["bs"]/s["n"],8),
                              "logloss":round(s["ls"]/s["n"],8),
                              "observed_rate":round(s["wins"]/s["n"],8),
                              "mean_prediction":round(s["p"]/s["n"],8)}

    # Paired BOOTSTRAP over 31 October days, not individual races.
    daykeys=sorted(by_day)
    if len(daykeys)!=31:
        raise ValueError("test_days_not_31")
    rng=random.Random(BOOTSTRAP_SEED)
    comparisons={"c1_vs_venue":("venue_plus_c1","venue"),
                 "c2_vs_venue":("venue_plus_c2","venue"),
                 "both_vs_venue":("venue_plus_both","venue"),
                 "both_vs_c1":("venue_plus_both","venue_plus_c1")}
    daily={}
    for day in daykeys:
        dd=by_day[day]
        daily[day]={"n":dd["venue"]["n"],
                    "delta":{name:{
                        "brier":dd[a]["bs"]-dd[b]["bs"],
                        "logloss":dd[a]["ls"]-dd[b]["ls"],
                    } for name,(a,b) in comparisons.items()}}
    ci_samples={name:{key:[] for key in ("brier","logloss")} for name in comparisons}
    for _ in range(BOOTSTRAP_DAYS):
        sampled=[daykeys[rng.randrange(len(daykeys))] for __ in daykeys]
        denom=sum(daily[d]["n"] for d in sampled)
        for name in comparisons:
            for key in ("brier","logloss"):
                ci_samples[name][key].append(
                    sum(daily[d]["delta"][name][key] for d in sampled)/denom)
    intervals={}
    for name in comparisons:
        intervals[name]={}
        for key in ("brier","logloss"):
            a=sorted(ci_samples[name][key])
            lo,hi=a[int(.025*(len(a)-1))],a[int(.975*(len(a)-1))]
            intervals[name][key]={"lower_95":round(lo,8),"upper_95":round(hi,8),
                                  "includes_zero":lo<=0<=hi}
    out["paired_October_day_bootstrap"]={"seed":BOOTSTRAP_SEED,
                                         "replications":BOOTSTRAP_DAYS,
                                         "days":len(daykeys),
                                         "intervals":intervals}
    out["delta_vs_venue"]={
        model: {"brier":round(out["models"][model]["brier"]-out["models"]["venue"]["brier"],8),
                "logloss":round(out["models"][model]["logloss"]-out["models"]["venue"]["logloss"],8)}
        for model in MODELS}
    return out

def analyze(path: Path):
    races,zipsha,sha=official_rows(path)
    train=[r for r in races if r["month"] in ("08","09")]
    test=[r for r in races if r["month"]=="10"]
    if len(train)!=9241 or len(test)!=4574:
        raise ValueError("training_test_cohort_drift")
    return {
        "schema":"BOAT_EDGE_OFFICIAL_K_92DAY_HISTORICAL_C2_ATHLETE_HOLDOUT_V1",
        "source_class":"official_K_postrace_original_only_not_T12",
        "period":"2026-08-01/2026-10-31",
        "training_window":"2026-08-01/2026-09-30",
        "holdout_window":"2026-10-01/2026-10-31",
        "official_K_artifact_original_SHA256":zipsha,
        "official_K_raw_races":14249,
        "eligible_races":13815,
        "excluded_races":434,
        "design":{"heldout_October_not_used_for_training":True,
                  "training_only_retrospective_actual_courses":True,
                  "unproven_same_race_T12_actual_entry":True,
                  "unseen_athlete_residual":0,
                  "venue_prior_n":VENUE_PRIOR_STRENGTH,
                  "athlete_residual_prior_n":ATHLETE_RESIDUAL_SHRINK,
                  "probability_clip":[MIN_P,1-MIN_P],
                  "historical_exploratory_not_preregistered_prospective":True,
                  "training_results_not_frozen_before_original_race_deadline":True,
                  "no_result_backfill_into_saved_predictions":True,
                  "day_block_bootstrap_is_not_independent_prospective_validation":True},
        "summary":{key:losses_for_target(train,test,key) for key in FIELDS},
        "official_daily_source_sha":[r for r in sha],
        "official_T12_feature_certified":False,
        "official_same_race_entry_predeadline_certified":False,
        "forecast_effect_formally_proven":False,
        "production_authorized":False,
        "main_changed":False,
    }

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--artifact-zip",required=True,type=Path)
    p.add_argument("--out",required=True,type=Path)
    a=p.parse_args()
    result=analyze(a.artifact_zip)
    a.out.parent.mkdir(exist_ok=True,parents=True)
    a.out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({key:{"n":v["holdout_n"],
                            "c1_delta_brier":v["delta_vs_venue"]["venue_plus_c1"]["brier"],
                            "c2_delta_brier":v["delta_vs_venue"]["venue_plus_c2"]["brier"]}
                      for key,v in result["summary"].items()},ensure_ascii=False))

if __name__=="__main__":
    main()

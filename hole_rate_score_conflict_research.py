"""Exploratory third-boat score/rate conflict, using FULL retrospective cohorts.

Thresholds are transparent illustrative rules, NOT trained or promoted.
Outcome accessed only AFTER frozen donor feature ranking and all choices.
"""
import json
from collections import Counter
from pathlib import Path
from four_mode_archive_api import archived_four_modes
from four_mode_frozen_diagnostic import compare_race
from four_mode_historical_cohort import run as cohort_run
from hole_chronological_exploratory import date_blocks
from hole_pair_diversification_research import first_second
from hole_third_choice_research import variants,national_rates
from hole_third_feature_gap_audit import ticket_features

POLICIES=("baseline","national","score","score_guard_1pt","score_guard_2pt")
STRATA=("no_conflict","rate_le_1pt","rate_1_to_2pt","rate_gt_2pt","missing_features")


def alternatives(archive,rates):
    frozen=variants(archive,rates)
    base=frozen["baseline"]
    national=frozen["third_national_rate"]
    score=frozen["max_ticket_score"]
    feature=ticket_features(archive,rates)
    third_original=[t for t in national if t not in base]
    score_lookup={first_second(t):t for t in score if t not in base}
    if len(base)!=10 or len(national)!=10 or len(score)!=10 or (
            base[:5]!=national[:5] or base[:5]!=score[:5]):
        raise ValueError("invalid_frozen_candidates")
    results={"baseline":base,"national":national,"score":score}
    conflict_bands={}
    for threshold,name in ((1,"score_guard_1pt"),(2,"score_guard_2pt")):
        altered=national[:]
        for t in third_original:
            alt=score_lookup.get(first_second(t))
            if alt is None or alt==t:
                conflict_bands[first_second(t)]="no_conflict"
                continue
            f=feature.get(t)
            g=feature.get(alt)
            if f is None or g is None or f["national_rate"] is None or g["national_rate"] is None:
                band="missing_features"
            else:
                diff=f["national_rate"]-g["national_rate"]
                band=("rate_le_1pt" if diff<=1 else
                      "rate_1_to_2pt" if diff<=2 else "rate_gt_2pt")
            conflict_bands[first_second(t)]=band
            if (band!="missing_features" and
                    f is not None and g is not None and
                    g["max_donor_score"]>f["max_donor_score"] and
                    f["national_rate"]-g["national_rate"]<=threshold):
                altered[altered.index(t)]=alt
        results[name]=altered
    baseline_pairs={first_second(t) for t in base}
    selected_pairs={first_second(t) for t in national}
    for p,tickets in results.items():
        if (len(tickets)!=10 or len(set(tickets))!=10 or
                tickets[:5]!=base[:5] or
                (p!="baseline" and {first_second(t) for t in tickets}!=selected_pairs) or
                not baseline_pairs.issubset({first_second(t) for t in tickets})):
            raise ValueError("top5_budget_pair_invariant_"+p)
    return results,conflict_bands


def inspect(codes,root):
    metrics={p:Counter() for p in POLICIES}
    conflicts=Counter();strata={band:Counter() for band in STRATA}
    days={};unavailable=Counter();n=0;changed=Counter()
    for code in codes:
        status,archive=archived_four_modes(code,root)
        if status!=200:
            unavailable["invalid_archive"]+=1;continue
        rates=national_rates(code,root)
        chosen,bands=alternatives(archive,rates)
        # Full candidate selection is complete before result access.
        record=compare_race(code,root)
        if record.get("status")!="historical_comparison_only":
            unavailable["unconfirmed_result"]+=1;continue
        win=record["winning_ticket"]
        n+=1
        hit={p:win in t for p,t in chosen.items()}
        day=days.setdefault(code[:8],Counter());day["races"]+=1
        for p in POLICIES:
            metrics[p]["hits"]+=int(hit[p])
            changed[p]+=int(chosen[p]!=chosen["national"])
            if p not in ("baseline","national"):
                metrics[p]["only_new"]+=int(hit[p] and not hit["national"])
                metrics[p]["only_national"]+=int(hit["national"] and not hit[p])
                day[p+"_net"]+=int(hit[p])-int(hit["national"])
        win_pair=first_second(win)
        # Report conflict conditions across ALL races using frozen 1st/2nd pair.
        # The selection is never conditional on whether the race was a hit.
        band=bands.get(win_pair,"no_conflict")
        conflicts[band]+=1
        strata[band]["races"]+=1
        strata[band]["national_hits"]+=int(hit["national"])
        strata[band]["score_hits"]+=int(hit["score"])
        strata[band]["national_only"]+=int(hit["national"] and not hit["score"])
        strata[band]["score_only"]+=int(hit["score"] and not hit["national"])
    if sum(conflicts.values())!=n:
        raise ValueError("strata_not_exhaustive")
    for p in POLICIES:
        m=metrics[p]
        if p not in ("baseline","national"):
            m["net"]=m["only_new"]-m["only_national"]
            if m["net"]!=m["hits"]-metrics["national"]["hits"]:
                raise ValueError("paired_metric_mismatch")
            if sum(day.get(p+"_net",0) for day in days.values())!=m["net"]:
                raise ValueError("date_net_mismatch")
    return {
        "comparable":n,"unavailable":dict(unavailable),
        "top10":{p:dict(v) for p,v in metrics.items()},
        "changed_from_national":dict(changed),
        "pre_result_conflict_strata_on_actual_pair":{p:dict(v) for p,v in strata.items()},
        "by_date":{p:dict(v) for p,v in sorted(days.items())},
        "caveat":"Winner-pair strata are descriptive and conditioned on the outcome."
    }


def run(root=None):
    root=Path(root) if root else Path(__file__).resolve().parent
    cohort=cohort_run(root=root,limit=120)
    if cohort.get("status")!="historical_research_only":
        return {"status":"historical_cohort_unavailable","formal":False}
    old=sorted(c for c in cohort["cohort_codes"] if c[:8]<"20261103")
    blocks=date_blocks(old)
    recent=sorted(p.stem for p in (root/"four_mode_forecasts").glob(
        "20261103????.json") if not p.is_symlink())
    return {"schema":"HOLE_RATE_SCORE_CONFLICT_EXPLORATORY_V1",
            "status":"already_inspected_retrospective_only",
            "thresholds_are_unvalidated":True,
            "formal":False,"independent_holdout":False,
            "prospective_validation":False,
            "independent_first_receipt_verified":False,
            "production_forecast_changed":False,
            "locked_selector_changed":False,
            "groups":{"historical_earlier_reused":inspect(blocks["earlier"],root),
                      "historical_later_reused":inspect(blocks["later"],root),
                      "nov03_previously_inspected":inspect(recent,root)},
            "warning":"Retrospective 1pt/2pt rules are not preregistered future "
                      "candidates. Full-cohort comparisons are descriptive only."}


if __name__=="__main__":
    print(json.dumps(run(),ensure_ascii=False,sort_keys=True))

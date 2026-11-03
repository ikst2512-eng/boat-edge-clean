"""Full-denominator paired third-choice audit; retrospective research ONLY.

Every ticket variant is fixed from pre-result frozen archives. Report both
unconditional Top10 and conditional correct-pair accuracy, never treating the
latter as a genuine prospective hit rate or an untouched holdout.
"""
import json
from collections import Counter
from pathlib import Path

from four_mode_archive_api import archived_four_modes
from four_mode_frozen_diagnostic import compare_race
from four_mode_historical_cohort import run as cohort_run
from hole_chronological_exploratory import date_blocks
from hole_error_attribution_research import failure_class
from hole_pair_diversification_research import first_second
from hole_third_choice_research import national_rates
from hole_third_donor_ranking_research import select
from hole_third_consensus_guard_research import guarded
from hole_locked_two_pair_miss_audit import third_donor_state

POLICIES=("baseline","third_national_rate","max_ticket_score",
          "donor_consensus","consensus_guard")
CONDITIONS=("new_pair_selected","prior_pair_already_covered",
            "winning_pair_not_covered")


def candidates(archive,rates):
    original=select(archive,rates)
    chosen={name:original[name][:] for name in POLICIES if name!="consensus_guard"}
    chosen["consensus_guard"]=guarded(archive,rates,original)
    base=chosen["baseline"]
    locked=chosen["third_national_rate"]
    pairs_locked={first_second(t) for t in locked}
    original_pairs={first_second(t) for t in base}
    if not original_pairs.issubset(pairs_locked) or any(
        len(t)!=10 or len(set(t))!=10 or t[:5]!=base[:5] or
        (name!="baseline" and {first_second(x) for x in t}!=pairs_locked)
        for name,t in chosen.items()
    ):
        raise ValueError("invalid_frozen_pair_or_budget")
    return chosen


def inspect(codes,root):
    totals={p:Counter() for p in POLICIES}
    conditioning={key:{p:Counter() for p in POLICIES} for key in CONDITIONS}
    miss_states=Counter();pairwise={p:Counter() for p in POLICIES[2:]}
    daily={};unavailable=Counter();examples=[];compared=0
    for code in codes:
        status,archive=archived_four_modes(code,root)
        if status!=200:
            unavailable["invalid_archive"]+=1
            continue
        rates=national_rates(code,root)
        chosen=candidates(archive,rates)
        # Candidate sets and all feature-dependent choices are fixed here.
        outcome=compare_race(code,root)
        if outcome.get("status")!="historical_comparison_only":
            unavailable["unconfirmed_result"]+=1
            continue
        win=outcome["winning_ticket"]
        compared+=1
        base=chosen["baseline"]
        locked=chosen["third_national_rate"]
        win_pair=first_second(win)
        original_pairs={first_second(t) for t in base}
        selected_pairs={first_second(t) for t in locked}
        if win_pair in original_pairs:
            condition="prior_pair_already_covered"
        elif win_pair in selected_pairs:
            condition="new_pair_selected"
        else:
            condition="winning_pair_not_covered"
        day=daily.setdefault(code[:8],Counter())
        day["races"]+=1
        day[condition]+=1
        donor_status=third_donor_state(archive,win)
        if failure_class(locked,win)=="third_boat_absent":
            miss_states[donor_status]+=1
        locked_hit=win in locked
        base_hit=win in base
        for name,rows in chosen.items():
            hit=win in rows
            m=totals[name]
            c=conditioning[condition][name]
            m["hits"]+=int(hit)
            m["gained_vs_baseline"]+=int(hit and not base_hit)
            m["lost_vs_baseline"]+=int(base_hit and not hit)
            c["races"]+=1
            c["hits"]+=int(hit)
            if name not in ("baseline","third_national_rate"):
                pair=pairwise[name]
                pair["only_new"]+=int(hit and not locked_hit)
                pair["only_locked"]+=int(locked_hit and not hit)
                day[name+"_net"]+=int(hit)-int(locked_hit)
                if hit!=locked_hit and len(examples)<30:
                    examples.append({"race_code":code,"policy":name,
                                     "winner":win,"condition":condition,
                                     "new_hit":hit,
                                     "donor_availability":donor_status})
    if any(sum(conditioning[key][p]["races"] for key in CONDITIONS)!=compared
           for p in POLICIES):
        raise ValueError("condition_denominator_mismatch")
    output={}
    for p in POLICIES:
        m=totals[p]
        m["net_vs_baseline"]=m["gained_vs_baseline"]-m["lost_vs_baseline"]
        if m["net_vs_baseline"]!=m["hits"]-totals["baseline"]["hits"]:
            raise ValueError("baseline_hit_reconciliation")
        output[p]=dict(m)
    paired={}
    for p,m in pairwise.items():
        m["net"]=m["only_new"]-m["only_locked"]
        if m["net"]!=totals[p]["hits"]-totals["third_national_rate"]["hits"]:
            raise ValueError("paired_reconciliation")
        if sum(day.get(p+"_net",0) for day in daily.values())!=m["net"]:
            raise ValueError("date_reconciliation")
        paired[p]=dict(m)
    if sum(miss_states.values())>compared-output["third_national_rate"]["hits"]:
        raise ValueError("invalid_wrong_third_count")
    return {
        "comparable":compared,"unavailable":dict(unavailable),
        "top10_all_races":output,
        "correct_pair_condition":{
            group:{policy:dict(c) for policy,c in names.items()}
            for group,names in conditioning.items()},
        "paired_against_national":paired,
        "national_wrong_third_donor_status":dict(miss_states),
        "by_date":{d:dict(c) for d,c in sorted(daily.items())},
        "disagreement_examples":examples,
    }


def run(root=None):
    root=Path(root) if root else Path(__file__).resolve().parent
    old=cohort_run(root=root,limit=120)
    if old.get("status")!="historical_research_only":
        return {"status":"historical_cohort_unavailable","formal":False}
    historical=sorted(c for c in old["cohort_codes"] if c[:8]<"20261103")
    blocks=date_blocks(historical)
    nov03=sorted(p.stem for p in (root/"four_mode_forecasts").glob(
        "20261103????.json") if not p.is_symlink())
    return {
        "schema":"HOLE_THIRD_CONDITIONAL_FULL_DENOMINATOR_V1",
        "status":"reused_historical_research_only",
        "formal":False,"independent_holdout":False,
        "prospective_validation":False,
        "independent_first_receipt_verified":False,
        "locked_selector_changed":False,
        "production_forecast_changed":False,
        "groups":{
            "earlier_reused":inspect(blocks["earlier"],root),
            "later_reused":inspect(blocks["later"],root),
            "nov03_already_inspected":inspect(nov03,root),
        },
        "warning":"Conditioning on the observed winning pair is a post-outcome "
                  "diagnostic, not a real-time policy or unbiased hit rate. "
                  "All cohorts have been repeatedly analyzed; no independent holdout."
    }


if __name__=="__main__":
    print(json.dumps(run(),ensure_ascii=False,sort_keys=True))

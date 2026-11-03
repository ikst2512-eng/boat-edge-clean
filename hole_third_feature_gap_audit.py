"""Retrospective, outcome-blind candidate feature-gap audit (NOT model tuning).

Compute donor candidate features BEFORE reading confirmed results. Observed
winning third is examined only as an explanatory post-outcome diagnostic.
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

FEATURES=("national_rate","max_donor_score","best_donor_rank")
GROUPS=("chosen_exact_hit","selected_pair_wrong_third_donor_exact",
        "selected_pair_wrong_third_not_in_donor","pair_not_selected")


def ticket_features(archive,rates):
    features={}
    for mode in ("hit","balance"):
        for rank,entry in enumerate(archive["modes"][mode]["tickets"],start=1):
            t=entry["combo"]
            item=features.setdefault(t,{"max_donor_score":entry["p"],
                                        "best_donor_rank":rank,
                                        "donor_modes":set()})
            item["max_donor_score"]=max(item["max_donor_score"],entry["p"])
            item["best_donor_rank"]=min(item["best_donor_rank"],rank)
            item["donor_modes"].add(mode)
    for t,item in features.items():
        item["national_rate"]=rates[int(t.split("-")[2])-1] if rates is not None else None
    return features


def signed_gap(a,b):
    if a is None or b is None:
        return "missing"
    if a>b:return "positive"
    if a<b:return "negative"
    return "zero"


def inspect(codes,root):
    counts=Counter();signs={name:Counter() for name in FEATURES}
    by_day={};unavailable=Counter();examples=[];comparable=0
    for code in codes:
        status,archive=archived_four_modes(code,root)
        if status!=200:
            unavailable["invalid_archive"]+=1;continue
        rates=national_rates(code,root)
        frozen=variants(archive,rates)
        selected=frozen["third_national_rate"]
        base=frozen["baseline"]
        features=ticket_features(archive,rates)
        if len(selected)!=10 or len(set(selected))!=10 or selected[:5]!=base[:5]:
            raise ValueError("invalid_frozen_top10")
        # All ticket selection and feature extraction precede result access.
        outcome=compare_race(code,root)
        if outcome.get("status")!="historical_comparison_only":
            unavailable["unconfirmed_result"]+=1;continue
        comparable+=1
        win=outcome["winning_ticket"]
        win_pair=first_second(win)
        same_pair=[t for t in selected if first_second(t)==win_pair]
        day=by_day.setdefault(code[:8],Counter())
        day["races"]+=1
        if win in selected:
            group="chosen_exact_hit"
        elif not same_pair:
            group="pair_not_selected"
        elif win in features:
            group="selected_pair_wrong_third_donor_exact"
        else:
            group="selected_pair_wrong_third_not_in_donor"
        counts[group]+=1
        day[group]+=1
        if group=="selected_pair_wrong_third_donor_exact":
            # Winner is only used for descriptive after-the-fact feature gaps.
            chosen=max(same_pair,key=lambda t:(
                features.get(t,{}).get("national_rate") or -1,t))
            reference=features.get(chosen)
            winning=features[win]
            for name in FEATURES:
                if reference is None:
                    sign="missing"
                else:
                    # Positive: selected ticket feature > actually winning ticket
                    sign=signed_gap(reference.get(name),winning.get(name))
                signs[name][sign]+=1
                day[name+"_"+sign]+=1
            if len(examples)<20:
                examples.append({
                    "race_code":code,"selected_ticket":chosen,
                    "winning_ticket":win,
                    "selected_features":{
                        k:reference.get(k) if reference is not None else None
                        for k in FEATURES},
                    "winning_features":{k:winning.get(k) for k in FEATURES}
                })
    if sum(counts.values())!=comparable:
        raise ValueError("group_denominator")
    target=counts["selected_pair_wrong_third_donor_exact"]
    for key in FEATURES:
        if sum(signs[key].values())!=target:
            raise ValueError("feature_gap_denominator")
    return {"comparable":comparable,"excluded":dict(unavailable),
            "outcomes":{k:counts[k] for k in GROUPS},
            "feature_gap_signs":{k:dict(v) for k,v in signs.items()},
            "by_date":{k:dict(v) for k,v in sorted(by_day.items())},
            "examples":examples}


def run(root=None):
    root=Path(root) if root is not None else Path(__file__).resolve().parent
    cohort=cohort_run(root=root,limit=120)
    if cohort.get("status")!="historical_research_only":
        return {"status":"historical_cohort_unavailable","formal":False}
    old=sorted(x for x in cohort["cohort_codes"] if x[:8]<"20261103")
    blocks=date_blocks(old)
    latest=sorted(p.stem for p in (root/"four_mode_forecasts").glob(
        "20261103????.json") if not p.is_symlink())
    return {"schema":"HOLE_THIRD_FEATURE_GAPS_V1",
            "status":"retrospective_previously_inspected_only",
            "formal":False,"independent_holdout":False,
            "prospective_validation":False,
            "independent_first_receipt_verified":False,
            "locked_selector_changed":False,
            "production_forecast_changed":False,
            "groups":{"historical_earlier_reused":inspect(blocks["earlier"],root),
                      "historical_later_reused":inspect(blocks["later"],root),
                      "nov03_previously_inspected":inspect(latest,root)},
            "warning":"Features of winner are examined after outcome, not available "
                      "as a live selection oracle. Directional gaps are descriptive "
                      "and cannot justify retrospectively fitted thresholds."}

if __name__=="__main__":
    print(json.dumps(run(),ensure_ascii=False,sort_keys=True))

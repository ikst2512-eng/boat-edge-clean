"""Explain later-date hole ticket misses with outcome-only historical diagnostics."""
import json
from collections import Counter
from pathlib import Path
from four_mode_historical_cohort import run as cohort_run
from hole_chronological_exploratory import date_blocks
from four_mode_frozen_diagnostic import compare_race
from four_mode_archive_api import archived_four_modes

TYPES=("covered","winner_head_absent","winner_second_pair_absent","winner_third_absent")
def diagnose(codes,root):
    counts={m:Counter() for m in ("hole","hit","balance")}
    rescue={"hit_head":0,"balance_head":0,"hit_pair":0,
            "balance_pair":0,"hit_full":0,"balance_full":0}
    cases=[]
    for code in codes:
        result=compare_race(code,root)
        status,archive=archived_four_modes(code,root)
        if result.get("status")!="historical_comparison_only" or status!=200:
            raise ValueError("unverifiable_race_"+code)
        winning=result["winning_ticket"]
        head,second,_=winning.split("-")
        pair=(head,second)
        modes={m:[x["combo"] for x in archive["modes"][m]["tickets"]]
               for m in ("hole","hit","balance")}
        row={"race_code":code,"winning_ticket":winning,
             "hole_miss":result["modes"]["hole"]["coverage_diagnostic"]}
        for mode in modes:
            kind=result["modes"][mode]["coverage_diagnostic"]
            if kind not in TYPES: raise ValueError("unknown_diagnostic")
            counts[mode][kind]+=1
        for mode in ("hit","balance"):
            parsed=[x.split("-") for x in modes[mode]]
            rescue[mode+"_head"]+=int(any(x[0]==head for x in parsed))
            rescue[mode+"_pair"]+=int(any(tuple(x[:2])==pair for x in parsed))
            rescue[mode+"_full"]+=int(winning in modes[mode])
        cases.append(row)
    return {"comparable":len(cases),
            "misses":{m:{key:counts[m][key] for key in TYPES} for m in counts},
            "donor_winning_coverage":rescue,"cases":cases}

def run(root=None):
    root=Path(root) if root else Path(__file__).resolve().parent
    cohort=cohort_run(root=root,limit=120)
    if cohort.get("status")!="historical_research_only":
        return {"status":"no_cohort","formal":False}
    split=date_blocks(cohort["cohort_codes"])
    if split["status"]!="date_blocked":
        return {"status":"insufficient_distinct_dates","formal":False}
    later=diagnose(split["later"],root)
    if later["comparable"]!=len(split["later"]):
        raise ValueError("incomplete_comparison")
    return {"schema":"HOLE_LATER_MISS_V1","status":"historical_diagnostic",
            "formal":False,"independent_holdout":False,
            "production_forecast_changed":False,
            "later_dates":sorted(set(x[:8] for x in split["later"])),
            "earlier_count":len(split["earlier"]),"later":later,
            "warning":"Winning order is used only for retrospective diagnostics, never ticket selection. Previously researched races."}
if __name__=="__main__":
    print(json.dumps(run(),ensure_ascii=False,sort_keys=True))

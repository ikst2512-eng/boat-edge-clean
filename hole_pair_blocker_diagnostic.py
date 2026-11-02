"""Outcome-blind hole donor insertion blockers; outcome only labels retrospective misses."""
import json
from collections import Counter
from pathlib import Path
from four_mode_historical_cohort import run as cohort_run
from hole_chronological_exploratory import date_blocks
from four_mode_archive_api import archived_four_modes
from four_mode_frozen_diagnostic import compare_race
from hole_upper_rank_pair_protection import propose

def reason(hole, donor, rank=3):
    base=hole[:10]
    if len(base)<rank: return "insufficient_base"
    pairs=[tuple(x.split("-")[:2]) for x in base]
    heads={p[0] for p in pairs}
    available=[t for t in donor if t not in base and t.split("-")[0] in heads
               and tuple(t.split("-")[:2]) not in pairs]
    if not available: return "no_new_same_head_pair_in_donor"
    counts=Counter(pairs)
    removable=[i for i in range(rank-1,len(base)) if counts[pairs[i]]>1]
    if not removable: return "no_redundant_pair_to_evict"
    if propose(base,donor,rank)==base: return "unexpected_no_change"
    return "insertion_possible"

def run(root=None):
    root=Path(root) if root else Path(__file__).resolve().parent
    cohort=cohort_run(root=root,limit=120)
    if cohort.get("status")!="historical_research_only":
        return {"status":"no_cohort","formal":False}
    split=date_blocks(cohort["cohort_codes"])
    if split["status"]!="date_blocked":
        return {"status":"insufficient_dates","formal":False}
    counts=Counter(); sub=Counter(); rows=[]
    for code in split["later"]:
        state,archive=archived_four_modes(code,root)
        result=compare_race(code,root)
        if state!=200 or result.get("status")!="historical_comparison_only":
            raise ValueError("missing_comparable_"+code)
        modes={m:[t["combo"] for t in archive["modes"][m]["tickets"]]
               for m in ("hole","hit","balance")}
        if result["modes"]["hole"]["coverage_diagnostic"]!="winner_second_pair_absent":
            continue
        target=result["winning_ticket"].split("-")[:2]
        donor=modes["hit"]
        donor_pairs=[tuple(t.split("-")[:2]) for t in donor]
        donor_has=tuple(target) in donor_pairs
        category=reason(modes["hole"],donor,3)
        counts[category]+=1
        sub[("donor_pair_present" if donor_has else "donor_pair_absent",category)]+=1
        rows.append({"race_code":code,"blocker":category,"donor_has_winning_pair":donor_has,
                     "candidate_changed":propose(modes["hole"][:10],donor,3)!=modes["hole"][:10],
                     "winning_pair":target})
    return {"schema":"HOLE_PAIR_BLOCKERS_V1","status":"retrospective_diagnostic",
            "formal":False,"independent_holdout":False,"production_forecast_changed":False,
            "cases":len(rows),"blockers":dict(sorted(counts.items())),
            "winning_pair_cross_tab":[{"donor_pair_present":p=="donor_pair_present",
              "blocker":b,"count":v} for (p,b),v in sorted(sub.items())],
            "rows":rows,"warning":"Results only label cases after the fact; no forecast modifications or prospective claims."}
if __name__=="__main__": print(json.dumps(run(),ensure_ascii=False,sort_keys=True))

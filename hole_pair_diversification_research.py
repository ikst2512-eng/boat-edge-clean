"""Research only: cover two distinct donor 1st-2nd pairs within 10 tickets.

Compare one pair with two third choices vs two pairs with one third each.
All selection is based on frozen predictions; finishing order is read afterwards.
"""
import hashlib
import json
from collections import Counter
from pathlib import Path
from four_mode_archive_api import archived_four_modes
from four_mode_frozen_diagnostic import compare_race, classify_ticket_miss
from four_mode_historical_cohort import run as cohort_run
from hole_top5_safe_bundle_research import proposals

TOPS=(3,5,10)
MODES=("baseline","same_pair_two_thirds","two_pairs_one_third")

def first_second(t):
    return tuple(t.split("-")[:2])

def diversify(archive):
    m=archive["modes"]
    base=[x["combo"] for x in m["hole"]["tickets"][:10]]
    if len(base)<10:
        return base
    existing={first_second(t) for t in base}
    heads={p[0] for p in existing}
    donor=list(dict.fromkeys(x["combo"] for name in ("hit","balance")
                              for x in m[name]["tickets"]))
    chosen=[]
    chosen_pairs=set()
    for t in donor:
        p=first_second(t)
        if t not in base and p not in existing and p not in chosen_pairs and p[0] in heads:
            chosen.append(t)
            chosen_pairs.add(p)
            if len(chosen)==2:break
    if len(chosen)!=2:
        return base
    counts=Counter(first_second(t) for t in base)
    removed=[]
    for i in range(len(base)-1,4,-1):
        p=first_second(base[i])
        if counts[p]>1:
            removed.append(i)
            counts[p]-=1
            if len(removed)==2:break
    if len(removed)!=2:
        return base
    candidate=base[:]
    for i in sorted(removed,reverse=True): candidate.pop(i)
    candidate[5:5]=chosen
    if candidate[:5]!=base[:5] or len(candidate)!=len(base) or len(set(candidate))!=len(candidate):
        raise ValueError("top5_or_budget")
    if not existing.issubset({first_second(t) for t in candidate}):
        raise ValueError("pair_coverage")
    return candidate

def variants(archive):
    previous=proposals(archive)
    return {"baseline":previous["baseline"],
            "same_pair_two_thirds":previous["bundle_protect_top5"],
            "two_pairs_one_third":diversify(archive)}

def inspect(codes,root):
    metrics={name:{f"top{k}":{"hits":0,"gained":0,"lost":0} for k in TOPS} for name in MODES}
    changed=Counter();missing=Counter()
    pair_selection={"second_pair_absent":0,"first_pair_selected":0,"second_pair_selected":0,
                    "same_pair_selected":0,"correct_ticket_added":0}
    rows=[]
    for code in codes:
        status,archive=archived_four_modes(code,root)
        if status!=200:
            missing["archive_unavailable"]+=1;continue
        # Freeze all candidates BEFORE accessing the confirmed result.
        candidates=variants(archive)
        result=compare_race(code,root)
        if result.get("status")!="historical_comparison_only":
            missing["unconfirmed_result"]+=1;continue
        winner=result["winning_ticket"]
        base=candidates["baseline"]
        flags={name:{f"top{k}":winner in picks[:k] for k in TOPS}
               for name,picks in candidates.items()}
        for name,picks in candidates.items():
            changed[name]+=int(picks!=base)
            if picks[:5]!=base[:5]:
                raise ValueError("top5_changed")
            for k in TOPS:
                key=f"top{k}";before=flags["baseline"][key];after=flags[name][key]
                m=metrics[name][key]
                m["hits"]+=int(after);m["gained"]+=int(after and not before)
                m["lost"]+=int(before and not after)
        if classify_ticket_miss(base,winner)=="winner_second_pair_absent":
            pair_selection["second_pair_absent"]+=1
            added=[t for t in candidates["two_pairs_one_third"] if t not in base]
            selected={first_second(t) for t in added}
            matching=first_second(winner) in selected
            pair_selection["first_pair_selected"]+=int(len(added)>0 and first_second(added[0])==first_second(winner))
            pair_selection["second_pair_selected"]+=int(len(added)>1 and first_second(added[1])==first_second(winner))
            pair_selection["same_pair_selected"]+=int(first_second(winner) in
                  {first_second(t) for t in candidates["same_pair_two_thirds"] if t not in base})
            pair_selection["correct_ticket_added"]+=int(winner in added)
        rows.append({"race_code":code,"flags":flags})
    for name in metrics:
        for k in TOPS:
            key=f"top{k}";m=metrics[name][key]
            m["net"]=m["gained"]-m["lost"]
            if m["hits"]-metrics["baseline"][key]["hits"]!=m["net"]:
                raise ValueError("attribution")
            if k<=5 and (m["gained"] or m["lost"]):
                raise ValueError("top5_hit_shift")
    return {"compared":len(rows),"missing":dict(missing),"changed":dict(changed),
            "topn":metrics,"pair_selection":pair_selection,"rows":rows}

def run(root=None):
    root=Path(root) if root else Path(__file__).resolve().parent
    c=cohort_run(root=root,limit=120)
    if c.get("status")!="historical_research_only":
        return {"status":"no_historical_cohort","formal":False}
    # Do not mix new Nov 3 results with repeatedly studied historical dates.
    old=sorted(x for x in c["cohort_codes"] if x[:8]<"20261103")
    new=sorted(p.stem for p in (root/"four_mode_forecasts").glob("20261103????.json")
               if not p.is_symlink())
    return {"schema":"HOLE_PAIR_DIVERSIFICATION_V1","status":"exploratory_research_only",
            "formal":False,"independent_holdout":False,
            "independent_first_receipt_verified":False,"prospective_validation":False,
            "production_forecast_changed":False,
            "prior_cohort_sha256":hashlib.sha256("\n".join(old).encode()).hexdigest(),
            "groups":{"previously_studied":inspect(old,root),"nov03_previously_inspected":inspect(new,root)},
            "warning":"No independent proof. Nov 3 outcomes already inspected; neither period is an independent held-out test. Candidates are selected without results."}

if __name__=="__main__":
    print(json.dumps(run(),ensure_ascii=False,sort_keys=True))

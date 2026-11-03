"""Compare Top5-preserving Top10 hole pair selection using only frozen scores.

No outcome data is used to select candidate pairs. Scores p are uncalibrated.
"""
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

from four_mode_archive_api import archived_four_modes
from four_mode_frozen_diagnostic import compare_race
from four_mode_historical_cohort import run as historical_cohort
from hole_chronological_exploratory import date_blocks
from hole_pair_third_bundle_research import bundle

TOPS=(3,5,10)
NAMES=("baseline","first_eligible","highest_joint_p","pair_agreement","score_margin_guard")
PAIR_POLICIES=("highest_joint_p","pair_agreement","score_margin_guard")


def pick(archive,policy):
    """Return ten tickets, preserving exact frozen Top5 and existing pair coverage."""
    if policy not in NAMES:
        raise ValueError("unknown_policy")
    modes=archive["modes"]
    base=[x["combo"] for x in modes["hole"]["tickets"][:10]]
    donors=[x["combo"] for key in ("hit","balance") for x in modes[key]["tickets"]]
    if policy=="baseline":
        return base
    first=list(dict.fromkeys(donors))
    if policy=="first_eligible":
        return bundle(base,first,6,2)
    # Combine exact-ticket evidence across modes without counting the same ticket twice.
    pmap={};rank={};sources=defaultdict(set)
    for mode in ("hit","balance"):
        for i,row in enumerate(modes[mode]["tickets"]):
            t=row["combo"]
            pmap[t]=max(pmap.get(t,0.0),row["p"])
            rank[t]=min(rank.get(t,999),i)
            sources[t].add(mode)
    pairs={tuple(x.split("-")[:2]) for x in base}
    heads={x[0] for x in pairs}
    groups=defaultdict(list)
    for t in first:
        pair=tuple(t.split("-")[:2])
        if t not in base and pair not in pairs and pair[0] in heads:
            groups[pair].append(t)
    eligible=[]
    for pair,items in groups.items():
        if len(items)<2:continue
        ordered=sorted(items,key=lambda t:(-pmap[t],rank[t],t))
        two=ordered[:2]
        agreement=int(any(pair==tuple(t.split("-")[:2]) for t in
                          (x["combo"] for x in modes["hit"]["tickets"]))
                      and any(pair==tuple(t.split("-")[:2]) for t in
                              (x["combo"] for x in modes["balance"]["tickets"])))
        eligible.append((pair,two,pmap[two[0]]+pmap[two[1]],agreement))
    if not eligible:
        return base
    if policy=="pair_agreement":
        eligible.sort(key=lambda x:(-x[3],-x[2],x[0]))
    else:
        eligible.sort(key=lambda x:(-x[2],-x[3],x[0]))
    # Preserve all existing 1-2 pairs by evicting two redundant tickets at rank >=6.
    counts=Counter(tuple(t.split("-")[:2]) for t in base)
    removed=[]
    for i in range(len(base)-1,4,-1):
        pair=tuple(base[i].split("-")[:2])
        if counts[pair]>1:
            removed.append(i)
            counts[pair]-=1
            if len(removed)==2:break
    if len(removed)!=2:
        return base
    chosen=eligible[0][1]
    if policy=="score_margin_guard":
        # Conservative score threshold: do not trade higher-scored discarded combos
        # for lower-scored replacements on frozen, uncalibrated values.
        old_score=sum(next((row["p"] for row in modes["hole"]["tickets"]
                            if row["combo"]==base[i]),0.0) for i in removed)
        if eligible[0][2]<old_score:
            return base
    new=base[:]
    for i in sorted(removed,reverse=True):
        new.pop(i)
    for offset,t in enumerate(chosen):
        new.insert(5+offset,t)
    if new[:5]!=base[:5] or len(new)!=len(base) or len(set(new))!=len(new):
        raise ValueError("top5_or_budget_changed")
    if not pairs.issubset({tuple(t.split("-")[:2]) for t in new}):
        raise ValueError("prior_pair_coverage_lost")
    return new


def compare(codes,root):
    hits={name:{f"top{k}":{"hits":0,"gained":0,"lost":0} for k in TOPS} for name in NAMES}
    changed=Counter();unavailable=Counter();rows=[]
    for code in codes:
        status,archive=archived_four_modes(code,root)
        if status!=200:
            unavailable["archive_unavailable"]+=1;continue
        # All candidate tickets are chosen before accessing confirmed order.
        candidates={name:pick(archive,name) for name in NAMES}
        result=compare_race(code,root)
        if result.get("status")!="historical_comparison_only":
            unavailable["unconfirmed_result"]+=1;continue
        winner=result["winning_ticket"]
        flags={name:{f"top{k}":winner in picks[:k] for k in TOPS}
               for name,picks in candidates.items()}
        baseline=flags["baseline"]
        for name in NAMES:
            changed[name]+=int(candidates[name]!=candidates["baseline"])
            for k in TOPS:
                key=f"top{k]";key=key[:-1] # explicitly use stable Top-N keys
                hit=flags[name][key];original=baseline[key]
                bucket=hits[name][key]
                bucket["hits"]+=int(hit)
                bucket["gained"]+=int(hit and not original)
                bucket["lost"]+=int(original and not hit)
        for name in NAMES:
            if flags[name]["top5"]!=baseline["top5"]:
                raise ValueError("top5_hit_changed")
        rows.append({"race_code":code,"flags":flags})
    for name in NAMES:
        for k in TOPS:
            key=f"top{k}";b=hits[name][key]
            b["net"]=b["gained"]-b["lost"]
            if b["hits"]-hits["baseline"][key]["hits"]!=b["net"]:
                raise ValueError("inconsistent_attribution")
    return {"comparable":len(rows),"unavailable":dict(unavailable),"changed":dict(changed),
            "topn":hits,"rows":rows}


def run(root=None):
    root=Path(root) if root else Path(__file__).resolve().parent
    cohort=historical_cohort(root=root,limit=120)
    if cohort.get("status")!="historical_research_only":
        return {"status":"no_historical_cohort","formal":False}
    split=date_blocks(cohort["cohort_codes"])
    if split["status"]!="date_blocked":
        return {"status":"no_date_block","formal":False}
    new_codes=sorted(path.stem for path in (root/"four_mode_forecasts").glob("20261103????.json")
                     if not path.is_symlink())
    dates=dict(sorted(Counter(c[:8] for c in cohort["cohort_codes"]).items()))
    fingerprint=hashlib.sha256("\n".join(sorted(cohort["cohort_codes"])).encode()).hexdigest()
    return {"schema":"HOLE_SAFE_TOP10_PAIR_RANK_V1","status":"exploratory_replay",
            "formal":False,"independent_holdout":False,
            "prospective_validation":False,"independent_first_receipt_verified":False,
            "score_calibrated":False,"production_forecast_changed":False,
            "historical_cohort_hash":fingerprint,"historical_date_counts":dates,
            "groups":{"historical_early":compare(split["earlier"],root),
                      "historical_late":compare(split["later"],root),
                      "nov03":compare(new_codes,root)},
            "warning":"Already-researched training dates may drift; Nov03 is a small, previously inspected forward date. No production conclusions."}


if __name__=="__main__":
    print(json.dumps(run(),ensure_ascii=False,sort_keys=True))

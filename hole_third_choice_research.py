"""Research-only third-boat choice for two distinct new first-second pairs.

Selection uses frozen forecasts and optional six national win rates only.
Never select using confirmed results. Independent predeadline receipt unverified.
"""
import hashlib
import json
import math
from collections import Counter,defaultdict
from pathlib import Path
from four_mode_archive_api import archived_four_modes
from four_mode_frozen_diagnostic import compare_race,classify_ticket_miss
from four_mode_historical_cohort import run as cohort_run
from hole_pair_diversification_research import diversify,first_second

TOPS=(3,5,10)
POLICIES=("baseline","donor_order","max_ticket_score","third_national_rate")

def variants(archive,rates=None):
    modes=archive["modes"]
    base=[x["combo"] for x in modes["hole"]["tickets"][:10]]
    selected=diversify(archive)
    if selected==base:
        return {p:base for p in POLICIES}
    new=[t for t in selected if t not in base]
    if len(new)!=2 or first_second(new[0])==first_second(new[1]):
        raise ValueError("unexpected_diversified_pairs")
    # Rank eligible third boats for exactly the same two selected pairs.
    donor={}
    for mode in ("hit","balance"):
        for rank,row in enumerate(modes[mode]["tickets"]):
            t=row["combo"]
            donor.setdefault(t,{"p":row["p"],"rank":rank})
            donor[t]["p"]=max(donor[t]["p"],row["p"])
            donor[t]["rank"]=min(donor[t]["rank"],rank)
    variants_out={"baseline":base,"donor_order":selected}
    for policy in ("max_ticket_score","third_national_rate"):
        alt=[]
        for original in new:
            target=first_second(original)
            candidates=[t for t in donor if first_second(t)==target and t not in base]
            if not candidates:
                candidates=[original]
            if policy=="third_national_rate" and rates is not None:
                ranked=sorted(candidates,key=lambda t:(-rates[int(t[-1])-1],-donor[t]["p"],donor[t]["rank"],t))
            else:
                ranked=sorted(candidates,key=lambda t:(-donor[t]["p"],donor[t]["rank"],t))
            alt.append(ranked[0])
        updated=[t for t in selected if t not in new]
        updated[5:5]=alt
        variants_out[policy]=updated
    pairs_before={first_second(t) for t in base}
    for p,updated in variants_out.items():
        if updated[:5]!=base[:5] or len(updated)!=len(base) or len(set(updated))!=len(updated):
            raise ValueError("top5_or_budget_"+p)
        if not pairs_before.issubset({first_second(t) for t in updated}):
            raise ValueError("prior_pair_removed_"+p)
    return variants_out

def national_rates(code,root):
    path=Path(root)/"four_mode_forecasts"/(code+".json")
    if path.is_symlink() or not path.is_file() or path.stat().st_size>30000:
        raise ValueError("untrusted_archive")
    obj=json.loads(path.read_text(encoding="utf-8"))
    rates=obj.get("input_national_win_rates")
    if rates is None:return None
    if not isinstance(rates,list) or len(rates)!=6 or any(
        type(v) not in (int,float) or not math.isfinite(v) or v<0 or v>10 for v in rates):
        raise ValueError("invalid_rates")
    return rates

def compare(codes,root):
    hits={p:{f"top{k}":{"hits":0,"gained":0,"lost":0} for k in TOPS} for p in POLICIES}
    detail=Counter();missing=Counter();rows=[];changed=Counter()
    for code in codes:
        status,archive=archived_four_modes(code,root)
        if status!=200:
            missing["invalid_archive"]+=1;continue
        rates=national_rates(code,root)
        chosen=variants(archive,rates)
        # No outcome is passed to the candidate generator.
        outcome=compare_race(code,root)
        if outcome.get("status")!="historical_comparison_only":
            missing["unconfirmed_result"]+=1;continue
        winner=outcome["winning_ticket"]
        base=chosen["baseline"]
        miss=classify_ticket_miss(base,winner)
        if miss=="winner_second_pair_absent":
            detail["missing_second_pair"]+=1
            first_two=[t for t in chosen["donor_order"] if t not in base]
            pair_matches=[t for t in first_two if first_second(t)==first_second(winner)]
            if pair_matches:
                detail["selected_correct_pair"]+=1
                if winner not in first_two:
                    detail["correct_pair_wrong_third"]+=1
                    all_donor={x["combo"] for name in ("hit","balance")
                               for x in archive["modes"][name]["tickets"]}
                    if winner in all_donor:detail["correct_third_available_in_donors"]+=1
        flags={}
        for p,tickets in chosen.items():
            changed[p]+=int(tickets!=base)
            flags[p]={f"top{k}":winner in tickets[:k] for k in TOPS}
            for k in TOPS:
                key=f"top{k}";before=winner in base[:k];after=flags[p][key]
                bucket=hits[p][key]
                bucket["hits"]+=int(after)
                bucket["gained"]+=int(after and not before)
                bucket["lost"]+=int(before and not after)
                if k<=5 and before!=after:raise ValueError("top5_moved")
        rows.append({"race_code":code,"miss_class":miss,"flags":flags})
    for p in POLICIES:
        for k in TOPS:
            key=f"top{k}";metric=hits[p][key]
            metric["net"]=metric["gained"]-metric["lost"]
            if metric["hits"]-hits["baseline"][key]["hits"]!=metric["net"]:
                raise ValueError("attribution")
    return {"comparable":len(rows),"unavailable":dict(missing),"changed":dict(changed),
            "third_choice_diagnostic":dict(detail),"topn":hits,"rows":rows}

def run(root=None):
    root=Path(root) if root else Path(__file__).resolve().parent
    c=cohort_run(root=root,limit=120)
    if c.get("status")!="historical_research_only":
        return {"status":"no_cohort","formal":False}
    older=sorted(code for code in c["cohort_codes"] if code[:8]<"20261103")
    newer=sorted(p.stem for p in (root/"four_mode_forecasts").glob("20261103????.json")
                 if not p.is_symlink())
    return {"schema":"HOLE_THIRD_BOAT_CHOICE_RESEARCH_V1","status":"exploratory_only",
            "formal":False,"independent_holdout":False,
            "independent_first_receipt_verified":False,"prospective_validation":False,
            "production_forecast_changed":False,"score_calibrated":False,
            "older_codes_sha256":hashlib.sha256("\n".join(older).encode()).hexdigest(),
            "groups":{"historical_reused":compare(older,root),
                      "nov03_already_inspected":compare(newer,root)},
            "warning":"All outcome comparisons are retrospective; Nov03 already inspected. National win rate is not third-place probability."}

if __name__=="__main__":
    print(json.dumps(run(),ensure_ascii=False,sort_keys=True))

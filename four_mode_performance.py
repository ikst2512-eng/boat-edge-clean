"""Four-mode simulated staking and verified results; never claim unverified performance."""
from datetime import datetime
from verification_pipeline import valid_ticket

MODES=("hit","balance","hole","narrow")

def allocate(tickets,budget_yen=5000):
    if type(budget_yen)!=int or budget_yen<5000 or budget_yen>10000 or budget_yen%100:
        raise ValueError("budget_out_of_range")
    if not isinstance(tickets,list) or not 1<=len(tickets)<=50:raise ValueError("invalid_tickets")
    combos=[v.get("combo") if isinstance(v,dict) else v for v in tickets]
    if len(combos)!=len(set(combos)) or not all(valid_ticket(c) for c in combos):raise ValueError("invalid_tickets")
    q,rem=divmod(budget_yen//100,len(combos))
    if q<1:raise ValueError("budget_too_small")
    return {c:100*(q+(i<rem)) for i,c in enumerate(combos)}

def evaluate(archive,result,payout_per_100_yen,budget_yen=5000,first_add_verified=False):
    if first_add_verified is not True:raise ValueError("first_git_add_proof_required")
    if archive.get("schema")!="CLEAN_FOUR_MODES_PREDEADLINE_V1":raise ValueError("invalid_archive")
    saved=datetime.fromisoformat(archive["generated_at_jst"])
    deadline=datetime.fromisoformat(archive["deadline_jst"])
    if saved.utcoffset() is None or deadline.utcoffset() is None or saved>=deadline:raise ValueError("late_or_unproven_forecast")
    race=archive.get("race_code")
    if not isinstance(race,str) or len(race)!=12 or not race.isdigit():raise ValueError("invalid_race")
    if result.get("race_code")!=race or result.get("status")!="confirmed":raise ValueError("unconfirmed_result")
    order=result.get("finish_order")
    if not isinstance(order,list) or len(order)!=3 or len(set(map(str,order)))!=3 or any(type(v)!=int or v<1 or v>6 for v in order):
        raise ValueError("invalid_finish")
    if type(payout_per_100_yen)!=int or payout_per_100_yen<100:raise ValueError("official_payout_required")
    modes=archive.get("modes")
    if not isinstance(modes,dict) or set(modes)!=set(MODES):raise ValueError("missing_modes")
    winner="-".join(map(str,order))
    output={}
    for mode in MODES:
        stakes=allocate(modes[mode]["tickets"],budget_yen)
        returns=stakes.get(winner,0)*payout_per_100_yen//100
        output[mode]={"hit":winner in stakes,"invested_yen":budget_yen,"return_yen":returns}
    return {"race_code":race,"verified":True,"modes":output}

def summary(records):
    records=[r for r in records if r.get("verified") is True]
    out={}
    for mode in MODES:
        samples=[r["modes"][mode] for r in records if mode in r.get("modes",{})]
        hits=sum(x["hit"] is True for x in samples)
        invested=sum(x["invested_yen"] for x in samples)
        returned=sum(x["return_yen"] for x in samples)
        out[mode]={"sample_races":len(samples),"hits":hits,
                   "actual_hit_rate_pct":round(hits*100/len(samples),2) if samples else None,
                   "actual_roi_pct":round(returned*100/invested,2) if invested else None,
                   "invested_yen":invested,"return_yen":returned,"profit_yen":returned-invested}
    return out

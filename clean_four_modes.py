"""CLEAN independent four-mode prospective forecasts. Targets are goals, not attained rates."""
from datetime import datetime
import json
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

TARGETS={"hit":0.60,"balance":0.50,"hole":0.125,"narrow":0.40}
LABELS={"hit":"本命","balance":"バランス","hole":"穴","narrow":"絞り"}


def rank_modes(prob_rows):
    """Different mode memberships, uncalibrated until forward evaluation."""
    rows=[("-".join(map(str,t)),float(p)) for t,p in prob_rows]
    if len(rows)!=120 or abs(sum(p for _,p in rows)-1)>1e-6:
        raise ValueError("probability_board_invalid")
    from itertools import permutations
    import math
    keys=[combo for combo,_ in rows]
    valid={"-".join(map(str,t)) for t in permutations(range(1,7),3)}
    if len(set(keys))!=120 or set(keys)!=valid or any(not math.isfinite(p) or p<0 for _,p in rows):
        raise ValueError("probability_board_invalid")
    ranked=sorted(rows,key=lambda item:(-item[1],item[0]))
    # Provisional new-generation count ladder, not a claim of historically agreed exact counts.
    # All modes use probability estimates, not unverified official odds.
    counts={"narrow":5,"hit":10,"balance":16,"hole":22}
    remaining=list(ranked)
    diverse=[]
    while remaining:
        firsts={combo[0] for combo,_ in diverse}
        pairs={combo[:3] for combo,_ in diverse}
        best=max(remaining,key=lambda x:(x[1]*(1+(0.30 if x[0][0] not in firsts else 0)+(0.15 if x[0][:3] not in pairs else 0)),x[1],x[0]))
        diverse.append(best)
        remaining.remove(best)
    # Moderate-hole: exclude the ten most likely tickets but avoid a tiny-probability tail.
    ordering={"narrow":ranked[:5],"hit":ranked[:10],"balance":diverse[:16],
              "hole":ranked[10:32]}
    modes={}
    for name,selected in ordering.items():
        total=sum(p for _,p in selected)
        modes[name]={"tickets":[{"combo":combo,"p":round(p*100,5)} for combo,p in selected],
                     "estimated_coverage_pct":round(total*100,2),
                     "target_hit_rate_pct":round(TARGETS[name]*100,1),
                     "target_met_by_estimate":total>=TARGETS[name],
                     "actual_hit_rate_pct":None,
                     "count_policy":"provisional_new_generation_v2"}
    assert ticket_order_audit(modes)["status"]=="pass"
    return modes


def research_hole_candidates(prob_rows, count=12):
    """Read-only mid-range comparison; never used for saved/live forecasts.

    Probabilities are uncalibrated estimates, not official odds.
    Choose the moderately likely non-top-ten outcomes, rather than
    targeting the near-0.4% extreme tail.
    """
    rows=[("-".join(map(str,t)),float(p)) for t,p in prob_rows]
    if len(rows)!=120 or len({combo for combo,_ in rows})!=120 or abs(sum(p for _,p in rows)-1)>1e-6:
        raise ValueError("probability_board_invalid")
    if not isinstance(count,int) or isinstance(count,bool) or not 1<=count<=30:
        raise ValueError("invalid_research_count")
    ranked=sorted(rows,key=lambda item:(-item[1],item[0]))
    eligible=ranked[10:]
    selected=eligible[:count]
    return {"research_only":True,"official_odds_verified":False,
            "selection":"probability_rank_11_onwards",
            "tickets":[{"combo":combo,"p":round(p*100,5)} for combo,p in selected],
            "estimated_coverage_pct":round(sum(p for _,p in selected)*100,2)}



def compare_hole_candidates(prob_rows, official_odds=None, confirmed_finish=None):
    """Research-only single-race comparison; no fabricated odds or results.

    An externally verified source must supply odds/finish; this function
    never collects data or alters saved forecasts.
    """
    normalized=[(tuple(t),float(p)) for t,p in prob_rows]
    keys=[t for t,_ in normalized]
    from itertools import permutations
    import math
    if (len(keys)!=120 or set(keys)!=set(permutations(range(1,7),3)) or
            any(not math.isfinite(p) or p<0 for _,p in normalized) or
            abs(sum(p for _,p in normalized)-1)>1e-6):
        raise ValueError("probability_board_invalid")
    normalized.sort(key=lambda item:(-item[1],item[0]))
    legacy=rank_modes(normalized)["hole"]["tickets"]
    moderate=research_hole_candidates(normalized)["tickets"]
    if official_odds is not None:
        if (not isinstance(official_odds,dict) or len(official_odds)!=120 or
                any(type(v) not in (int,float) or not __import__("math").isfinite(v)
                    or v<1 or v>1000000 for v in official_odds.values())):
            raise ValueError("unverified_odds_board")
        expected={"-".join(map(str,t)) for t,_ in prob_rows}
        if set(official_odds)!=expected:
            raise ValueError("unverified_odds_board")
    if confirmed_finish is not None and confirmed_finish not in {"-".join(map(str,t)) for t,_ in prob_rows}:
        raise ValueError("invalid_confirmed_finish")
    def summarize(tickets):
        combos={t["combo"] for t in tickets}
        odds=[official_odds[t] for t in combos] if official_odds is not None else None
        return {"ticket_count":len(combos),
                "estimated_coverage_pct":round(sum(t["p"] for t in tickets),5),
                "official_odds_range":([min(odds),max(odds)] if odds is not None else None),
                "hit":(confirmed_finish in combos if confirmed_finish is not None else None)}
    return {"research_only":True,"historical_formal_evidence":False,
            # A passed-in value is not independently authenticated or timestamped.
            "odds_supplied":official_odds is not None,
            "result_supplied":confirmed_finish is not None,
            "odds_verified":False,
            "result_verified":False,
            "legacy_extreme":summarize(legacy),
            "moderate_candidate":summarize(moderate)}


def ticket_order_audit(modes):
    """Audit the agreed count contract without altering archived predictions."""
    names=("narrow","hit","balance","hole")
    counts={}
    for name in names:
        mode=modes.get(name)
        tickets=mode.get("tickets") if isinstance(mode,dict) else None
        if not isinstance(tickets,list):
            return {"status":"unknown","counts":counts,
                    "required_order":"narrow < hit < balance < hole"}
        counts[name]=len(tickets)
    ordered=all(counts[a] < counts[b] for a,b in zip(names,names[1:]))
    return {"status":"pass" if ordered else "mismatch","counts":counts,
            "required_order":"narrow < hit < balance < hole"}


def load_archived(code):
    path=Path(__file__).resolve().parent/"four_mode_forecasts"/(code+".json")
    if path.is_symlink():raise ValueError("archive_symlink")
    if path.is_file():
        raw=path.read_bytes()
    else:
        url="https://raw.githubusercontent.com/ikst2512-eng/boat-edge-clean/main/four_mode_forecasts/"+code+".json"
        try:
            with urlopen(Request(url,headers={"User-Agent":"CLEAN-FOUR-MODES/1.0"}),timeout=4) as response:
                raw=response.read(30001)
        except HTTPError as exc:
            if exc.code==404:return None
            raise
        except (URLError,TimeoutError,OSError):
            return None
    if len(raw)>30000:raise ValueError("archive_oversize")
    d=json.loads(raw)
    if (not isinstance(d,dict) or d.get("race_code")!=code or
        d.get("schema")!="CLEAN_FOUR_MODES_PREDEADLINE_V1" or
        d.get("target_rates_not_proven") is not True or
        not isinstance(d.get("modes"),dict)):
        raise ValueError("archive_invalid")
    saved=datetime.fromisoformat(d["generated_at_jst"])
    deadline=datetime.fromisoformat(d["deadline_jst"])
    if not saved.utcoffset() or not deadline.utcoffset() or saved>=deadline:
        raise ValueError("archive_time_invalid")
    return {"ok":True,"status":"provisional","validated":False,
            "snapshot_type":"archived_proof_pending",
            "model_version":d["model_version"],"race_code":code,
            "deadline_jst":d["deadline_jst"],"generated_at_jst":d["generated_at_jst"],
            "source_sha256":d["source_sha256"],
            "beforeinfo":d.get("beforeinfo"),"targets_are_not_realized_hit_rates":True,
            "modes":d["modes"],"ticket_order_audit":ticket_order_audit(d["modes"])}



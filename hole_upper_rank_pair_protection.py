"""Outcome-blind rank insertion with pair-coverage preservation (historical research only)."""
import json
from collections import Counter
from pathlib import Path
from four_mode_archive_api import archived_four_modes
from four_mode_frozen_diagnostic import compare_race
from four_mode_historical_cohort import run as cohort_run

ROOT = Path(__file__).resolve().parent
TOPS = (3, 5, 10)

def propose(hole, donor, insert_rank=3, max_tickets=10):
    base = list(hole[:max_tickets])
    if insert_rank not in (3, 5) or len(base) < insert_rank:
        return base
    pairs = [tuple(t.split("-")[:2]) for t in base]
    counts = Counter(pairs)
    heads = {head for head, _ in pairs}
    used = set(base)
    candidate = next((t for t in donor if t not in used
                      and t.split("-")[0] in heads
                      and tuple(t.split("-")[:2]) not in counts), None)
    if candidate is None:
        return base
    # Only evict redundant coverage at or after insertion. Prefer lowest rank.
    remove_idx = next((i for i in range(len(base)-1, insert_rank-2, -1)
                       if counts[pairs[i]] > 1), None)
    if remove_idx is None:
        return base
    updated = base[:]
    updated.pop(remove_idx)
    updated.insert(insert_rank-1, candidate)
    if len(updated) != len(base) or len(set(updated)) != len(updated):
        raise ValueError("invalid_ticket_budget")
    if not set(pairs).issubset({tuple(t.split("-")[:2]) for t in updated}):
        raise ValueError("pair_coverage_lost")
    return updated

def run(root=ROOT, limit=120):
    root = Path(root)
    cohort = cohort_run(root=root, limit=limit)
    if cohort.get("status") != "historical_research_only":
        return {"status":"no_paired_archives", "formal":False}
    scenarios = {f"{source}_rank{rank}":{"changed":0,
          "topn":{f"top{k}":{"gained":0,"lost":0} for k in TOPS}}
          for source in ("hit","balance","hit_balance") for rank in (3,5)}
    case_rows=[]
    for code in cohort["cohort_codes"]:
        row = compare_race(code, root)
        if row.get("status") != "historical_comparison_only":
            continue
        status, archived = archived_four_modes(code, root)
        if status != 200:
            raise ValueError("archive_unavailable")
        modes={name:[t["combo"] for t in archived["modes"][name]["tickets"]]
               for name in ("hole","hit","balance")}
        original=modes["hole"][:10]
        donors={"hit":modes["hit"],"balance":modes["balance"],
                "hit_balance":list(dict.fromkeys(modes["hit"]+modes["balance"]))}
        winner=row["winning_ticket"]
        cases={}
        for source, donor in donors.items():
            for rank in (3,5):
                key=f"{source}_rank{rank}"
                picks=propose(original,donor,rank)
                s=scenarios[key]
                changed=picks!=original
                s["changed"]+=int(changed)
                diff={"added":[t for t in picks if t not in original],
                      "removed":[t for t in original if t not in picks]}
                if len(diff["added"])!=len(diff["removed"]) or len(picks)!=len(original):
                    raise ValueError("invalid_change")
                for k in TOPS:
                    before=winner in original[:k]
                    after=winner in picks[:k]
                    s["topn"][f"top{k}"]["gained"]+=int(after and not before)
                    s["topn"][f"top{k}"]["lost"]+=int(before and not after)
                cases[key]=diff
        case_rows.append({"race_code":code,"winning_ticket":winner,"changes":cases})
    return {"status":"historical_research_only","formal":False,
      "simulated_only":True,"production_forecast_changed":False,
      "remote_first_seen_verified":False,"comparable":len(case_rows),
      "scenarios":scenarios,"case_rows":case_rows,
      "warning":"In-sample archival study; no independent first-publication verification or prospective efficacy."}

if __name__=="__main__":
    print(json.dumps(run(),ensure_ascii=False,sort_keys=True))

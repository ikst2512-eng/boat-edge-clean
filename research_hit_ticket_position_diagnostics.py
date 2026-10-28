"""Diagnose why 10-ticket hit mode loses coverage (research only).

Only archived predeadline selections and already confirmed results are read.
A hypothetical perfect-knowledge 10-ticket selector is NOT a deployable policy.
"""
import json
from collections import Counter
from pathlib import Path

ROOT=Path(__file__).resolve().parent
def analyze(history,root=ROOT):
    if history.get("schema")!="CLEAN_VERIFIED_FOUR_MODE_HISTORY_V1":
        raise ValueError("verified_history_required")
    races=history["races"]
    if len({r["race_code"] for r in races})!=len(races):
        raise ValueError("duplicate_races")
    ranks=Counter()
    by_boat=Counter()
    examples=[]
    for race in races:
        code=race["race_code"]
        archive=json.loads((root/"four_mode_forecasts"/(code+".json")).read_text(encoding="utf-8"))
        if archive.get("race_code")!=code or archive.get("schema")!="CLEAN_FOUR_MODES_PREDEADLINE_V1":
            raise ValueError("archive_mismatch")
        picks=[t["combo"] for t in archive["modes"]["hit"]["tickets"]]
        if len(picks)!=len(set(picks)):
            raise ValueError("duplicate_tickets")
        finish=race["finish"]
        index=picks.index(finish) if finish in picks else -1
        if (index>=0)!=race["modes"]["hit"]["hit"]:
            raise ValueError("verified_history_disagrees")
        if index>=0:
            bucket=f"{5*(index//5)+1}-{5*(index//5+1)}"
            ranks[bucket]+=1
            if index>=10:
                by_boat[finish.split("-")[0]]+=1
                examples.append({"race_code":code,"finish":finish,"saved_ticket_position":index+1})
    return {"schema":"CLEAN_HIT_COVERAGE_LOSS_DIAGNOSTICS_V1",
            "research_only":True,"sample_races":len(races),
            "winning_ticket_position_buckets":dict(sorted(ranks.items(),key=lambda x:int(x[0].split("-")[0]))),
            "hits_in_first_10_saved_tickets":sum(v for k,v in ranks.items() if int(k.split("-")[0])<=10),
            "wins_in_saved_positions_11_plus":sum(v for k,v in ranks.items() if int(k.split("-")[0])>=11),
            "excluded_winner_first_boats":dict(sorted(by_boat.items())),
            "excluded_race_examples":examples[:30],
            "rank_semantics":"original_ticket_order_not_calibrated_probability_rank"}

if __name__=="__main__":
    h=json.loads((ROOT/"four_mode_performance"/"history-10000.json").read_text(encoding="utf-8"))
    print(json.dumps(analyze(h),ensure_ascii=False,indent=2))

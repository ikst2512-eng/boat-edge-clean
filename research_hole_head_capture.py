"""Evaluate the head candidate restriction using only saved before-deadline model inputs.

This does NOT evaluate hole tickets or ROI, because pre-deadline odds are missing.
"""
import json
from pathlib import Path
from research_model import probabilities

ROOT=Path(__file__).resolve().parent

def first_place_candidates(rates, n):
    if n not in (1, 2, 3):
        raise ValueError("invalid_head_count")
    scores = {str(i): 0.0 for i in range(1, 7)}
    for combo, prob in probabilities(rates):
        scores[str(combo[0])] += prob
    return tuple(sorted(scores, key=lambda b: (-scores[b], b))[:n])

def analyze(history, root=ROOT):
    if history.get("schema")!="CLEAN_VERIFIED_FOUR_MODE_HISTORY_V1" or history.get("budget_yen")!=10000:
        raise ValueError("verified_history_required")
    seen=set()
    counts={"one_head":0,"two_heads":0,"three_heads":0,"original_hole_head":0}
    distinct_heads={}
    for race in history["races"]:
        code=race["race_code"]
        if code in seen:
            raise ValueError("duplicate_race")
        seen.add(code)
        archive=json.loads((root/"four_mode_forecasts"/(code+".json")).read_text(encoding="utf-8"))
        if archive.get("race_code")!=code or archive.get("schema")!="CLEAN_FOUR_MODES_PREDEADLINE_V1":
            raise ValueError("archive_mismatch")
        finish=race["finish"]
        if finish not in ["-".join(map(str, t)) for t,p in probabilities(archive["input_national_win_rates"])]:
            raise ValueError("invalid_result")
        head=finish[0]
        counts["one_head"]+=int(head in first_place_candidates(archive["input_national_win_rates"],1))
        counts["two_heads"]+=int(head in first_place_candidates(archive["input_national_win_rates"],2))
        counts["three_heads"]+=int(head in first_place_candidates(archive["input_national_win_rates"],3))
        original={str(t["combo"][0]) for t in archive["modes"]["hole"]["tickets"]}
        distinct_heads[len(original)]=distinct_heads.get(len(original),0)+1
        counts["original_hole_head"]+=int(head in original)
    n=len(seen)
    return {"schema":"CLEAN_RESEARCH_HOLE_HEAD_DIAGNOSTICS_V1","sample_races":n,
            "predeadline_odds_available":False,"hole_ticket_hit_rates":None,"hole_roi":None,
            "head_candidate_capture_counts":counts,
            "head_candidate_capture_pct":{k:round(100*v/n,2) if n else None for k,v in counts.items()},
            "original_hole_distinct_head_counts":dict(sorted(distinct_heads.items())),
            "note":"Head-only upper bound; not a winning trifecta or payout estimate."}

if __name__=="__main__":
    h=json.loads((ROOT/"four_mode_performance"/"history-10000.json").read_text(encoding="utf-8"))
    print(json.dumps(analyze(h),ensure_ascii=False,indent=2))

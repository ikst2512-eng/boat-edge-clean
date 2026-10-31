"""Isolated research-only late feature candidate; NOT an independently validated model.

The ranking is an explicit, frozen illustrative candidate using actual courses.
Do not publish as betting advice or claim lift until prospective evidence exists.
"""
import json
from itertools import permutations
from pathlib import Path
from scripts.late_preview_feature_pairs import build


def candidate(pair):
    boats=pair["boats"]
    if len(boats)!=6 or sorted(x["boat"] for x in boats)!=list(range(1,7)):
        raise ValueError("invalid boat identities")
    if sorted(x["entry_course"] for x in boats)!=list(range(1,7)):
        raise ValueError("invalid course permutation")
    # Preregistered mechanical baseline; intentionally does not fit to outcomes.
    # Prefer inner actual course, then exhibition time as a tiebreaker.
    ranked=sorted(boats,key=lambda x:(x["entry_course"],x["exhibition_time"],x["boat"]))
    ids=[x["boat"] for x in ranked]
    # Produce ten distinct trifectas without looking at race result or payout.
    tickets=["-".join(map(str,t)) for t in permutations(ids,3)]
    return {"race_code":pair["race_code"],"predictions":tickets[:10],
            "generated_from_received_at_jst":pair["both_sources_received_at_jst"],
            "model_version":"late-course-mechanical-baseline-v0",
            "status":"research_candidate_unvalidated","validated":False,
            "uses_features":["entry_course","exhibition_time"],
            "not_a_calibrated_probability":True}


def build_candidates(day, preview_root):
    pairs=build(day,preview_root)["records"]
    rows=[candidate(pair) for pair in pairs]
    return {"day":day,"count":len(rows),"predictions":rows,
            "research_only":True}


if __name__=="__main__":
    from research_model import JST
    from datetime import datetime
    print(json.dumps(build_candidates(datetime.now(JST).strftime("%Y%m%d"),
                                      Path("late_preview_evidence")),ensure_ascii=False))

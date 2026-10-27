"""Historical real-source collection rehearsal. NEVER persist or score predictions.

Reconstructs eligibility using published race CSV from 2026-10-27 at a
simulated 07:45 JST; retrieval occurs later, so not live cutoff evidence.
"""
import json
from datetime import datetime
from research_model import JST,BASE,read_rows
from collect_clean_prospective import build,VERSION

DAY="20261027"

def rehearse():
    path="2026/10/27.csv"
    titles,_,title_hash=read_rows(BASE+"title/"+path)
    cards,_,card_hash=read_rows(BASE+"race_cards/"+path)
    simulated=datetime(2026,10,27,7,45,tzinfo=JST)
    records=build(DAY,titles,cards,simulated,simulated,title_hash,card_hash,simulated,
                  {"model_git_sha":"0"*40,"model_source_sha256":"0"*64})
    if not records:raise RuntimeError("real title/cards produce zero valid predictions at 07:45")
    if any(r["formal"] or r["scoring"] or r["validated"] for r in records.values()):
        raise RuntimeError("rehearsal incorrectly promoted model")
    if any(len(r["predictions"])!=10 or r["generated_at"]!=simulated.isoformat() for r in records.values()):
        raise RuntimeError("invalid prediction replay")
    return {"day":DAY,"input_source":"real published title and race_cards CSV",
            "simulated_collection_jst":simulated.isoformat(),
            "source_retrieved_after_event":True,
            "eligible_races":len(records),"stored_prospective_forecasts":0,
            "eligible_sample":sorted(records)[:5],
            "formal_accuracy":None,"real_cutoff_attested":False}

if __name__=="__main__":
    print(json.dumps(rehearse(),ensure_ascii=False))

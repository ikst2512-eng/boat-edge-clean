"""Read-only audit of Nov4+ locally frozen hole research candidates.

Fail closed on source or candidate tampering. Same-job local freeze timestamps
and GitHub artifacts do NOT establish independent first-receipt evidence.
"""
import argparse
import hashlib
import json
from datetime import datetime,timedelta
from pathlib import Path

from four_mode_archive_api import archived_four_modes,valid_ticket
from four_mode_frozen_diagnostic import compare_race
from hole_future_locked_eval import FIRST_ELIGIBLE_DAY,LOCKED_SELECTION_BLOBS
from hole_third_choice_research import national_rates,variants

POLICIES=("baseline","donor_order","max_ticket_score","third_national_rate")
TOPS=(3,5,10)

def audit(root,shadow):
    root=Path(root);shadow=Path(shadow)
    if shadow.is_symlink() or not shadow.is_file():
        return {"status":"missing_shadow","formal":False,"comparable":0}
    data=json.loads(shadow.read_text(encoding="utf-8"))
    if data.get("status")!="research_only_after_confirmed_push" or not isinstance(data.get("records"),list):
        return {"status":"unusable_shadow","formal":False,"comparable":0}
    hits={p:{f"top{k}":0 for k in TOPS} for p in POLICIES}
    missing={};rows=[];seen=set()
    def exclude(reason):
        missing[reason]=missing.get(reason,0)+1
    for record in data["records"]:
        code=record.get("race_code")
        if not isinstance(code,str) or len(code)!=12 or not code.isdigit() or code in seen:
            raise ValueError("invalid_or_duplicate_code")
        seen.add(code)
        if code[:8]<FIRST_ELIGIBLE_DAY.strftime("%Y%m%d"):
            exclude("not_future_eligible");continue
        if record.get("status")!="shadow_frozen_unverified":
            exclude("not_frozen");continue
        state,archive=archived_four_modes(code,root)
        if state!=200:
            exclude("invalid_archive");continue
        path=root/"four_mode_forecasts"/(code+".json")
        if path.is_symlink() or hashlib.sha256(path.read_bytes()).hexdigest()!=record.get("source_sha256"):
            exclude("source_hash_mismatch");continue
        freeze_at=datetime.fromisoformat(record["local_freeze_at_jst"])
        deadline=datetime.fromisoformat(archive["deadline_jst"])
        if (freeze_at.utcoffset()!=timedelta(hours=9) or deadline.utcoffset()!=timedelta(hours=9)
                or freeze_at>=deadline or record.get("deadline_jst")!=archive["deadline_jst"]):
            exclude("local_timing_invalid");continue
        picks=record.get("future_locked_candidates")
        if not isinstance(picks,dict) or set(picks)!=set(POLICIES):
            exclude("locked_candidates_missing");continue
        if record.get("future_locked_selector_git_blobs")!=LOCKED_SELECTION_BLOBS:
            exclude("selection_method_mismatch");continue
        expected=variants(archive,national_rates(code,root))
        if any(not isinstance(picks[p],list) or picks[p]!=expected[p] or
               len(set(picks[p]))!=len(picks[p]) or any(not valid_ticket(t) for t in picks[p])
               for p in POLICIES):
            exclude("candidate_replay_mismatch");continue
        if any(picks[p][:5]!=picks["baseline"][:5] for p in POLICIES):
            exclude("top5_changed");continue
        result=compare_race(code,root)
        if result.get("status")!="historical_comparison_only":
            exclude("unconfirmed_result");continue
        winner=result["winning_ticket"]
        flags={}
        for p in POLICIES:
            flags[p]={f"top{k}":winner in picks[p][:k] for k in TOPS}
            for k in TOPS:hits[p][f"top{k}"]+=int(flags[p][f"top{k}"])
        rows.append({"race_code":code,"flags":flags})
    delta={}
    for p in POLICIES[1:]:
        delta[p]={}
        for k in TOPS:
            key=f"top{k}"
            gained=sum(int(x["flags"][p][key] and not x["flags"]["baseline"][key]) for x in rows)
            lost=sum(int(x["flags"]["baseline"][key] and not x["flags"][p][key]) for x in rows)
            if hits[p][key]-hits["baseline"][key]!=gained-lost:
                raise ValueError("bad_attribution")
            delta[p][key]={"gained":gained,"lost":lost,"net":gained-lost}
    return {"schema":"HOLE_FUTURE_SHADOW_REPLAY_V1",
            "status":"research_only_matched_local_freezes" if rows else "no_comparable_future_shadows",
            "formal":False,"independent_first_receipt_verified":False,
            "prospective_validation":False,"production_forecast_changed":False,
            "comparable":len(rows),"excluded_by_reason":missing,"hits":hits,"delta":delta,"rows":rows,
            "warning":"Same-job freeze is unverified by independent remote first receipt; do not claim formal predeadline accuracy."}

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--root",default=".")
    p.add_argument("--shadow",required=True)
    args=p.parse_args()
    print(json.dumps(audit(args.root,args.shadow),ensure_ascii=False,sort_keys=True))

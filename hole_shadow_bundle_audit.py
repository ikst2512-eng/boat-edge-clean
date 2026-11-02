"""Read-only hole shadow comparison; no formal accuracy without independent receipt proof."""
import argparse
import hashlib
import json
import re
from pathlib import Path
from four_mode_archive_api import archived_four_modes, valid_ticket
from four_mode_frozen_diagnostic import compare_race

TOPS=(3,5,10)
FIELDS=("baseline","shadow","shadow_bundle2")

def audit(root,shadow_path):
    root=Path(root);shadow_path=Path(shadow_path)
    if shadow_path.is_symlink() or not shadow_path.is_file():
        return {"status":"missing_shadow","formal":False}
    report=json.loads(shadow_path.read_text(encoding="utf-8"))
    records=report.get("records")
    if report.get("status")!="research_only_after_confirmed_push" or not isinstance(records,list):
        return {"status":"unusable_shadow","formal":False}
    totals={field:{f"top{k}":0 for k in TOPS} for field in FIELDS}
    rows=[]; excluded=[]
    seen=set()
    for record in records:
        code=record.get("race_code")
        if not isinstance(code,str) or not re.fullmatch(r"20[0-9]{10}",code) or code in seen:
            raise ValueError("invalid_or_duplicate_race")
        seen.add(code)
        if record.get("status")!="shadow_frozen_unverified":
            excluded.append({"race_code":code,"reason":"not_frozen"});continue
        status,archive=archived_four_modes(code,root)
        if status!=200:
            excluded.append({"race_code":code,"reason":"missing_archive"});continue
        path=root/"four_mode_forecasts"/(code+".json")
        if path.is_symlink() or hashlib.sha256(path.read_bytes()).hexdigest()!=record.get("source_sha256"):
            excluded.append({"race_code":code,"reason":"source_hash_mismatch"});continue
        if record.get("deadline_jst")!=archive["deadline_jst"]:
            excluded.append({"race_code":code,"reason":"deadline_mismatch"});continue
        base=record.get("baseline")
        original=[x["combo"] for x in archive["modes"]["hole"]["tickets"]][:10]
        if base!=original:
            excluded.append({"race_code":code,"reason":"baseline_mismatch"});continue
        candidate_sets={}
        for field in FIELDS:
            picks=record.get(field)
            if (not isinstance(picks,list) or len(picks)!=len(base)
                or len(set(picks))!=len(picks)
                or any(not valid_ticket(t) for t in picks)):
                raise ValueError("invalid_frozen_tickets_"+code+"_"+field)
            candidate_sets[field]=picks
        result=compare_race(code,root)
        if result.get("status")!="historical_comparison_only":
            excluded.append({"race_code":code,"reason":"unconfirmed_result"});continue
        winner=result["winning_ticket"]
        flags={}
        for field,picks in candidate_sets.items():
            flags[field]={f"top{k}":winner in picks[:k] for k in TOPS}
            for k in TOPS:totals[field][f"top{k}"]+=int(flags[field][f"top{k}"])
        rows.append({"race_code":code,"flags":flags})
    n=len(rows)
    changes={}
    for field in ("shadow","shadow_bundle2"):
        changes[field]={}
        for k in TOPS:
            key=f"top{k}"
            gained=sum(x["flags"][field][key] and not x["flags"]["baseline"][key] for x in rows)
            lost=sum(x["flags"]["baseline"][key] and not x["flags"][field][key] for x in rows)
            changes[field][key]={"gained":gained,"lost":lost,"net":gained-lost}
            if totals[field][key]-totals["baseline"][key]!=gained-lost:
                raise ValueError("attribution")
    return {"schema":"HOLE_SHADOW_BUNDLE_AUDIT_V1",
            "status":"retrospective_shadow_comparison" if n else "no_comparable_shadow",
            "formal":False,"independent_first_receipt_verified":False,
            "prospective_validation":False,"production_forecast_changed":False,
            "comparable":n,"excluded":excluded,"hits":totals,"delta":changes,"rows":rows,
            "warning":"Same-job post-publication snapshots are not independent first-receipt proof. Never claim formal predeadline accuracy."}

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--root",default=".")
    p.add_argument("--shadow",required=True)
    args=p.parse_args()
    print(json.dumps(audit(args.root,args.shadow),ensure_ascii=False,sort_keys=True))

"""Read-only PR16 prospective pair preflight; never loads outcomes or attests receipts."""
import argparse
import json
import hashlib
import math
import re
from datetime import datetime
from pathlib import Path
from paired_compare import TICKETS, timestamp

def inspect_pair(pair, source_snapshot_bytes=None):
    reasons=[]
    if not isinstance(pair,dict) or pair.get("status")!="research_unvalidated":
        return {"ready_for_scoring":False,"distribution_structure_valid":False,
                "source_snapshot_digest_verified_locally":False,
                "reasons":["not a research prospective pair"]}
    code=pair.get("race_code")
    if not isinstance(code,str) or not re.fullmatch(r"20[0-9]{10}",code):
        reasons.append("invalid canonical race code")
    else:
        try:
            datetime.strptime(code[:8],"%Y%m%d")
            if not 1<=int(code[8:10])<=24 or not 1<=int(code[10:12])<=12:
                reasons.append("race venue or number out of range")
        except ValueError:
            reasons.append("invalid race calendar date")
    if not isinstance(pair.get("source_snapshot_sha256"),str) or not re.fullmatch(r"[0-9a-f]{64}",pair["source_snapshot_sha256"]):
        reasons.append("missing source snapshot digest")
    source_snapshot_checked = False
    if source_snapshot_bytes is None:
        reasons.append("source snapshot original bytes not supplied")
    else:
        if not isinstance(source_snapshot_bytes,bytes):
            reasons.append("invalid source snapshot bytes")
        else:
            try:
                original=json.loads(source_snapshot_bytes)
                canonical=json.dumps(original,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode("utf-8")
                digest=hashlib.sha256(canonical).hexdigest()
                if digest!=pair.get("source_snapshot_sha256"):
                    reasons.append("source snapshot bytes mismatch")
                if original.get("race_code")!=code:
                    reasons.append("source snapshot race mismatch")
                if original.get("status")!="research" or original.get("validated") is not False:
                    reasons.append("source snapshot not unvalidated research")
                if (digest==pair.get("source_snapshot_sha256") and original.get("race_code")==code
                    and original.get("status")=="research" and original.get("validated") is False):
                    source_snapshot_checked = True
            except (ValueError,TypeError,AttributeError):
                reasons.append("invalid source snapshot JSON")
    for key in ("baseline_model_id","candidate_model_id"):
        if not isinstance(pair.get(key),str) or not pair[key].strip():
            reasons.append("missing "+key)
    if not isinstance(pair.get("candidate_git_blob_sha"),str) or not re.fullmatch(r"[0-9a-f]{40}",pair["candidate_git_blob_sha"]):
        reasons.append("invalid candidate model blob identity")
    for name in ("baseline","candidate"):
        p=pair.get(name)
        if not isinstance(p,dict) or set(p)!=TICKETS:
            reasons.append(name+": incomplete 120-ticket distribution")
        elif any(type(v) not in (int,float) or not math.isfinite(v) or v<=0 for v in p.values()) or abs(math.fsum(p.values())-1)>1e-7:
            reasons.append(name+": invalid probability distribution")
    if pair.get("prospective_verified") is not False:
        reasons.append("unexpected prospective verification claim")
    try:
        frozen=timestamp(pair["frozen_at_jst"])
        cutoff=timestamp(pair["cutoff_jst"])
        generated=timestamp(pair["source_snapshot_generated_at"])
        if generated>frozen or frozen>=cutoff:
            reasons.append("inconsistent pre-cutoff chronology")
    except (KeyError,TypeError,ValueError,AttributeError):
        reasons.append("missing or invalid chronology")
    if pair.get("entry_status")!="assumed_identity_not_verified":
        reasons.append("unknown entry provenance")
    return {"ready_for_scoring":False,
            "source_snapshot_digest_verified_locally":source_snapshot_checked,
            "distribution_structure_valid":not any("distribution" in x for x in reasons),
            "reasons":reasons+[
              "requires independently verified server first-seen commit and exact pair bytes",
              "requires original source-byte receipts, preregistration and both model identities",
              "requires independently verified permitted outcome and official deadline",
            ]}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("pair",type=Path)
    parser.add_argument("--source-snapshot",type=Path,help="optional original research snapshot for digest binding")
    args=parser.parse_args()
    source=args.source_snapshot.read_bytes() if args.source_snapshot else None
    print(json.dumps(inspect_pair(json.loads(args.pair.read_text(encoding="utf-8")),source),ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()

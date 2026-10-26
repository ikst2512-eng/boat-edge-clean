"""Read-only PR16 prospective pair preflight; never loads outcomes or attests receipts."""
import argparse
import json
import math
from pathlib import Path
from paired_compare import TICKETS, timestamp

def inspect_pair(pair):
    reasons=[]
    if not isinstance(pair,dict) or pair.get("status")!="research_unvalidated":
        return {"ready_for_scoring":False,"reasons":["not a research prospective pair"]}
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
    if pair.get("candidate_git_blob_sha") is None:
        reasons.append("missing candidate model blob identity")
    return {"ready_for_scoring":False,
            "distribution_structure_valid":not any("distribution" in x for x in reasons),
            "reasons":reasons+[
              "requires independently verified server first-seen commit and exact pair bytes",
              "requires original source-byte receipts, preregistration and both model identities",
              "requires independently verified permitted outcome and official deadline",
            ]}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("pair",type=Path)
    args=parser.parse_args()
    print(json.dumps(inspect_pair(json.loads(args.pair.read_text(encoding="utf-8"))),ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()

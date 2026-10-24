"""Offline verification of a nonpublic candidate and its separate audit receipt.

Does not upgrade a candidate to formal Fresh or infer GitHub arrival time.
"""
import argparse
import hashlib
import json
from pathlib import Path
from fresh_feed_builder import canonical, VALID

def verify(candidate_path,receipt_path):
    p=Path(candidate_path); q=Path(receipt_path)
    if p.is_symlink() or q.is_symlink():
        raise ValueError("symlink prohibited")
    raw=p.read_bytes()
    candidate=json.loads(raw)
    audit=json.loads(q.read_bytes())
    if not isinstance(candidate,dict) or not isinstance(audit,dict):
        raise ValueError("invalid evidence object")
    if (audit.get("schema")!="fresh-prospective-receipt-v1"
        or audit.get("status")!="candidate_only_not_formal_or_public"
        or audit.get("independent_github_arrival_verified") is not False
        or "freeze_proof" in candidate):
        raise ValueError("not nonpublic original evidence")
    if (audit.get("race_code")!=candidate.get("race_code")
        or p.name!=str(candidate.get("race_code"))+".json"
        or audit.get("deadline_at")!=candidate.get("deadline_at")
        or audit.get("source_snapshot_sha256")!=candidate.get("source_snapshot_sha256")
        or audit.get("candidate_sha256")!=hashlib.sha256(raw).hexdigest()):
        raise ValueError("receipt/candidate mismatch")
    probs=candidate.get("probabilities")
    if not isinstance(probs,dict) or set(probs)!=VALID:
        raise ValueError("missing full 120 probabilities")
    if candidate.get("validated") is not True:
        raise ValueError("unvalidated input")
    if any(type(v) not in (int,float) or not 0<=v<=1 for v in probs.values()):
        raise ValueError("invalid probability")
    if abs(sum(probs.values())-1)>1e-8:
        raise ValueError("unnormalized probabilities")
    return {"candidate_intact":True,"formal_approved":False,
            "github_arrival_verified":False,"race_code":candidate["race_code"]}

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("candidate");parser.add_argument("receipt")
    args=parser.parse_args()
    print(json.dumps(verify(args.candidate,args.receipt),sort_keys=True))

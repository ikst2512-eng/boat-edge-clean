"""Bind research pair file bytes to a server-observed push commit.

A passing result establishes that the exact frozen bytes are reachable at a
matching SHA with a server-side Actions timestamp before cutoff. Never infers
model improvement or certifies source inputs independently.
"""
import hashlib
from research_push_receipt_audit import audit_push_receipt

def audit_pair_blob(pair_bytes, pair_path, run, commit_sha, committed_blob_bytes):
    if not pair_path.startswith("research_prospective_pairs/") or not pair_path.endswith(".json"):
        raise ValueError("not a research pair path")
    import json
    pair=json.loads(pair_bytes)
    if pair_path.rsplit("/",1)[-1] != pair["race_code"]+".json":
        raise ValueError("path/race mismatch")
    same_bytes = hashlib.sha256(pair_bytes).digest() == hashlib.sha256(committed_blob_bytes).digest()
    receipt=audit_push_receipt(pair,run,commit_sha)
    return {**receipt,"file_blob_matches_commit":same_bytes,
            "remote_pair_evidence":bool(same_bytes and receipt["server_observed_pre_cutoff"]),
            "prospective_hit_rate_verified":False}

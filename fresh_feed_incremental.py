"""Merge already published forecasts with new verified candidates without mutating prior entries.

Writes a new versioned feed, not the currently published file. Promote the
new artifact only with a compare-and-swap Git commit against the expected
parent revision. This module does not perform such promotion.
"""
import hashlib
import json
from pathlib import Path
from fresh_feed_batch import race_key
from fresh_feed_builder import canonical
from fresh_feed_isolated import collect

def merge(existing, candidates):
    if not isinstance(existing, dict) or not isinstance(candidates, dict):
        raise ValueError("feed dictionaries required")
    combined={}
    for key,record in existing.items():
        if not isinstance(record,dict) or race_key(record.get("race_code"))!=key:
            raise ValueError("invalid existing record")
        combined[key]=record
    added=[]; unchanged=[]
    for key,record in candidates.items():
        if not isinstance(record,dict) or race_key(record.get("race_code"))!=key:
            raise ValueError("invalid candidate")
        if key in combined:
            if canonical(combined[key]) != canonical(record):
                raise ValueError("published race mutation blocked")
            unchanged.append(key)
        else:
            combined[key]=record
            added.append(key)
    return {k:combined[k] for k in sorted(combined)},sorted(added),sorted(unchanged)

def stage(existing_path,manifest_path,output_path,audit_path,resolver=None):
    src=Path(existing_path);dest=Path(output_path);audit=Path(audit_path)
    if len({str(p.resolve()) for p in (src,dest,audit)}) != 3:
        raise ValueError("paths must differ")
    if dest.exists() or audit.exists():
        raise FileExistsError("versioned artifact already exists")
    source=src.read_bytes() if src.exists() else b"{}\n"
    existing=json.loads(source)
    entries=json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    kwargs={} if resolver is None else {"resolver":resolver}
    accepted,rejected=collect(entries,**kwargs)
    merged,added,unchanged=merge(existing,accepted)
    if not added:
        raise ValueError("no new verified candidates")
    report={"previous_sha256":hashlib.sha256(source).hexdigest(),
            "new_sha256":hashlib.sha256(canonical(merged)).hexdigest(),
            "added":added,"unchanged":unchanged,"rejected":rejected,
            "independent_timestamp_verified":False,
            "deployment_status":"staged_not_published"}
    dest.parent.mkdir(parents=True,exist_ok=True)
    audit.parent.mkdir(parents=True,exist_ok=True)
    with audit.open("xb") as f:f.write(canonical(report))
    with dest.open("xb") as f:f.write(canonical(merged))
    return report

if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument("--existing",required=True)
    p.add_argument("--manifest",required=True)
    p.add_argument("--out",required=True)
    p.add_argument("--audit",required=True)
    a=p.parse_args()
    print(json.dumps(stage(a.existing,a.manifest,a.out,a.audit),ensure_ascii=False))

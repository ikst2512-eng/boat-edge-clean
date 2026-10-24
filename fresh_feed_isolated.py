"""Isolated candidate feed assembly with explicit rejection audit.

Never silently skip malformed manifest structures or duplicate race codes.
This does not certify independent pre-deadline publication.
"""
import json
from pathlib import Path
from fresh_feed_batch import race_key
from fresh_feed_builder import canonical
from fresh_feed_publisher import assemble

def collect(entries, resolver=assemble):
    if not isinstance(entries,list) or not entries:
        raise ValueError("nonempty list required")
    accepted, rejected, seen = {}, [], set()
    for index,entry in enumerate(entries):
        if not isinstance(entry,dict) or set(entry)!={"commit_sha","race_code","deadline_at"}:
            raise ValueError("invalid manifest structure")
        code=entry["race_code"]
        key=race_key(code)
        if key in seen:
            raise ValueError("duplicate race in manifest")
        seen.add(key)
        try:
            record=resolver(entry["commit_sha"],code,entry["deadline_at"])
            if not isinstance(record,dict) or record.get("race_code")!=code or not isinstance(record.get("freeze_proof"),dict):
                raise ValueError("invalid verified record")
            accepted[key]=record
        except (ValueError,KeyError,TypeError,OSError,TimeoutError) as exc:
            rejected.append({"race_code":code,"reason":type(exc).__name__})
    return {k:accepted[k] for k in sorted(accepted)}, rejected

def publish(manifest_path,feed_path,audit_path,resolver=assemble):
    feed_destination=Path(feed_path);audit_destination=Path(audit_path)
    if feed_destination.resolve()==audit_destination.resolve():
        raise ValueError("feed and audit paths must differ")
    if feed_destination.exists() or audit_destination.exists():
        raise FileExistsError("destination already exists")
    entries=json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    accepted,rejected=collect(entries,resolver)
    if not accepted:
        raise ValueError("no verified forecasts; nothing published")
    feed_destination.parent.mkdir(parents=True,exist_ok=True)
    audit_destination.parent.mkdir(parents=True,exist_ok=True)
    # Write the audit first, then feed. Never rewrite existing artifacts.
    with audit_destination.open("xb") as f:
        f.write(canonical({"accepted":list(accepted),"rejected":rejected,
                           "independent_timestamp_verified":False}))
    try:
        with feed_destination.open("xb") as f:
            f.write(canonical(accepted))
    except BaseException:
        # Preserve audit for incident investigation; no feed was successfully published.
        raise
    return len(accepted),len(rejected)

if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument("--manifest",required=True)
    p.add_argument("--out",required=True)
    p.add_argument("--audit",required=True)
    a=p.parse_args()
    print(publish(a.manifest,a.out,a.audit))

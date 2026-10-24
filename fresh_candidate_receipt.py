"""Produce a local, nonpublic audit receipt for a prospective Fresh candidate.

The runner's clock is informational, not independent GitHub arrival proof.
The externally issued Actions run id permits later verification via GitHub API.
"""
import argparse,hashlib,json,re
from datetime import datetime,timezone
from pathlib import Path
from fresh_feed_builder import canonical

def receipt(snapshot_path,run_id,run_attempt,now=None):
    if not re.fullmatch(r"[1-9][0-9]*",str(run_id)):
        raise ValueError("invalid workflow run id")
    if not re.fullmatch(r"[1-9][0-9]*",str(run_attempt)):
        raise ValueError("invalid run attempt")
    p=Path(snapshot_path)
    if p.is_symlink() or not p.is_file() or p.stat().st_size>100000:
        raise ValueError("missing or unsafe snapshot")
    raw=p.read_bytes()
    record=json.loads(raw)
    if p.name!=str(record.get("race_code"))+".json":
        raise ValueError("race id mismatch")
    if record.get("validated") is not True or "freeze_proof" in record:
        raise ValueError("not an unpromoted source")
    instant=now or datetime.now(timezone.utc)
    if instant.tzinfo is None or instant.utcoffset() is None:
        raise ValueError("timezone needed")
    return {
        "schema":"fresh-prospective-receipt-v1",
        "status":"candidate_only_not_formal_or_public",
        "race_code":record["race_code"],
        "source_snapshot_sha256":record["source_snapshot_sha256"],
        "candidate_sha256":hashlib.sha256(raw).hexdigest(),
        "workflow_run_id":int(run_id),
        "workflow_attempt":int(run_attempt),
        "runner_recorded_at":instant.isoformat(),
        "deadline_at":record["deadline_at"],
        "independent_github_arrival_verified":False,
    }

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--source",required=True)
    p.add_argument("--output",required=True)
    p.add_argument("--run-id",required=True)
    p.add_argument("--run-attempt",required=True)
    a=p.parse_args()
    dest=Path(a.output)
    dest.parent.mkdir(parents=True,exist_ok=True)
    with dest.open("xb") as stream:
        stream.write(canonical(receipt(a.source,a.run_id,a.run_attempt)))

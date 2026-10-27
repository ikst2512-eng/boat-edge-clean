"""Read-only first-add Git history audit for locally complete research snapshots.
Git commit dates can be forged. This is NOT a trusted remote receipt or outcome audit.
"""
import argparse
import json
import subprocess
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

from research_snapshot_inventory import REQUIRED

def git(*args, repo):
    return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()

def audit(repo, snapshot_dir):
    repo = Path(repo).resolve()
    root = Path(snapshot_dir).resolve()
    counts, exclusions = Counter(), Counter()
    for path in sorted(root.glob("*.json")):
        counts["files"] += 1
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
            if (not isinstance(record, dict) or record.get("race_code") != path.stem or
                record.get("validated") is not False or record.get("status") != "research" or
                any(not record.get(field) for field in REQUIRED)):
                exclusions["missing_or_invalid_local_metadata"] += 1
                continue
            cutoff = datetime.fromisoformat(record["cutoff_jst"])
            deadline = datetime.fromisoformat(record["source_deadline_jst"])
            generated = datetime.fromisoformat(record["generated_at"])
            if any(d.tzinfo is None or d.utcoffset() is None for d in (cutoff, deadline, generated)):
                exclusions["invalid_local_times"] += 1
                continue
            if cutoff != deadline - timedelta(minutes=12) or generated > cutoff:
                exclusions["invalid_local_cutoff"] += 1
                continue
            counts["local_candidates"] += 1
            relative = path.relative_to(repo).as_posix()
            raw = git("log", "--all", "--diff-filter=A", "--format=%H%x09%cI", "--", relative, repo=repo).splitlines()
            entries = [line.split("\t") for line in raw if "\t" in line]
            if len(entries) != 1:
                exclusions["first_add_ambiguous_or_absent"] += 1
                continue
            sha, committed_at = entries[0]
            original_blob = git("rev-parse", f"{sha}:{relative}", repo=repo)
            current_blob = git("hash-object", relative, repo=repo)
            if original_blob != current_blob:
                exclusions["original_blob_changed"] += 1
                continue
            counts["first_add_blob_matches"] += 1
            git_time = datetime.fromisoformat(committed_at)
            if git_time > cutoff:
                exclusions["commit_timestamp_after_cutoff"] += 1
                continue
            counts["git_commit_timestamp_before_cutoff"] += 1
            exclusions["remote_receipt_unverified"] += 1
        except (ValueError, KeyError, TypeError, OSError, subprocess.CalledProcessError):
            exclusions["invalid_or_unverifiable_record"] += 1
    return {"status":"GIT_LOCAL_AUDIT_NOT_FORMAL_SCORING",
            "counts":dict(counts), "exclusions":dict(exclusions),
            "trusted_remote_receipts_verified":0, "outcomes_verified":0,
            "note":"Commit timestamps and local blob identity do not prove trusted remote receipt. Never retroactively score or relabel forecasts."}

if __name__ == "__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--repo", default=".")
    p.add_argument("--snapshots", default="research_snapshots")
    args=p.parse_args()
    print(json.dumps(audit(args.repo,args.snapshots),ensure_ascii=False,indent=2))

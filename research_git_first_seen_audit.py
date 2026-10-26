"""Conservative Git first-seen research forecast audit.

Git commit timestamps are metadata and not trusted timestamps. This audit
reports chronological consistency and blob equivalence, not proof of prospective
prediction. Do not score or promote on this evidence alone.
"""
import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path


def _git(*args):
    return subprocess.check_output(["git", *args], text=True, stderr=subprocess.PIPE).strip()


def audit_one(path):
    path = Path(path)
    record = json.loads(path.read_text(encoding="utf-8"))
    code = record["race_code"]
    if path.stem != code:
        raise ValueError("race_code/filename mismatch")
    cutoff = datetime.fromisoformat(record["cutoff_jst"])
    generated = datetime.fromisoformat(record["generated_at"])
    if not cutoff.tzinfo or not generated.tzinfo:
        raise ValueError("timezone required")
    # Git's oldest path touch is *not* necessarily its first appearance after
    # rename/move; explicitly mark this method as indicative, never definitive.
    commits = _git("log", "--all", "--follow", "--format=%H", "--", str(path)).splitlines()
    if not commits:
        return {"race_code": code, "status": "no_history", "prospective_verified": False}
    first = commits[-1]
    commit_iso = _git("show", "-s", "--format=%cI", first)
    committed = datetime.fromisoformat(commit_iso)
    original = _git("show", f"{first}:{path.as_posix()}")
    # A modified later snapshot must never inherit early proof.
    unchanged = original.encode("utf-8") == path.read_bytes().rstrip(b"\n")
    before_cutoff = committed < cutoff
    return {"race_code": code, "first_commit": first,
            "first_commit_time": committed.isoformat(),
            "declared_generated_before_cutoff": generated < cutoff,
            "commit_metadata_before_cutoff": before_cutoff,
            "first_commit_blob_matches_current": unchanged,
            "status": "metadata_pre_cutoff" if before_cutoff and unchanged else "unproven",
            "prospective_verified": False}


def audit_all(directory):
    results = []
    for path in sorted(Path(directory).glob("*.json")):
        try:
            results.append(audit_one(path))
        except (ValueError, KeyError, OSError, subprocess.CalledProcessError) as exc:
            results.append({"file": path.name, "status": "error",
                            "reason": str(exc)[:160], "prospective_verified": False})
    from collections import Counter
    return {"files": len(results),
            "status_counts": dict(Counter(x["status"] for x in results)),
            "prospective_verified": 0,
            "warning": "Git timestamps are not trusted independent first-seen proof.",
            "details": results}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("directory")
    args = parser.parse_args()
    print(json.dumps(audit_all(args.directory), ensure_ascii=False, indent=2))

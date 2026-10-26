"""Offline check of initial Git additions against a caller-provided frozen blob digest.

Run only against an independently cloned repository, with locked outcome access.
Git commit timestamps are author-controlled; this check alone is NOT a trusted
server-side receipt proving the blob existed before the race deadline.
"""
import argparse
import hashlib
import json
import re
import subprocess
from datetime import datetime, timezone, timedelta
from pathlib import Path

SHA = re.compile(r"[0-9a-f]{40}\Z")
DIGEST = re.compile(r"[0-9a-f]{64}\Z")

def git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), *args], check=True,
                          capture_output=True, timeout=20).stdout

def audit(repo, commit, path, expected_sha256, deadline):
    if not SHA.fullmatch(commit) or not DIGEST.fullmatch(expected_sha256):
        raise ValueError("invalid digest or commit")
    if path.startswith("/") or ".." in Path(path).parts or not path or "\\x00" in path:
        raise ValueError("unsafe path")
    cutoff=datetime.fromisoformat(deadline.replace("Z","+00:00"))
    if cutoff.tzinfo is None or cutoff.utcoffset() is None:
        raise ValueError("timezone required")
    parents=git(repo,"rev-list","--parents","-n","1",commit).decode().strip().split()
    if len(parents)!=2:
        raise ValueError("first-addition audit requires a single-parent commit")
    change=git(repo,"diff-tree","--no-commit-id","--name-status","-r",commit,"--",path)
    if change.decode().strip()!=f"A\t{path}":
        raise ValueError("path was not newly added in asserted commit")
    prior_history=git(repo,"log","--format=%H",parents[1],"--",path)
    if prior_history.strip():
        raise ValueError("not the first historical addition of path")
    raw=git(repo,"show",f"{commit}:{path}")
    if hashlib.sha256(raw).hexdigest()!=expected_sha256:
        raise ValueError("frozen blob bytes differ")
    record=json.loads(raw)
    if not isinstance(record,dict):
        raise ValueError("expected JSON object")
    committer=git(repo,"show","-s","--format=%cI",commit).decode().strip()
    saved=datetime.fromisoformat(committer)
    if saved>=cutoff-timedelta(minutes=12):
        raise ValueError("Git committer timestamp not before 12-minute cutoff")
    return {"status":"LOCAL_GIT_FIRST_ADD_AND_BLOB_MATCH_ONLY",
            "commit":commit,"path":path,"blob_sha256":expected_sha256,
            "git_committer_time":committer,
            "limitations":"Git timestamps can be rewritten. Requires independent trusted server receipt and forecast content review; cannot alone authorize scoring."}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--repo",type=Path,required=True)
    p.add_argument("--commit",required=True)
    p.add_argument("--path",required=True)
    p.add_argument("--sha256",required=True)
    p.add_argument("--deadline",required=True)
    a=p.parse_args()
    print(json.dumps(audit(a.repo,a.commit,a.path,a.sha256,a.deadline),
                     ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()

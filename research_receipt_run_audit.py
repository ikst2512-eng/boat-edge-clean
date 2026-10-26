"""Audit committed pair bytes against the triggering GitHub Actions run.

Fetches the run via GitHub API; run.created_at is server-side evidence.
The runner's checked-out SHA must exactly equal the run head SHA. No claim of
external/source-data verification or model success is made.
"""
import argparse
import json
import os
from pathlib import Path
from urllib.request import Request, urlopen
from research_remote_pair_evidence import audit_pair_blob

REPO="ikst2512-eng/boat-edge-clean"

def run_audit(run_id, sha, folder="research_prospective_pairs"):
    if not str(run_id).isdigit() or len(sha)!=40 or any(c not in "0123456789abcdef" for c in sha):
        raise ValueError("invalid GitHub run identifier or SHA")
    url=f"https://api.github.com/repos/{REPO}/actions/runs/{run_id}"
    headers={"Accept":"application/vnd.github+json","User-Agent":"BOAT-EDGE-CLEAN-RESEARCH"}
    token=os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"]="Bearer "+token
    with urlopen(Request(url,headers=headers),timeout=12) as response:
        run=json.load(response)
    if run.get("id")!=int(run_id) or run.get("head_sha")!=sha:
        raise ValueError("run does not correspond to checked-out commit")
    import subprocess
    added = set(subprocess.check_output(
        ["git", "diff-tree", "--root", "--no-commit-id", "--name-only",
         "--diff-filter=A", "-r", sha], text=True).splitlines())
    reports=[]
    for path in sorted(Path(folder).glob("*.json")):
        if path.as_posix() not in added:
            continue
        if path.is_symlink():
            raise ValueError("symlink pair forbidden")
        raw=path.read_bytes()
        # This workflow checks out the triggering commit. HEAD contains the
        # committed blob; no local pair writes occur before this inspection.
        committed=subprocess.check_output(["git","show",f"{sha}:{path.as_posix()}"])
        reports.append(audit_pair_blob(raw,path.as_posix(),run,sha,committed))
    if not reports:
        raise ValueError("push did not introduce any new paired forecast files")
    if not all(item["remote_pair_evidence"] for item in reports):
        raise ValueError("one or more new research pairs lack pre-cutoff remote evidence")
    return {"run_id":int(run_id),"inspected":len(reports),
            "remote_pair_evidence_count":sum(x["remote_pair_evidence"] for x in reports),
            "reports":reports,
            "formal_validation":False}

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--run-id",required=True)
    p.add_argument("--sha",required=True)
    args=p.parse_args()
    print(json.dumps(run_audit(args.run_id,args.sha),ensure_ascii=False))

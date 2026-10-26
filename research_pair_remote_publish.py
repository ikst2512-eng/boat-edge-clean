"""Opt-in research branch push with remote SHA verification.

A matching remote commit SHA proves publication at query time, NOT an
independent pre-cutoff receipt timestamp. Never push main or formal Fresh.
"""
import argparse
import json
import subprocess
from datetime import datetime
from research_model import JST
from research_pair_publish_guard import eligible_paths
from research_pair_git_prepare import BRANCH, _git

def push(day, folder="research_prospective_pairs", dry_run=True):
    if _git("branch","--show-current") != BRANCH:
        raise ValueError("only research branch allowed")
    # Collection creates baseline snapshots that are intentionally not committed
    # by the isolated paired publisher. Allow only their untracked files.
    changes=_git("status","--porcelain","--untracked-files=all").splitlines()
    allowed_prefix=f"?? research_snapshots/{day}"
    if any(not (line.startswith(allowed_prefix) and line.endswith(".json"))
           for line in changes):
        raise ValueError("unrelated working-tree changes prevent research push")
    paths=eligible_paths(folder,day,datetime.now(JST))
    if not paths:
        raise ValueError("no eligible paired forecasts to publish")
    head=_git("rev-parse","HEAD")
    # Receipt auditor only certifies files added in this HEAD commit.
    added=set(_git("diff-tree","--root","--no-commit-id","--name-only",
                   "--diff-filter=A","-r",head).splitlines())
    if not set(paths).issubset(added):
        raise ValueError("eligible pair not newly added in HEAD")
    changes=set(_git("diff-tree","--root","--no-commit-id","--name-only",
                     "-r",head).splitlines())
    if changes != set(paths):
        raise ValueError("HEAD contains unrelated changes; refuse publication")
    for name in paths:
        committed=_git("rev-parse",f"HEAD:{name}")
        current=_git("hash-object",name)
        if committed != current:
            raise ValueError("eligible pair not committed at HEAD")
    if not dry_run:
        eligible_paths(folder,day,datetime.now(JST))
        subprocess.run(["git","push","origin",f"HEAD:refs/heads/{BRANCH}"],check=True)
        remote=_git("ls-remote","origin",f"refs/heads/{BRANCH}").split()
        if len(remote) != 2 or remote[0] != head:
            raise ValueError("remote head SHA mismatch after push")
    return {"branch":BRANCH,"head":head,"dry_run":dry_run,
            "remote_head_verified":not dry_run,
            "pre_cutoff_remote_receipt_verified":False}

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--day",required=True)
    p.add_argument("--folder",default="research_prospective_pairs")
    p.add_argument("--push",action="store_true")
    args=p.parse_args()
    print(json.dumps(push(args.day,args.folder,not args.push),ensure_ascii=False))

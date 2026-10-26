"""Opt-in, research-branch-only Git publisher; never touches formal Fresh.

Run AFTER collecting research pairs; only staged eligible pair JSONs are
committed. A local commit is not independent proof of pre-cutoff receipt.
This utility deliberately does not push automatically: a remote publication
must be independently authorized and verified against server-side timestamps.
"""
import argparse
import subprocess
from pathlib import Path
from research_pair_publish_guard import eligible_paths
from research_model import JST
from datetime import datetime

BRANCH="research/paired-hit-evaluation-20261027"

def _git(*args):
    return subprocess.check_output(["git",*args],text=True).strip()

def prepare(day, folder="research_prospective_pairs", now=None):
    if _git("branch","--show-current") != BRANCH:
        raise ValueError("refuse non-research branch")
    test_clock = now is not None
    now=now or datetime.now(JST)
    files=eligible_paths(folder,day,now)
    if not files:
        return {"ready":0,"commit_created":False}
    for path in files:
        resolved=Path(path).resolve()
        parent=Path(folder).resolve()
        if parent not in resolved.parents or resolved.is_symlink():
            raise ValueError("path outside paired forecast folder")
    # Stage only verified pair files; never stage production artifacts.
    subprocess.run(["git","add","--",*files],check=True)
    staged=_git("diff","--cached","--name-only").splitlines()
    expected=set(files)
    if set(staged)-expected:
        subprocess.run(["git","reset","--",*files],check=True)
        raise ValueError("unrelated staged changes: refuse commit")
    if not staged:
        return {"ready":len(files),"commit_created":False}
    added=set(_git("diff","--cached","--name-only","--diff-filter=A").splitlines())
    if set(staged) != added:
        subprocess.run(["git","reset","--",*files],check=True)
        raise ValueError("refuse to overwrite existing paired forecast")

    # Re-check immediately before committing; race cutoffs can pass mid-run.
    eligible_paths(folder,day,now if test_clock else datetime.now(JST))
    subprocess.run(["git","-c","user.name=research-pair-capture-bot",
                    "-c","user.email=research-pair-capture-bot@users.noreply.github.com",
                    "commit","-m",f"Freeze research paired forecasts {day}"],check=True)
    return {"ready":len(files),"commit_created":True,
            "commit":_git("rev-parse","HEAD"),"remote_receipt_verified":False}

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--day",required=True)
    p.add_argument("--folder",default="research_prospective_pairs")
    args=p.parse_args()
    print(prepare(args.day,args.folder))

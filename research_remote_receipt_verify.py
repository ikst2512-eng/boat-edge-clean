"""Independently verify publication using GitHub API server Date, not local clock.

A successful post-push GitHub ref GET after publication is conservative evidence:
the remote ref points to the exact commit at the server's Date time. If even
one added pair is past cutoff at that time, refuse to certify the batch.
"""
import argparse
import json
import os
import subprocess
from datetime import datetime
from email.utils import parsedate_to_datetime
from urllib.request import Request,urlopen
from research_pair_publish_guard import eligible_paths
from research_pair_git_prepare import BRANCH

REPO="ikst2512-eng/boat-edge-clean"

def verify(day, fetch=None):
    head=subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip()
    added=set(subprocess.check_output(
        ["git","diff-tree","--root","--no-commit-id","--name-only",
         "--diff-filter=A","-r",head],text=True).splitlines())
    if not added or any(not x.startswith("research_prospective_pairs/") for x in added):
        raise ValueError("commit has no exclusively research paired forecast additions")
    token=os.environ.get("GITHUB_TOKEN")
    if fetch is None:
        def fetch():
            headers={"Accept":"application/vnd.github+json","User-Agent":"boat-edge-clean-receipt"}
            if token: headers["Authorization"]="Bearer "+token
            url=f"https://api.github.com/repos/{REPO}/git/ref/heads/{BRANCH}"
            with urlopen(Request(url,headers=headers),timeout=15) as response:
                return json.load(response),response.headers["Date"]
    body,server_date=fetch()
    remote_sha=body.get("object",{}).get("sha")
    if remote_sha!=head or len(head)!=40:
        raise ValueError("GitHub remote ref does not point to candidate commit")
    observed=parsedate_to_datetime(server_date)
    if observed.tzinfo is None:
        raise ValueError("GitHub Date header must be timezone-aware")
    verified=set(eligible_paths("research_prospective_pairs",day,now=observed,
                               only_paths=added))
    if verified!=added:
        raise ValueError("pair batch mismatch")
    return {"commit":head,"server_observed_at":observed.isoformat(),
            "eligible_pairs":len(verified),"remote_observed_pre_cutoff":True,
            "independent_source_verified":False,"forecast_accuracy_verified":False}

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--day",required=True)
    a=p.parse_args()
    print(json.dumps(verify(a.day),ensure_ascii=False))

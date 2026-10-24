"""Promote a staged Fresh feed through GitHub Contents API with optimistic concurrency.

Requires a token with Contents write permission. This command is never invoked
by CI and never assumes that Git commit timestamps certify Fresh status.
"""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.error import HTTPError

REPO="ikst2512-eng/boat-edge-clean"
PATH="predictions.json"

def request_json(method,url,token,payload=None):
    headers={"Authorization":"Bearer "+token,"Accept":"application/vnd.github+json",
             "User-Agent":"BOAT-EDGE-FRESH-PROMOTER/1","X-GitHub-Api-Version":"2022-11-28"}
    raw=None if payload is None else json.dumps(payload).encode("utf-8")
    if raw is not None:headers["Content-Type"]="application/json"
    with urlopen(Request(url,data=raw,headers=headers,method=method),timeout=15) as resp:
        return json.load(resp)

def promote(staged_path,audit_path,branch,token,api=request_json):
    if not token or not isinstance(branch,str) or not branch or branch=="main":
        raise ValueError("explicit non-main branch and GitHub token required")
    staged=Path(staged_path).read_bytes()
    audit=json.loads(Path(audit_path).read_text(encoding="utf-8"))
    if audit.get("deployment_status")!="staged_not_published":
        raise ValueError("not a staging audit")
    if hashlib.sha256(staged).hexdigest()!=audit.get("new_sha256"):
        raise ValueError("staged feed hash mismatch")
    candidate=json.loads(staged)
    if not isinstance(candidate,dict) or not candidate:
        raise ValueError("empty candidate feed")
    url=f"https://api.github.com/repos/{REPO}/contents/{PATH}"
    current=api("GET",url+"?ref="+branch,token)
    if current.get("type")!="file" or not isinstance(current.get("sha"),str):
        raise ValueError("existing GitHub feed unavailable")
    decoded=base64.b64decode(current["content"])
    if hashlib.sha256(decoded).hexdigest()!=audit.get("previous_sha256"):
        raise ValueError("published feed changed since staging")
    original=json.loads(decoded)
    from fresh_feed_incremental import merge
    merged,added,unchanged=merge(original,candidate)
    if merged!=candidate or not added:
        raise ValueError("candidate is not a strict immutable extension")
    body={"message":"Append verified candidate predictions (no existing changes)",
          "content":base64.b64encode(staged).decode("ascii"),
          "sha":current["sha"],"branch":branch}
    result=api("PUT",url,token,body)
    if not isinstance(result.get("commit",{}).get("sha"),str):
        raise ValueError("GitHub did not return a commit")
    return {"commit_sha":result["commit"]["sha"],"new_races":added,
            "feed_sha256":audit["new_sha256"],"branch":branch}

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--staged",required=True)
    p.add_argument("--audit",required=True)
    p.add_argument("--branch",required=True)
    a=p.parse_args()
    print(json.dumps(promote(a.staged,a.audit,a.branch,os.environ.get("GITHUB_TOKEN",""))))

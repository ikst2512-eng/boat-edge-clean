"""Check whether manual paired capture is actually registered on default branch.

This preflight intentionally does not dispatch or modify workflows. A workflow
existing only in a PR branch is NOT evidence that workflow_dispatch is usable.
"""
import argparse
import json
import os
from urllib.request import Request, urlopen
from urllib.error import HTTPError

REPO = "ikst2512-eng/boat-edge-clean"
WORKFLOW = "research-pair-capture-manual.yml"

def preflight(fetch=None):
    def get(url):
        headers={"Accept":"application/vnd.github+json","User-Agent":"boat-edge-clean-research"}
        token=os.environ.get("GITHUB_TOKEN")
        if token: headers["Authorization"]="Bearer "+token
        with urlopen(Request(url,headers=headers),timeout=15) as response:
            return json.load(response)
    get=fetch or get
    repo=get(f"https://api.github.com/repos/{REPO}")
    default=repo["default_branch"]
    try:
        workflow=get(f"https://api.github.com/repos/{REPO}/contents/.github/workflows/{WORKFLOW}?ref={default}")
    except HTTPError as e:
        if e.code == 404:
            return {"default_branch":default,"registered_on_default":False,
                    "dispatch_ready":False,"reason":"workflow file absent from default branch",
                    "formal_fresh_unchanged":True}
        raise
    if workflow.get("type")!="file":
        raise ValueError("manual workflow path is not a file")
    return {"default_branch":default,"registered_on_default":True,
            "dispatch_ready":True,"reason":"default-branch workflow file exists; verify enabled state and permissions before dispatch",
            "formal_fresh_unchanged":True}

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--strict",action="store_true")
    args=p.parse_args()
    state=preflight()
    print(json.dumps(state,ensure_ascii=False))
    if args.strict and not state["dispatch_ready"]:
        raise SystemExit(2)

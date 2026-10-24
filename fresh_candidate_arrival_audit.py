"""Check GitHub-issued arrival evidence for a nonpublic candidate workflow run.

Run metadata comes from GitHub's API, not from the candidate's runner clock.
A passing check proves a workflow run existed before cutoff; it does NOT prove
official deadline validity, upstream model identity, or formal Fresh approval.
"""
import argparse,json
from datetime import datetime,timedelta
from pathlib import Path
from urllib.request import Request,urlopen

REPO="ikst2512-eng/boat-edge-clean"
WORKFLOW=".github/workflows/fresh-prospective-capture.yml"

def check(receipt,run):
    if not isinstance(receipt,dict) or not isinstance(run,dict):
        raise ValueError("audit metadata required")
    if (receipt.get("schema")!="fresh-prospective-receipt-v1"
        or receipt.get("independent_github_arrival_verified") is not False
        or type(receipt.get("workflow_run_id")) is not int
        or receipt["workflow_run_id"]!=run.get("id")
        or type(receipt.get("workflow_attempt")) is not int
        or receipt["workflow_attempt"]!=run.get("run_attempt")
        or run.get("event")!="repository_dispatch"
        or run.get("conclusion")!="success"
        or run.get("head_branch")!="main"):
        raise ValueError("incorrect candidate witness")
    path=run.get("path")
    if not isinstance(path,str) or path.split("@",1)[0]!=WORKFLOW:
        raise ValueError("wrong workflow")
    cutoff=datetime.fromisoformat(receipt["deadline_at"])-timedelta(minutes=12)
    arrival=datetime.fromisoformat(run["created_at"].replace("Z","+00:00"))
    if any(x.tzinfo is None or x.utcoffset() is None for x in (cutoff,arrival)):
        raise ValueError("timezone missing")
    if arrival>=cutoff:
        raise ValueError("GitHub run started after safety cutoff")
    return {"github_run_arrived_before_cutoff":True,
            "formal_approved":False,"race_code":receipt["race_code"],
            "workflow_run_id":run["id"]}

def fetch(run_id):
    if type(run_id) is not int or run_id<=0:
        raise ValueError("run id invalid")
    url=f"https://api.github.com/repos/{REPO}/actions/runs/{run_id}"
    with urlopen(Request(url,headers={"Accept":"application/vnd.github+json",
                                       "User-Agent":"boat-edge-candidate-audit"}),timeout=10) as response:
        return json.load(response)

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("receipt")
    a=p.parse_args()
    r=json.loads(Path(a.receipt).read_bytes())
    print(json.dumps(check(r,fetch(r["workflow_run_id"])),sort_keys=True))

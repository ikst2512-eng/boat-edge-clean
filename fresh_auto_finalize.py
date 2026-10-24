"""Finalize a witnessed snapshot push into a new local predictions.json.

Designed for GitHub workflow_run *after* the dedicated witness succeeded.
Never invents a forecast, never changes previously published race records.
"""
import argparse
import json
import re
from pathlib import Path
from fresh_feed_builder import canonical
from fresh_feed_incremental import merge
from fresh_feed_publisher import assemble,fetch_json

REPO="ikst2512-eng/boat-edge-clean"
WITNESS=".github/workflows/fresh-snapshot-witness.yml"
def witness_valid(run,sha):
    return (isinstance(run,dict) and run.get("head_sha")==sha and
            run.get("event")=="push" and run.get("conclusion")=="success" and
            run.get("head_branch")=="main" and
            run.get("path") in (WITNESS,WITNESS+"@refs/heads/main"))

def collect_from_witness(run_id,lookup=fetch_json,resolve=assemble):
    if type(run_id) is not int or run_id<=0:
        raise ValueError("invalid witness run")
    run=lookup(f"https://api.github.com/repos/{REPO}/actions/runs/{run_id}")
    sha=run.get("head_sha","")
    if not isinstance(sha,str) or not re.fullmatch("[0-9a-f]{40}",sha) or not witness_valid(run,sha):
        raise ValueError("untrusted witness")
    commit=lookup(f"https://api.github.com/repos/{REPO}/commits/{sha}")
    paths=commit.get("files")
    if not isinstance(paths,list) or not paths:
        raise ValueError("commit file list unavailable")
    accepted={}
    for item in paths:
        if not isinstance(item,dict):
            raise ValueError("invalid commit file metadata")
        name=item.get("filename","")
        if not name.startswith("fresh_snapshots/"):
            continue
        if item.get("status")!="added" or not re.fullmatch(r"fresh_snapshots/[0-9]{12}\.json",name):
            raise ValueError("snapshot modified or deleted")
        code=name[len("fresh_snapshots/"):-5]
        # The publisher loads the *immutable source* from this exact commit.
        # Its deadline is taken from the original file, not an adjustable
        # post-hoc manifest. Resolve once without trusting the push payload.
        from urllib.request import Request,urlopen
        from datetime import datetime,timezone
        url=f"https://raw.githubusercontent.com/{REPO}/{sha}/{name}"
        with urlopen(Request(url,headers={"User-Agent":"BOAT-EDGE-FRESH-FINALIZE/1"}),timeout=8) as response:
            blob=response.read(100001)
        if len(blob)>100000:
            raise ValueError("snapshot too large")
        frozen=json.loads(blob)
        if frozen.get("race_code")!=code or not isinstance(frozen.get("deadline_at"),str):
            raise ValueError("invalid original race/deadline")
        record=resolve(sha,code,frozen["deadline_at"],run_id)
        if record.get("race_code")!=code or not isinstance(record.get("freeze_proof"),dict):
            raise ValueError("publisher yielded unverified record")
        key=f"{code[:8]}-{code[8:10]}-{int(code[10:])}"
        if key in accepted:
            raise ValueError("duplicate race")
        accepted[key]=record
    if not accepted:
        raise ValueError("witnessed commit contains no new snapshots")
    return accepted

def finalize(run_id,existing,out,lookup=fetch_json,resolve=assemble):
    source=Path(existing)
    old=json.loads(source.read_text(encoding="utf-8")) if source.exists() else {}
    records=collect_from_witness(run_id,lookup,resolve)
    updated,added,unchanged=merge(old,records)
    if not added:
        raise ValueError("no new race to publish")
    dest=Path(out)
    if dest.resolve()==source.resolve():
        raise ValueError("must stage into a separate path")
    dest.parent.mkdir(parents=True,exist_ok=True)
    with dest.open("xb") as f:
        f.write(canonical(updated))
    return {"added":added,"unchanged":unchanged,"total":len(updated)}

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--run-id",required=True,type=int)
    p.add_argument("--existing",default="predictions.json")
    p.add_argument("--out",required=True)
    a=p.parse_args()
    print(json.dumps(finalize(a.run_id,a.existing,a.out)))

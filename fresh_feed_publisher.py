"""Build a *candidate* public prediction feed from an actual GitHub commit.

This uses GitHub's commit API and raw immutable object. The Git committer
timestamp is NOT independent proof that GitHub received it before deadline.
Do not count this as audited Fresh without server-side publication evidence.
"""
import argparse
import hashlib
import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from urllib.request import Request, urlopen
from fresh_feed_builder import canonical

REPO="ikst2512-eng/boat-edge-clean"

def fetch_json(url):
    with urlopen(Request(url,headers={"Accept":"application/vnd.github+json",
                                     "User-Agent":"BOAT-EDGE-FRESH-PUBLISHER/1"}),timeout=8) as r:
        return json.load(r)

def assemble(commit_sha,race_code,deadline_at,run_id=None):
    if not isinstance(commit_sha,str) or not re.fullmatch("[0-9a-f]{40}",commit_sha):
        raise ValueError("invalid commit SHA")
    if not isinstance(race_code,str) or not re.fullmatch("[0-9]{12}",race_code):
        raise ValueError("invalid race code")
    deadline=datetime.fromisoformat(deadline_at)
    if deadline.tzinfo is None or deadline.utcoffset() is None:
        raise ValueError("deadline timezone required")
    metadata=fetch_json(f"https://api.github.com/repos/{REPO}/commits/{commit_sha}")
    committed_at=datetime.fromisoformat(metadata["commit"]["committer"]["date"].replace("Z","+00:00"))
    if committed_at.tzinfo is None or committed_at>=deadline:
        raise ValueError("Git committer date is after deadline")
    if type(run_id) is not int or run_id<=0:
        raise ValueError("GitHub server timestamp witness required")
    run=fetch_json(f"https://api.github.com/repos/{REPO}/actions/runs/{run_id}")
    if (run.get("head_sha")!=commit_sha or run.get("event")!="push" or
        run.get("conclusion")!="success" or run.get("head_branch")!="main" or
        (not isinstance(run.get("path"), str) or run["path"].split("@", 1)[0] != ".github/workflows/fresh-snapshot-witness.yml")):
        raise ValueError("GitHub run did not witness commit")
    run_created=datetime.fromisoformat(run["created_at"].replace("Z","+00:00"))
    if run_created.tzinfo is None or run_created>=deadline-timedelta(minutes=12):
        raise ValueError("GitHub server run started too late")
    path=f"fresh_snapshots/{race_code}.json"
    with urlopen(Request(f"https://raw.githubusercontent.com/{REPO}/{commit_sha}/{path}",
                         headers={"User-Agent":"BOAT-EDGE-FRESH-PUBLISHER/1"}),timeout=8) as r:
        raw=r.read(100001)
    if len(raw)>100000: raise ValueError("snapshot too large")
    record=json.loads(raw)
    if not isinstance(record,dict) or record.get("race_code")!=race_code or record.get("validated") is not True:
        raise ValueError("invalid committed record")
    if "freeze_proof" in record: raise ValueError("nested proof in immutable source")
    source_deadline=datetime.fromisoformat(record["deadline_at"])
    if source_deadline.tzinfo is None or source_deadline.utcoffset() is None or source_deadline!=deadline:
        raise ValueError("manifest deadline differs from frozen source deadline")
    gen=datetime.fromisoformat(record["generated_at"])
    if gen.tzinfo is None or gen.utcoffset() is None or gen>committed_at or gen>run_created:
        raise ValueError("forecast created after commit")
    probs=record.get("probabilities")
    from fresh_feed_builder import VALID
    import math
    if not isinstance(probs,dict) or set(probs)!=VALID or any(type(v) not in (int,float) or not math.isfinite(v) or v<0 or v>1 for v in probs.values()):
        raise ValueError("invalid 120 probabilities")
    if abs(sum(probs.values())-1)>1e-8: raise ValueError("probability sum invalid")
    expected=sorted(VALID,key=lambda t:(-probs[t],tuple(map(int,t.split("-")))))
    picks=record.get("predictions")
    if not isinstance(picks,list) or len(picks)!=10 or any(not isinstance(p,dict) or p.get("ticket")!=t or p.get("probability")!=probs[t] for p,t in zip(picks,expected[:10])):
        raise ValueError("top10 differs from distribution")
    proof={"commit_sha":commit_sha,"committed_at":committed_at.isoformat(),
           "deadline_at":deadline.isoformat(),"path":path,
           "sha256":hashlib.sha256(raw).hexdigest(),"run_id":run_id}
    return {**record,"freeze_proof":proof}

def write_new_feed(record,out):
    code=record["race_code"]
    key=f"{code[:8]}-{code[8:10]}-{int(code[10:])}"
    dest=Path(out)
    dest.parent.mkdir(parents=True,exist_ok=True)
    # Never replace an existing feed. Merging requires a separate audited writer.
    with dest.open("xb") as f:
        f.write(canonical({key:record}))
    return dest

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--commit",required=True)
    p.add_argument("--race-code",required=True)
    p.add_argument("--deadline",required=True)
    p.add_argument("--run-id",type=int,required=True)
    p.add_argument("--out",default="predictions.json")
    a=p.parse_args()
    record=assemble(a.commit,a.race_code,a.deadline,a.run_id)
    print(write_new_feed(record,a.out))

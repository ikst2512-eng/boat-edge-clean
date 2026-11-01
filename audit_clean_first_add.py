"""Read-only audit of the first Git addition of CLEAN prospective predictions.

A Git committer timestamp is evidence, not proof of remote server receipt.
This module NEVER promotes a candidate to a formal forecast or scoring.
"""
import json
import re
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parent
PATTERN=re.compile(r"^prospective_predictions/(20[0-9]{10})\.json$")

def first_add(path, root=ROOT):
    rel=str(path).replace("\\","/")
    if not PATTERN.fullmatch(rel):
        raise ValueError("invalid record path")
    history=subprocess.check_output(["git","log","--format=%H","--diff-filter=A","--",rel],cwd=root,text=True).splitlines()
    if len(history)!=1:
        raise ValueError("unambiguous first addition not found")
    sha=history[0]
    original=subprocess.check_output(["git","show",sha+":"+rel],cwd=root)
    current=(root/rel).read_bytes()
    if current!=original:
        raise ValueError("candidate changed since first add")
    stamp=subprocess.check_output(["git","show","-s","--format=%cI",sha],cwd=root,text=True).strip()
    return current,sha,datetime.fromisoformat(stamp)

def inspect(path, root=ROOT):
    original,sha,first_committer_at=first_add(path,root)
    obj=json.loads(original)
    code=PATTERN.fullmatch(path).group(1)
    if obj.get("race_code")!=code or obj.get("status")!="prospective_candidate" or obj.get("formal") is not False or obj.get("scoring") is not False:
        raise ValueError("wrong archive type")
    deadline=datetime.fromisoformat(obj["source_deadline_jst"])
    cutoff=datetime.fromisoformat(obj["cutoff_jst"])
    generated=datetime.fromisoformat(obj["generated_at"])
    times=[datetime.fromisoformat(obj[k]) for k in ("source_title_received_jst","source_cards_received_jst")]
    if any(v.utcoffset()!=timedelta(hours=9) for v in [deadline,cutoff,generated,*times]):
        raise ValueError("non-JST timestamp")
    if (deadline-cutoff!=timedelta(minutes=12)
            or deadline.strftime("%Y%m%d")!=code[:8]
            or max(times)>generated
            or max([generated,*times])>=cutoff
            or first_committer_at.utcoffset() is None
            or first_committer_at<generated
            or first_committer_at>=cutoff):
        raise ValueError("invalid source chronology or first Git commit after cutoff")
    return {"race_code":code,"first_add_sha":sha,
            "first_committer_at":first_committer_at.isoformat(),
            "candidate_unchanged":True,"git_commit_before_cutoff":True,
            "remote_first_seen_verified":False,"formal":False,"scoring":False}

if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument("paths",nargs="+")
    args=p.parse_args()
    print(json.dumps([inspect(f) for f in args.paths],ensure_ascii=False))

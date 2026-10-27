"""Freeze V236 coverage15 ONLY from precommitted CLEAN-owned V232 candidates.

Does not read old boat-edge at runtime, outcomes, odds updates, or next-day data.
The first Git-add of the input cohort is required before deadline.
"""
import datetime as dt
import hashlib
import json
import re
import subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parent
JST=dt.timezone(dt.timedelta(hours=9))
KEY=re.compile(r"^20\d{6}-\d{2}-\d{2}$")
TICKET=re.compile(r"^[1-6]-[1-6]-[1-6]$")
SCHEMA="BOAT_EDGE_V232_SITE_PROSPECTIVE_ACCURACY_COHORT_V1"


def parse_time(s):
    try:
        v=dt.datetime.fromisoformat(s.replace("Z","+00:00"))
        return v if v.tzinfo is not None else None
    except (ValueError,TypeError,AttributeError):
        return None


def first_commit(root,rel):
    def git(*args):
        return subprocess.check_output(["git","-C",str(root),*args],stderr=subprocess.DEVNULL,timeout=10)
    commits=git("log","--reverse","--diff-filter=A","--format=%H","--",str(rel)).decode().splitlines()
    if len(commits)!=1:raise ValueError("first_add_missing")
    sha=commits[0]
    content=git("show",sha+":"+str(rel))
    created=parse_time(git("show","-s","--format=%cI",sha).decode().strip())
    if created is None:raise ValueError("first_commit_time_invalid")
    return sha,created,hashlib.sha256(content).digest()


def combo_ok(v):
    return isinstance(v,str) and TICKET.fullmatch(v) is not None and len(set(v.split("-")))==3


def prepare(root,path,now):
    key=path.stem
    if not KEY.fullmatch(key):raise ValueError("race_key")
    if path.is_symlink() or path.stat().st_size>30000:raise ValueError("cohort_file")
    content=path.read_bytes()
    data=json.loads(content)
    if data.get("schema")!=SCHEMA or data.get("race_key")!=key or data.get("model_id")!="SITE_REFERENCE_V122":
        raise ValueError("cohort_identity")
    if data.get("scope")!="SITE_REFERENCE_UNSEEN_PRE_RESULT_ONLY_NOT_FORMAL_FRESH":
        raise ValueError("cohort_scope")
    if data.get("formal_results_seen") is not False or data.get("formal_gate_unlocked") is not False:
        raise ValueError("result_leakage_guard")
    if data.get("paper_purchases_authorized") is not False or data.get("real_purchases_authorized") is not False:
        raise ValueError("purchase_guard")
    deadline=parse_time(data.get("deadline_jst"))
    saved=parse_time(data.get("snapshot_saved_at"))
    evidence=parse_time(data.get("evidence_committed_at"))
    if not deadline or not saved or not evidence or deadline.astimezone(JST).strftime("%Y%m%d")!=key[:8]:
        raise ValueError("deadline_or_source_time")
    if not 90<=(deadline-now).total_seconds()<=900:
        raise ValueError("outside_predeadline_window")
    sha,first_at,orig_digest=first_commit(root,path.relative_to(root))
    if not(saved<=evidence<=first_at<=now<deadline) or orig_digest!=hashlib.sha256(content).digest():
        raise ValueError("not_proven_predeadline")
    frozen=data.get("frozen_mode_tickets")
    if not isinstance(frozen,dict):raise ValueError("missing_candidates")
    def values(mode):
        rows=frozen.get(mode)
        return [r.get("combo") for r in rows] if isinstance(rows,list) and all(isinstance(r,dict) for r in rows) else []
    hit=values("hit")
    hole=values("hole")
    if len(hit)!=10 or len(set(hit))!=10 or len(hole)<10 or len(set(hole))!=len(hole) or not all(combo_ok(t) for t in hit+hole) or data.get("top10")!=hit:
        raise ValueError("candidate_invalid")
    tickets=list(dict.fromkeys(hit+hole))[:15]
    if len(tickets)!=15:raise ValueError("insufficient_unique_tickets")
    race=key[:8]+key[9:11]+key[12:14]
    return {"race_code":race,"model":"V236_coverage15","tickets":tickets,
            "saved_at_jst":now.astimezone(JST).isoformat(),
            "deadline_jst":deadline.astimezone(JST).isoformat(),
            "candidate_cohort_sha256":hashlib.sha256(content).hexdigest(),
            "candidate_first_git_sha":sha,"selection":"V236_PREDECLARED_HEAD_TAIL_COVERAGE15"}


def run(root=ROOT,now=None):
    now=now or dt.datetime.now(dt.timezone.utc)
    base=root/"data/site_autopilot/v232_cohort"
    dest=root/"v236_forecasts"
    completed,errors=[],{}
    for path in sorted(base.glob("*.json")):
        code=path.stem.replace("-","")
        if (dest/(code+".json")).exists():continue
        try:
            record=prepare(root,path,now)
            dest.mkdir(parents=True,exist_ok=True)
            with (dest/(code+".json")).open("x",encoding="utf-8") as fp:
                json.dump(record,fp,ensure_ascii=False,sort_keys=True,indent=2)
                fp.write("\n")
            completed.append(code)
        except (OSError,ValueError,TypeError,KeyError,subprocess.SubprocessError,TimeoutError) as exc:
            errors[type(exc).__name__+":"+str(exc)]=errors.get(type(exc).__name__+":"+str(exc),0)+1
    return {"new_forecasts":completed,"excluded":errors}


if __name__=="__main__":
    print(json.dumps(run(),ensure_ascii=False))

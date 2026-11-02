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

# Bulk audit is opt-in and isolated to the worker thread; all individual
# records still require original-blob byte equality and cutoff validation.
from contextlib import contextmanager
from threading import local
_BULK = local()

@contextmanager
def bulk_first_add(root=ROOT):
    root = Path(root).resolve()
    raw = subprocess.check_output(
        ["git", "log", "--format=COMMIT %H %cI", "--name-only",
         "--diff-filter=A", "--", "prospective_predictions"],
        cwd=root, text=True)
    additions = {}
    sha = stamp = None
    for line in raw.splitlines():
        if line.startswith("COMMIT "):
            sha, stamp = line[7:].split(" ", 1)
            if len(sha) != 40 or any(c not in "0123456789abcdef" for c in sha):
                raise ValueError("invalid bulk commit SHA")
        elif PATTERN.fullmatch(line):
            additions.setdefault(line, []).append((sha, stamp))
    previous = getattr(_BULK, "state", None)
    _BULK.state = (root, additions)
    try:
        yield
    finally:
        _BULK.state = previous

def first_add(path, root=ROOT):
    rel=str(path).replace("\\","/")
    if not PATTERN.fullmatch(rel):
        raise ValueError("invalid record path")
    # Read commit SHA and timestamp in one Git traversal; retain the
    # unique-first-add requirement and verify the original blob below.
    # Two matching additions are enough to reject ambiguous evidence.
    bulk = getattr(_BULK, "state", None)
    if bulk is not None and Path(root).resolve() == bulk[0]:
        history = bulk[1].get(rel, [])
        if len(history) != 1:
            raise ValueError("unambiguous first addition not found")
        sha, stamp = history[0]
    else:
        history=subprocess.check_output(
            ["git","log","--max-count=2","--format=%H %cI","--diff-filter=A","--",rel],
            cwd=root,text=True).splitlines()
        if len(history)!=1:
            raise ValueError("unambiguous first addition not found")
        sha, stamp = history[0].split(" ",1)
    if len(sha)!=40 or any(c not in "0123456789abcdef" for c in sha):
        raise ValueError("invalid first addition SHA")
    original=subprocess.check_output(["git","show",sha+":"+rel],cwd=root)
    current=(root/rel).read_bytes()
    if current!=original:
        raise ValueError("candidate changed since first add")

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
    if deadline-cutoff!=timedelta(minutes=12):
        raise ValueError("cutoff interval invalid")
    if generated>=cutoff:
        raise ValueError("generated after cutoff")
    if any(t>=cutoff for t in times):
        raise ValueError("source received after cutoff")
    if first_committer_at>=cutoff:
        raise ValueError("first Git commit not before prospective cutoff")
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

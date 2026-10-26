"""Fail closed before publishing research pairs to a Git remote.

Returns eligible filenames only when every file's frozen timestamp, source
timestamps and *current* wall clock are strictly before the cutoff. This gate
cannot prove remote receipt time; verify GitHub remote receipt separately.
"""
import argparse
import json
from datetime import datetime
from pathlib import Path
from research_model import JST

def eligible_paths(folder, day, now=None):
    now = now or datetime.now(JST)
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("aware current time required")
    if len(day) != 8 or not day.isascii() or not day.isdigit():
        raise ValueError("invalid day")
    paths = sorted(Path(folder).glob(day + "*.json"))
    accepted = []
    for path in paths:
        row = json.loads(path.read_text(encoding="utf-8"))
        if path.stem != row.get("race_code"):
            raise ValueError("race code mismatch")
        cutoff = datetime.fromisoformat(row["cutoff_jst"])
        frozen = datetime.fromisoformat(row["frozen_at_jst"])
        source = datetime.fromisoformat(row["source_snapshot_generated_at"])
        if any(x.tzinfo is None or x.utcoffset() is None for x in (cutoff,frozen,source)):
            raise ValueError("naive timestamp")
        if max(now,frozen,source) >= cutoff:
            raise ValueError("pair already at/past cutoff")
        if row.get("status") != "research_unvalidated" or row.get("prospective_verified") is not False:
            raise ValueError("not unvalidated research")
        if len(row.get("baseline",{})) != 120 or len(row.get("candidate",{})) != 120:
            raise ValueError("incomplete distribution")
        accepted.append(path.as_posix())
    return accepted

if __name__ == "__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--folder",default="research_prospective_pairs")
    p.add_argument("--day",default=datetime.now(JST).strftime("%Y%m%d"))
    args=p.parse_args()
    for path in eligible_paths(args.folder,args.day):
        print(path)

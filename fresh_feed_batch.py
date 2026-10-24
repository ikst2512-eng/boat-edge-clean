"""Produce a multi-race candidate feed from independently checked GitHub snapshots.

This command never overwrites existing files and never labels Git metadata
as independently verified Fresh publication evidence.
"""
import argparse
import json
from pathlib import Path
from fresh_feed_builder import canonical
from fresh_feed_publisher import assemble

def race_key(code):
    if not isinstance(code,str) or len(code)!=12 or not code.isascii() or not code.isdigit():
        raise ValueError("invalid race code")
    venue=int(code[8:10]); race=int(code[10:12])
    if not 1<=venue<=24 or not 1<=race<=12:
        raise ValueError("invalid venue or race")
    return f"{code[:8]}-{code[8:10]}-{race}"

def prepare(entries, resolve=assemble):
    if not isinstance(entries,list) or not entries:
        raise ValueError("nonempty manifest list required")
    feed={}
    for entry in entries:
        if not isinstance(entry,dict) or set(entry)!={"commit_sha","race_code","deadline_at"}:
            raise ValueError("invalid manifest entry")
        key=race_key(entry["race_code"])
        if key in feed:
            raise ValueError("duplicate race in manifest")
        record=resolve(entry["commit_sha"],entry["race_code"],entry["deadline_at"])
        if record.get("race_code")!=entry["race_code"] or "freeze_proof" not in record:
            raise ValueError("unverified race record")
        feed[key]=record
    return {key:feed[key] for key in sorted(feed)}

def write_new_batch(manifest_path, out, resolve=assemble):
    entries=json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    feed=prepare(entries,resolve)
    destination=Path(out)
    destination.parent.mkdir(parents=True,exist_ok=True)
    # Exclusive file creation: no loss or mutation of any already-published races.
    with destination.open("xb") as stream:
        stream.write(canonical(feed))
    return len(feed)

if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--manifest",required=True,help="JSON list: commit_sha, race_code, deadline_at")
    p.add_argument("--out",required=True,help="NEW candidate feed path, must not exist")
    args=p.parse_args()
    print(write_new_batch(args.manifest,args.out))

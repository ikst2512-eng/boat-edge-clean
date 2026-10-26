"""Research-only pre-push integrity gate for newly added forecast JSONs.

Checks internal consistency only. Does not attest a remote first-seen time.
"""
import argparse
import hashlib
import json
import re
from datetime import datetime, timedelta
from pathlib import Path

HEX40=re.compile(r"[0-9a-f]{40}\Z")
HEX64=re.compile(r"[0-9a-f]{64}\Z")
NAME=re.compile(r"20[0-9]{10}\.json\Z")

def check_file(path):
    path=Path(path)
    if path.is_symlink() or not NAME.fullmatch(path.name) or path.stat().st_size>20000:
        raise ValueError("invalid research snapshot path or size")
    obj=json.loads(path.read_bytes())
    if not isinstance(obj,dict) or obj.get("race_code")!=path.stem or obj.get("status")!="research" or obj.get("validated") is not False:
        raise ValueError("invalid research snapshot envelope")
    for key in ("source_title_sha256","source_cards_sha256","input_sha256","model_source_sha256"):
        if not isinstance(obj.get(key),str) or not HEX64.fullmatch(obj[key]):
            raise ValueError("missing or malformed "+key)
    if not isinstance(obj.get("model_git_sha"),str) or not HEX40.fullmatch(obj["model_git_sha"]):
        raise ValueError("missing model git SHA")
    expected=hashlib.sha256((obj["source_title_sha256"]+":"+obj["source_cards_sha256"]).encode("ascii")).hexdigest()
    if obj["input_sha256"]!=expected or obj.get("input_hash_scope")!="source_csv_byte_hashes_ordered_title_cards":
        raise ValueError("input composite hash mismatch")
    times=[datetime.fromisoformat(obj[k]) for k in ("source_title_received_jst","source_cards_received_jst","generated_at","cutoff_jst","source_deadline_jst")]
    if any(x.utcoffset()!=timedelta(hours=9) for x in times):
        raise ValueError("timestamps must be JST")
    title,cards,generated,cutoff,deadline=times
    if max(title,cards)>generated or generated>cutoff or deadline-cutoff!=timedelta(minutes=12) or cutoff.strftime("%Y%m%d")!=path.stem[:8]:
        raise ValueError("invalid research snapshot timing")
    return path

def main():
    p=argparse.ArgumentParser()
    p.add_argument("paths",nargs="+")
    args=p.parse_args()
    for path in args.paths:
        check_file(path)
    print(json.dumps({"checked":len(args.paths),"ready_for_scoring":False,"remote_receipt_verified":False}))

if __name__=="__main__":
    main()

"""Import trusted v5 snapshot inputs into immutable Fresh candidates.

Separate from research-only collection. Never manufacture prediction probabilities.
The inbox must already contain actual v5 forecast files from a trusted producer.
"""
import argparse
import json
import os
from datetime import datetime,timezone,timedelta
from pathlib import Path
from fresh_feed_builder import canonical,convert

def capture(inbox,out,model_version,now=None):
    now=now or datetime.now(timezone.utc)
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("timezone-aware current time required")
    source=Path(inbox); target=Path(out)
    if not source.is_dir() or source.resolve()==target.resolve():
        raise ValueError("input inbox missing or aliases output")
    counts={"saved":0,"already_saved":0,"rejected":0}
    for path in sorted(source.glob("*.json")):
        try:
            if path.is_symlink() or path.stat().st_size>100000:
                raise ValueError("invalid source file")
            record=convert(path.read_bytes(),model_version)
            if path.stem!=record["race_code"]:
                raise ValueError("filename does not match race code")
            generated=datetime.fromisoformat(record["generated_at"])
            deadline=datetime.fromisoformat(record["deadline_at"])
            # Never backfill a 'Fresh' record after deadline, even if source
            # timestamps claim it was generated earlier.
            if generated>now or now>=deadline-timedelta(minutes=12):
                raise ValueError("late/untrusted collection timestamp")
            dest=target/(path.stem+".json")
            target.mkdir(parents=True,exist_ok=True)
            if dest.exists():
                if dest.read_bytes()!=canonical(record):
                    raise ValueError("immutable candidate collision")
                counts["already_saved"]+=1
                continue
            with dest.open("xb") as stream:
                stream.write(canonical(record))
                stream.flush()
                os.fsync(stream.fileno())
            counts["saved"]+=1
        except (ValueError,KeyError,TypeError,OSError):
            counts["rejected"]+=1
    return counts

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--inbox",default="fresh_inbox")
    p.add_argument("--out",default="fresh_snapshots")
    p.add_argument("--model-version",required=True)
    args=p.parse_args()
    print(json.dumps(capture(args.inbox,args.out,args.model_version)))

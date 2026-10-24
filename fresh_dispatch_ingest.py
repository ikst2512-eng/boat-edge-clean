"""Receive one externally-produced v5 snapshot from a GitHub repository_dispatch event.

The sender must be authorized to dispatch events to this repository. No odds,
race results, or research-only forecasts are accepted as substitutes.
"""
import argparse
import base64
import binascii
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from fresh_feed_builder import canonical, convert

def receive(event_bytes, out_dir, now=None, expected_action='fresh_v5_snapshot'):
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("aware now required")
    event=json.loads(event_bytes)
    if expected_action not in ("fresh_v5_snapshot","fresh_v5_candidate") or event.get("action") != expected_action:
        raise ValueError("wrong dispatch event")
    data=event.get("client_payload")
    if not isinstance(data, dict) or set(data)!={"snapshot_base64","model_version"}:
        raise ValueError("missing or unexpected dispatch payload")
    encoded=data["snapshot_base64"]
    if not isinstance(encoded,str) or len(encoded)>140000:
        raise ValueError("snapshot too large")
    try:
        original=base64.b64decode(encoded,validate=True)
    except (binascii.Error,ValueError) as exc:
        raise ValueError("invalid base64") from exc
    if not original or len(original)>100000:
        raise ValueError("snapshot byte size invalid")
    record=convert(original,data["model_version"])
    generated=datetime.fromisoformat(record["generated_at"])
    deadline=datetime.fromisoformat(record["deadline_at"])
    if generated>now or now>=deadline-timedelta(minutes=12):
        raise ValueError("not captured safely before cutoff")
    target=Path(out_dir)/f'{record["race_code"]}.json'
    target.parent.mkdir(parents=True,exist_ok=True)
    content=canonical(record)
    with target.open("xb") as f:
        f.write(content)
    return str(target)

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--event",required=True)
    p.add_argument("--out-dir",default="fresh_snapshots")
    p.add_argument("--event-type",choices=("fresh_v5_snapshot","fresh_v5_candidate"),default="fresh_v5_snapshot")
    a=p.parse_args()
    print(receive(Path(a.event).read_bytes(),a.out_dir,expected_action=a.event_type))

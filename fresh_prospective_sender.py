"""Submit one pre-existing v5 forecast as a NONPUBLIC prospective candidate.

No probability generation, formal publication, or scoring occurs here.
"""
import argparse
import base64
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.request import Request, urlopen
from fresh_feed_builder import convert
from fresh_formal_source_preflight import assess_collection, STATUS_URL

DISPATCH_URL="https://api.github.com/repos/ikst2512-eng/boat-edge-clean/dispatches"

def prepare(path,model_version,now=None):
    now=now or datetime.now(timezone.utc)
    p=Path(path)
    if p.is_symlink():
        raise ValueError("symbolic links forbidden")
    raw=p.read_bytes()
    if not raw or len(raw)>45000:
        raise ValueError("candidate size invalid")
    record=convert(raw,model_version)
    if record["race_code"]!=p.stem:
        raise ValueError("race name mismatch")
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("current timezone required")
    if datetime.fromisoformat(record["generated_at"])>now or now>=datetime.fromisoformat(record["deadline_at"])-timedelta(minutes=15):
        raise ValueError("candidate too late to dispatch")
    return {"event_type":"fresh_v5_candidate","client_payload":{
        "snapshot_base64":base64.b64encode(raw).decode("ascii"),
        "model_version":model_version}}

def dispatch(payload,token,source_status,opener=urlopen,now=None):
    if not isinstance(token,str) or not token:
        raise ValueError("FRESH_DISPATCH_TOKEN missing")
    if assess_collection(source_status)["ready"] is not True:
        raise ValueError("pre-result collection guards closed")
    if payload.get("event_type")!="fresh_v5_candidate":
        raise ValueError("public dispatch not allowed in prospective sender")
    # Recheck time after remote preflight and receiver lookup, immediately before POST.
    try:
        inner=payload["client_payload"]
        original=base64.b64decode(inner["snapshot_base64"],validate=True)
        record=convert(original,inner["model_version"])
        instant=now or datetime.now(timezone.utc)
        cutoff=datetime.fromisoformat(record["deadline_at"])-timedelta(minutes=15)
        if instant.tzinfo is None or instant.utcoffset() is None or instant>=cutoff:
            raise ValueError("dispatch cutoff passed")
    except (KeyError,TypeError) as exc:
        raise ValueError("invalid candidate dispatch body") from exc
    raw=json.dumps(payload,separators=(",",":")).encode()
    if len(raw)>65000:
        raise ValueError("GitHub dispatch payload too large")
    req=Request(DISPATCH_URL,data=raw,method="POST",headers={
        "Authorization":"Bearer "+token,
        "Accept":"application/vnd.github+json",
        "Content-Type":"application/json",
        "User-Agent":"boat-edge-nonpublic-candidate"})
    with opener(req,timeout=10) as response:
        if response.status!=204:
            raise ValueError("dispatch not accepted")
    return "accepted_not_frozen_or_witnessed"

def verify_receiver_on_main(opener=urlopen):
    """Fail closed if the repository_dispatch handler is absent on main."""
    url="https://api.github.com/repos/ikst2512-eng/boat-edge-clean/contents/.github/workflows/fresh-prospective-capture.yml?ref=main"
    request=Request(url,headers={"Accept":"application/vnd.github+json",
                                  "User-Agent":"boat-edge-prospective-readiness"})
    try:
        with opener(request,timeout=10) as response:
            data=json.load(response)
    except Exception as exc:
        raise ValueError("receiver on main not verified; dispatch blocked") from exc
    if not isinstance(data,dict) or data.get("type")!="file" or data.get("path")!=".github/workflows/fresh-prospective-capture.yml":
        raise ValueError("receiver workflow missing on default branch")
    return True

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("snapshot")
    parser.add_argument("--model-version",required=True)
    parser.add_argument("--dry-run",action="store_true")
    args=parser.parse_args()
    payload=prepare(args.snapshot,args.model_version)
    request=Request(STATUS_URL,headers={"User-Agent":"boat-edge-prospective"})
    with urlopen(request,timeout=10) as response:
        status=json.load(response)
    if assess_collection(status)["ready"] is not True:
        raise ValueError("upstream pre-result guards not closed")
    if args.dry_run:
        print(json.dumps({"candidate_valid":True,"sent":False,"formal_approved":False}))
    else:
        verify_receiver_on_main()
        print(dispatch(payload,os.environ.get("FRESH_DISPATCH_TOKEN",""),status))

if __name__=="__main__":
    main()

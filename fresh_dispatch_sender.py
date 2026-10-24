"""Send a pre-existing v5 immutable prediction to GitHub repository_dispatch.

Does not generate probabilities. Requires caller-supplied FRESH_DISPATCH_TOKEN.
Use a fine-grained token authorized to send repository dispatches.
"""
import argparse,base64,json,os
from datetime import datetime,timezone,timedelta
from pathlib import Path
from urllib.request import Request,urlopen
from fresh_feed_builder import convert
from fresh_formal_source_preflight import check_remote, assess_collection, STATUS_URL

URL="https://api.github.com/repos/ikst2512-eng/boat-edge-clean/dispatches"
def prepare(path,model_version,now=None,collection_only=False):
    now=now or datetime.now(timezone.utc)
    if now.tzinfo is None or now.utcoffset() is None:raise ValueError("timezone required")
    source=Path(path)
    if source.is_symlink():raise ValueError("symlink not permitted")
    raw=source.read_bytes()
    if len(raw)>45000:raise ValueError("dispatch size limit")
    record=convert(raw,model_version)
    if source.stem!=record["race_code"]:raise ValueError("race filename mismatch")
    created=datetime.fromisoformat(record["generated_at"])
    deadline=datetime.fromisoformat(record["deadline_at"])
    if created>now or now>=deadline-timedelta(minutes=15):
        raise ValueError("insufficient time to dispatch and witness")
    return {"event_type":"fresh_v5_candidate" if collection_only else "fresh_v5_snapshot","client_payload":{
        "snapshot_base64":base64.b64encode(raw).decode("ascii"),
        "model_version":model_version}}
def collection_check():
    with urlopen(Request(STATUS_URL,headers={"User-Agent":"boat-edge-fresh-collection"}),timeout=10) as response:
        return assess_collection(json.load(response))

def send(payload,token,opener=urlopen,source_check=check_remote,candidate_check=None):
    if payload.get("event_type")=="fresh_v5_candidate":
        status=(candidate_check or collection_check)()
    elif payload.get("event_type")=="fresh_v5_snapshot":
        status=source_check()
    else:
        raise ValueError("unrecognized dispatch event")
    if status.get("ready") is not True:
        raise ValueError("formal model source not ready: "+str(status.get("reason")))
    if not token:raise ValueError("FRESH_DISPATCH_TOKEN required")
    body=json.dumps(payload,separators=(",",":")).encode()
    if len(body)>65000:raise ValueError("dispatch exceeds request limit")
    req=Request(URL,data=body,method="POST",headers={
        "Authorization":"Bearer "+token,"Accept":"application/vnd.github+json",
        "Content-Type":"application/json","User-Agent":"boat-edge-fresh-v5-dispatcher"})
    with opener(req,timeout=10) as response:
        if response.status!=204:raise ValueError("GitHub did not accept dispatch")
    # 204 means queued, not frozen or witnessed. Check Actions independently.
    return "accepted_not_witnessed"
if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("snapshot")
    p.add_argument("--model-version",required=True)
    p.add_argument("--dry-run",action="store_true")
    p.add_argument("--collection-only",action="store_true",help="Send nonpublic candidate; never publish")
    a=p.parse_args()
    payload=prepare(a.snapshot,a.model_version,collection_only=a.collection_only)
    if a.dry_run:
        status=collection_check() if a.collection_only else check_remote()
        print(json.dumps({"valid_snapshot":True,"formal_source":status,"race_code":Path(a.snapshot).stem,"sent":False}))
    else:print(send(payload,os.environ.get("FRESH_DISPATCH_TOKEN","")))

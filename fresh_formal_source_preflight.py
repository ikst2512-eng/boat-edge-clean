"""Read-only preflight of the upstream formal model status.

A site-reference prediction or model readiness estimate cannot authorize
formal Fresh publication. This tool never generates or dispatches forecasts.
"""
import argparse,json
from pathlib import Path
from urllib.request import Request,urlopen

STATUS_URL="https://raw.githubusercontent.com/ikst2512-eng/boat-edge/main/data/formal_status.json"

def assess_collection(status):
    """Allow prospective evidence collection, never public Fresh approval."""
    if not isinstance(status,dict):
        raise ValueError("formal status must be a JSON object")
    guards=status.get("guards")
    if not isinstance(guards,dict) or any(
        guards.get(k) is not False for k in ("results_seen","unlock","scoring")
    ) or guards.get("RESULT_UNLOCK_TOKEN") is not None:
        return {"ready":False,"reason":"PRE_RESULT_GUARDS_NOT_CLOSED"}
    return {"ready":True,"reason":"COLLECTION_ONLY_NO_FORMAL_APPROVAL"}

def assess(status):
    if not isinstance(status,dict):
        raise ValueError("formal status must be a JSON object")
    guards=status.get("guards")
    if not isinstance(guards,dict) or any(guards.get(k) is not False for k in ("results_seen","unlock","scoring")):
        return {"ready":False,"reason":"FORMAL_GUARDS_NOT_CLOSED"}
    frozen=status.get("formalFirst100")
    if not isinstance(frozen,dict) or frozen.get("races")!=100 or not frozen.get("freezeManifestSha"):
        return {"ready":False,"reason":"FORMAL_FIRST100_NOT_FROZEN"}
    if status.get("connected") is not True or status.get("predictions_ready") is not True:
        return {"ready":False,"reason":"APPROVED_MODEL_NOT_CONNECTED"}
    approved=status.get("approved_prediction_sha256_by_race")
    if not isinstance(approved,dict) or len(approved)!=100:
        return {"ready":False,"reason":"APPROVED_PREDICTION_HASHES_NOT_COMPLETE"}
    return {"ready":True,"reason":"FORMAL_STATUS_PREFLIGHT_ONLY_NOT_FRESH_WITNESS"}

def check_remote():
    req=Request(STATUS_URL,headers={"User-Agent":"boat-edge-fresh-status-preflight"})
    with urlopen(req,timeout=10) as response:
        status=json.load(response)
    return assess(status)

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--file",help="Offline JSON status file; otherwise read the live upstream source")
    p.add_argument("--collection-only",action="store_true",help="No approval or public Fresh claims")
    a=p.parse_args()
    if a.collection_only:
        if a.file: status=json.loads(Path(a.file).read_text())
        else:
            with urlopen(Request(STATUS_URL,headers={"User-Agent":"boat-edge-collection-preflight"}),timeout=10) as response:
                status=json.load(response)
        result=assess_collection(status)
    else:
        result=assess(json.loads(Path(a.file).read_text())) if a.file else check_remote()
    print(json.dumps(result))
    if not result["ready"]:
        raise SystemExit(2)

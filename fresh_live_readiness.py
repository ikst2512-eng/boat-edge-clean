"""Read-only operational status for actual Fresh v5 collection.
Never sends an event, fabricates a prediction, opens results or unlocks scoring.
"""
import argparse,json
from pathlib import Path
from urllib.request import Request,urlopen
from fresh_formal_source_preflight import STATUS_URL,assess_collection,assess

def evaluate(status,receiver_installed,source_snapshot=None):
    collection=assess_collection(status)
    formal=assess(status)
    has_source=source_snapshot is not None
    return {"receiver_installed":bool(receiver_installed),
            "pre_result_collection_allowed":collection["ready"],
            "formal_source_approved":formal["ready"],
            "real_v5_source_verified":False if not has_source else None,
            "actual_dispatch_performed":False,
            "ready_to_send_real_candidate":False,
            "blockers":([ "receiver_missing_on_main" ] if not receiver_installed else [])
               + (["pre_result_guards_closed"] if not collection["ready"] else [])
               + (["external_v5_original_not_supplied"] if not has_source else ["external_v5_original_requires_independent_provenance_check"])
               + (["formal_parent_not_approved"] if not formal["ready"] else [])}

def get(url):
    with urlopen(Request(url,headers={"User-Agent":"fresh-readiness-read-only","Accept":"application/vnd.github+json"}),timeout=10) as r:
        return json.load(r)

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--status-file",help="Offline upstream status, otherwise fetch GitHub raw")
    p.add_argument("--receiver-installed",action="store_true",help="Only after confirming receiver on main")
    a=p.parse_args()
    status=json.loads(Path(a.status_file).read_bytes()) if a.status_file else get(STATUS_URL)
    print(json.dumps(evaluate(status,a.receiver_installed),sort_keys=True))

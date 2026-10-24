"""Check GitHub-issued artifact creation time separately from workflow start.

This is metadata evidence of artifact creation, not proof of upstream model
approval or official race deadline correctness. Candidate byte SHA validation
must be done independently against the downloaded artifact.
"""
from datetime import datetime,timedelta
from fresh_candidate_arrival_audit import check as check_run

def check_artifact(receipt,run,artifacts):
    check_run(receipt,run)
    if not isinstance(artifacts,dict):
        raise ValueError("artifact response required")
    rows=artifacts.get("artifacts")
    if not isinstance(rows,list):
        raise ValueError("artifact list missing")
    expected="prospective-v5-"+str(receipt["workflow_run_id"])
    matching=[a for a in rows if isinstance(a,dict) and a.get("name")==expected]
    if len(matching)!=1:
        raise ValueError("unique candidate artifact not found")
    item=matching[0]
    if (item.get("expired") is not False
        or type(item.get("id")) is not int
        or type(item.get("size_in_bytes")) is not int
        or item["size_in_bytes"]<=0
        or not isinstance(item.get("digest"),str)
        or not item["digest"].startswith("sha256:")
        or len(item["digest"])!=71):
        raise ValueError("invalid or expired artifact")
    workflow=item.get("workflow_run")
    if not isinstance(workflow,dict) or workflow.get("id")!=run["id"]:
        raise ValueError("artifact belongs to another run")
    cutoff=datetime.fromisoformat(receipt["deadline_at"])-timedelta(minutes=12)
    created=datetime.fromisoformat(item["created_at"].replace("Z","+00:00"))
    if any(x.tzinfo is None or x.utcoffset() is None for x in (cutoff,created)):
        raise ValueError("timezone required")
    if created>=cutoff:
        raise ValueError("artifact was created too late")
    return {"artifact_created_before_cutoff":True,
            "candidate_bytes_independently_verified":False,
            "official_deadline_independently_verified":False,
            "formal_approved":False,
            "artifact_id":item["id"],
            "race_code":receipt["race_code"]}

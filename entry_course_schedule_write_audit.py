"""Independent read-only audit of nonforecast scheduled runner write witnesses.

This checks actual immutable Git blob bytes and links the recorded Actions run ID
to a schedule-triggered run. It proves only observed operational write/read
evidence, not forecast publication or GitHub's independent receive timestamp.
"""
from datetime import datetime,timezone,timedelta
import json
import re
from entry_course_archive_integrity_audit import _read_blob

RUN_ID=re.compile(r"[0-9]{1,20}\Z")
JST=timezone(timedelta(hours=9))
SCHEMA="ENTRY_SCHEDULED_ACTIONS_WRITE_PROOF_V1"


def inspect_write_witness(day, kind, tree, scheduled_runs, fetch, *, repository):
    if kind not in ("t12","t2"):
        raise ValueError("write_witness_bad_kind")
    path=f"operations/scheduled-write-proof/{day}/{kind}.json"
    matches=[x for x in tree if isinstance(x,dict) and
             x.get("path")==path and x.get("type")=="blob"]
    if not matches:
        return {"status":"scheduled_write_proof_missing",
                "path":path,"write_proven":False,
                "forecast_record":False}
    if len(matches)!=1:
        return {"status":"scheduled_write_proof_duplicate_tree_entry",
                "path":path,"write_proven":False,
                "forecast_record":False}
    try:
        raw=_read_blob(matches[0].get("sha"),fetch,repository)
        witness=json.loads(raw)
        if not isinstance(witness,dict):
            raise ValueError("write_witness_bad_object")
        run_id=witness.get("run_id")
        observed=witness.get("received_at_local")
        at=datetime.fromisoformat(observed) if isinstance(observed,str) else None
        if (witness.get("schema")!=SCHEMA or
                witness.get("date_jst")!=day or
                witness.get("workflow_kind")!=kind or
                witness.get("event_name")!="schedule" or
                witness.get("forecast_record") is not False or
                witness.get("formal") is not False or
                witness.get("independent_github_server_first_seen_verified") is not False or
                type(run_id) is not str or not RUN_ID.fullmatch(run_id) or
                at is None or at.utcoffset() is None or
                at.astimezone(JST).strftime("%Y%m%d")!=day):
            raise ValueError("write_witness_invalid_schema_or_clock")
        identified=[x for x in scheduled_runs if str(x["id"])==run_id]
        if len(identified)!=1:
            return {"status":"scheduled_write_proof_run_not_in_schedule_history",
                    "path":path,"run_id":run_id,"write_proven":False,
                    "forecast_record":False}
        started=datetime.fromisoformat(identified[0]["created_at"])
        if at < started:
            raise ValueError("write_witness_earlier_than_run_created")
        return {"status":"scheduled_write_proof_run_linked",
                "path":path,"run_id":run_id,
                "write_proven":True,"forecast_record":False,
                "git_blob_sha_verified":True,
                "original_local_receive_time":at.isoformat(),
                "independent_server_first_seen_verified":False}
    except (ValueError,TypeError,KeyError,UnicodeError,OSError) as exc:
        return {"status":"scheduled_write_proof_invalid_or_unreadable",
                "path":path,"error_type":type(exc).__name__,
                "write_proven":False,"forecast_record":False}

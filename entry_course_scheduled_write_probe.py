"""Non-forecast daily write/read proof from an ACTUAL scheduled Actions runner.

This is an operational permission witness only. It does not freeze a racing
prediction, authenticate upstream data, or prove GitHub server first-seen time.
One immutable canary per JST day and workflow avoids 5-minute-run clutter.
"""
from datetime import datetime, timezone, timedelta
import hashlib
import json
import os
import re

JST=timezone(timedelta(hours=9))
RUN_ID=re.compile(r"[0-9]{1,20}\Z")
KINDS={"t12","t2"}


def schedule_canary(kind, *, read, create, now, event_name, run_id):
    if kind not in KINDS:
        raise ValueError("scheduled_probe_invalid_kind")
    if event_name!="schedule":
        return {"status":"skipped_non_schedule","is_forecast":False,
                "write_permission_tested_this_run":False}
    if type(run_id) is not str or not RUN_ID.fullmatch(run_id):
        raise ValueError("scheduled_probe_missing_run_id")
    if not isinstance(now,datetime) or now.utcoffset() is None:
        raise ValueError("scheduled_probe_invalid_clock")
    today=now.astimezone(JST).strftime("%Y%m%d")
    path=f"operations/scheduled-write-proof/{today}/{kind}.json"
    old=read(path)
    if old is not None:
        try:
            item=json.loads(old)
        except (ValueError,UnicodeError) as exc:
            raise ValueError("scheduled_probe_existing_invalid_json") from exc
        if (type(item) is not dict or
                item.get("schema")!="ENTRY_SCHEDULED_ACTIONS_WRITE_PROOF_V1" or
                item.get("date_jst")!=today or item.get("workflow_kind")!=kind or
                item.get("forecast_record") is not False or
                item.get("formal") is not False or
                item.get("event_name")!="schedule" or
                type(item.get("run_id")) is not str or
                not RUN_ID.fullmatch(item["run_id"])):
            raise ValueError("scheduled_probe_existing_invalid")
        if read(path)!=old:
            raise ValueError("scheduled_probe_existing_changed")
        return {"status":"previous_schedule_proof_readback",
                "path":path,"first_witness_run_id":item["run_id"],
                "sha256":hashlib.sha256(old).hexdigest(),
                "is_forecast":False,"write_permission_tested_this_run":False}
    payload={
        "schema":"ENTRY_SCHEDULED_ACTIONS_WRITE_PROOF_V1",
        "date_jst":today,"workflow_kind":kind,"event_name":"schedule",
        "run_id":run_id,"received_at_local":now.isoformat(),
        "formal":False,"forecast_record":False,
        "independent_github_server_first_seen_verified":False
    }
    raw=(json.dumps(payload,ensure_ascii=False,sort_keys=True)+"\n").encode()
    create(path,raw)
    if read(path)!=raw:
        raise ValueError("scheduled_probe_remote_readback_failed")
    return {"status":"new_scheduled_runner_write_proof",
            "path":path,"first_witness_run_id":run_id,
            "sha256":hashlib.sha256(raw).hexdigest(),
            "is_forecast":False,"write_permission_tested_this_run":True}


def from_environment(kind, read, create, *, environ=None, now=None):
    env=environ if environ is not None else os.environ
    current=now if now is not None else datetime.now(JST)
    return schedule_canary(kind,read=read,create=create,now=current,
                           event_name=env.get("GITHUB_EVENT_NAME"),
                           run_id=env.get("GITHUB_RUN_ID"))

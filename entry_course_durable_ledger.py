"""Append-only GitHub archive for source-backed late-preview research captures.

No official provenance, no independent first-seen certificate. GitHub readback
proves only that bytes match the copy created by the publishing job.
"""
import base64
from datetime import datetime, timezone
from itertools import permutations
import hashlib
import json
import re
import subprocess

BRANCH="entry-course-evidence-ledger"
VALID={"-".join(map(str,p)) for p in permutations(range(1,7),3)}
CODE=re.compile(r"20[0-9]{10}\Z")
HASH=re.compile(r"[a-f0-9]{64}\Z")
REPO=re.compile(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+\Z")


def _clock(value):
    try:
        t=datetime.fromisoformat(value)
        return t if t.utcoffset() is not None else None
    except (TypeError,ValueError):
        return None


def prepare(raw, *, now=None):
    """Validate exact prospective payload, return immutable branch path."""
    if type(raw) is not bytes or not raw or len(raw)>150_000:
        raise ValueError("invalid_late_capture_size")
    try:
        data=json.loads(raw)
    except (ValueError,UnicodeError) as exc:
        raise ValueError("invalid_late_capture_json") from exc
    if type(data) is not dict or data.get("schema")!="entry-course-late-preview-study-v1":
        raise ValueError("invalid_late_capture_schema")
    code=data.get("race_code")
    if type(code) is not str or not CODE.fullmatch(code):
        raise ValueError("invalid_late_capture_race")
    if (data.get("research_only") is not True or data.get("formal") is not False
            or data.get("not_equivalent_to_t12") is not True
            or data.get("entry_source")!="third_party_timestamped_preview"
            or data.get("independent_remote_first_seen_verified") is not False):
        raise ValueError("invalid_late_capture_provenance")
    cutoff=_clock(data.get("cutoff_at"))
    generated=_clock(data.get("frozen_at"))
    reference=_clock(data.get("reference_baseline_cutoff_at"))
    write=_clock(data.get("write_received_at"))
    now=now or datetime.now(timezone.utc)
    if (not cutoff or not generated or not reference or not write
            or now.utcoffset() is None or
            not reference < generated <= write < cutoff or now>=cutoff):
        raise ValueError("late_capture_not_before_cutoff")
    for name in ("baseline","course","course_plus_st"):
        row=data.get(name)
        if type(row) is not list or len(row)!=120 or len(set(row))!=120 or set(row)!=VALID:
            raise ValueError("invalid_late_"+name+"_ranking")
    entry=data.get("entry")
    if type(entry) is not list or len(entry)!=6 or any(type(n)!=int for n in entry) or set(entry)!=set(range(1,7)):
        raise ValueError("invalid_late_entry")
    receipts=data.get("source_receipts")
    if type(receipts) is not list or len(receipts)<2:
        raise ValueError("missing_late_receipts")
    for receipt in receipts:
        timestamp=_clock(receipt.get("received_at")) if type(receipt) is dict else None
        if (not timestamp or timestamp>generated or timestamp>=cutoff or
                not HASH.fullmatch(str(receipt.get("sha256") or ""))):
            raise ValueError("invalid_late_receipt")
    return f"entry_course/{code[:8]}/{code}.json"


def publish(raw, remote_read, remote_create, *, clock=None):
    """Create without overwrite and byte-verify before cutoff; fail closed."""
    now=clock or (lambda:datetime.now(timezone.utc))
    path=prepare(raw,now=now())
    before=remote_read(path)
    if before is not None and before!=raw:
        raise ValueError("immutable_late_capture_conflict")
    if before is None:
        remote_create(path,raw)
        state="new_append_only_late_capture"
    else:
        state="already_identical_late_capture"
    if remote_read(path)!=raw:
        raise ValueError("late_capture_remote_readback_mismatch")
    if now()>=_clock(json.loads(raw)["cutoff_at"]):
        # A remote write may exist, but it must never count as in-time evidence.
        raise ValueError("remote_published_after_late_cutoff")
    return {"status":state,"stored":True,"path":path,"branch":BRANCH,
            "sha256":hashlib.sha256(raw).hexdigest(),
            "formal":False,"research_only":True,
            "independent_remote_first_seen_verified":False}


# Non-forecast canary: verify the scheduled job's write permission ahead of
# the first actual course forecast. This is never counted as a race capture.
WRITE_PROBE_PATH="operations/entry-course-write-access-v1.json"
WRITE_PROBE_BYTES=(b'{"formal":false,"forecast_record":false,'
                   b'"schema":"ENTRY_COURSE_LEDGER_WRITE_ACCESS_PROBE_V1"}' + bytes([10]))


def verify_write_access(remote_read,remote_create):
    existing=remote_read(WRITE_PROBE_PATH)
    if existing is None:
        remote_create(WRITE_PROBE_PATH,WRITE_PROBE_BYTES)
        status="new_write_probe"
    elif existing==WRITE_PROBE_BYTES:
        status="existing_write_probe_readback"
    else:
        raise ValueError("course_ledger_write_probe_collision")
    if remote_read(WRITE_PROBE_PATH)!=WRITE_PROBE_BYTES:
        raise ValueError("course_ledger_write_probe_readback_mismatch")
    return {"status":status,"path":WRITE_PROBE_PATH,
            "formal":False,"forecast_record":False,
            "write_permission_tested_this_run":status=="new_write_probe"}



def _t12_trace(path, phase, **fields):
    """Log only digest and API outcome, never source data or credentials."""
    if not path.startswith("t12_baselines/"):
        return
    record={"path":path,"phase":phase,
            "observed_utc":datetime.now(timezone.utc).isoformat(),**fields}
    print("T12_LEDGER_TRACE="+json.dumps(record,sort_keys=True))


def _http_status(stderr):
    match=re.search(rb"HTTP (\d{3})",stderr or b"")
    return int(match.group(1)) if match else None


def _git_blob_sha1(raw):
    return hashlib.sha1(b"blob "+str(len(raw)).encode("ascii")+b"\0"+raw).hexdigest()


def _gh(args, *, diagnostic_path=None):
    response=subprocess.run(["gh","api",*args],capture_output=True,timeout=30)
    if response.returncode:
        if diagnostic_path is not None:
            _t12_trace(diagnostic_path,"PUT",state="api_error",
                       http_status=_http_status(response.stderr))
        raise ValueError("course_ledger_github_api_failed")
    return response.stdout


def github_ops(repository):
    if not isinstance(repository,str) or not REPO.fullmatch(repository):
        raise ValueError("invalid_repo")
    def read(path):
        r=subprocess.run(["gh","api","-X","GET",
            f"repos/{repository}/contents/{path}?ref={BRANCH}"],
            capture_output=True,timeout=30)
        if r.returncode:
            code=_http_status(r.stderr)
            _t12_trace(path,"GET",state="missing_404" if code==404 else "api_error",
                       http_status=code)
            if b"HTTP 404" in r.stderr:
                return None
            raise ValueError("course_ledger_read_failed")
        item=json.loads(r.stdout)
        if item.get("type")!="file":
            _t12_trace(path,"GET",state="nonfile")
            raise ValueError("course_ledger_nonfile")
        observed=base64.b64decode(item["content"])
        api_blob=item.get("sha")
        api_blob=api_blob if type(api_blob) is str and re.fullmatch(r"[a-f0-9]{40}",api_blob) else None
        _t12_trace(path,"GET",state="bytes_received",
                   bytes_sha256=hashlib.sha256(observed).hexdigest(),
                   api_blob_sha1=api_blob,
                   api_blob_matches_bytes=(_git_blob_sha1(observed)==api_blob) if api_blob else None)
        return observed
    def create(path,raw):
        encoded=base64.b64encode(raw).decode("ascii")
        response=_gh(["-X","PUT",f"repos/{repository}/contents/{path}",
             "-f","message=research: preserve append-only entry-course evidence",
             "-f",f"branch={BRANCH}","-f",f"content={encoded}"],
             diagnostic_path=path)
        if path.startswith("t12_baselines/"):
            try:
                receipt=json.loads(response)
                api_blob=receipt.get("content",{}).get("sha")
                api_commit=receipt.get("commit",{}).get("sha")
                api_blob=api_blob if type(api_blob) is str and re.fullmatch(r"[a-f0-9]{40}",api_blob) else None
                api_commit=api_commit if type(api_commit) is str and re.fullmatch(r"[a-f0-9]{40}",api_commit) else None
            except (ValueError,TypeError,AttributeError):
                api_blob=api_commit=None
            _t12_trace(path,"PUT",state="api_returned_success",
                       bytes_sha256=hashlib.sha256(raw).hexdigest(),
                       expected_blob_sha1=_git_blob_sha1(raw),
                       api_blob_sha1=api_blob,api_commit_sha=api_commit,
                       api_blob_matches_bytes=(_git_blob_sha1(raw)==api_blob) if api_blob else None)
    return read,create

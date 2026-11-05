"""Durably preserve ALL-MODE result-blind shadows on an existing append-only branch.

This is a bounded remote OBSERVATION, not an independently attested first
remote receipt or official T-12 certified candidate. No production changes,
no outcome reads, no auto-merge, no new workflows or ledgers.
"""
import argparse
import base64
import hashlib
import json
import os
import re
import subprocess
import urllib.request
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime
from pathlib import Path

from four_mode_all_shadow_reference_review import validate_capture_before_any_results
from four_mode_all_mode_same_job_shadow import SCHEMA
from third_rate_evidence_ledger import BRANCH, _github_ops

RUN = re.compile(r"[1-9][0-9]{0,16}\Z")
SHA = re.compile(r"[0-9a-f]{40}\Z")
RACE = re.compile(r"20[0-9]{10}\Z")
REPO = re.compile(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+\Z")


def prepare(raw, root, run_id, attempt, git=None):
    if (type(raw) is not bytes or not raw or len(raw) > 2_000_000 or
            type(run_id) is not str or not RUN.fullmatch(run_id) or
            type(attempt) is not str or not RUN.fullmatch(attempt)):
        raise ValueError("invalid_evidence_or_run_identity")
    document = json.loads(raw)
    if (type(document) is not dict or document.get("schema") != SCHEMA or
            document.get("formal") is not False or
            document.get("candidate_first_remote_receipt_verified") is not False or
            document.get("production_forecast_changed") is not False):
        raise ValueError("unsafe_or_forged_evidence")
    # Validates every candidate against exact original bytes, output of
    # selector, finish clocks and no outcome-derived features.
    roster, _, published = validate_capture_before_any_results([document], root)
    if document["frozen_count"] != sum(v is not None for v in roster.values()):
        raise ValueError("frozen_count_replay_mismatch")
    if published == 0:
        return None
    commit = document.get("publication_commit_sha")
    if (type(commit) is not str or SHA.fullmatch(commit) is None or
            type(document.get("candidate_method_sha256")) is not str or
            len(document["candidate_method_sha256"]) != 64):
        raise ValueError("invalid_publication_or_method_identity")
    command = git or (lambda args: subprocess.check_output(
        ["git", *args], cwd=root, timeout=30))
    def run(*args):
        value = command(list(args))
        return value if type(value) is bytes else value.encode("utf-8")
    if run("rev-parse", "HEAD").decode().strip() != commit:
        raise ValueError("first_add_head_mismatch")
    run("merge-base", "--is-ancestor", commit, "origin/main")
    files=run("diff-tree","--no-commit-id","--name-only","--diff-filter=A",
              "-r",commit,"--","four_mode_forecasts/").decode().splitlines()
    expected={f"four_mode_forecasts/{code}.json" for code in roster}
    if (len(files)!=published or len(set(files))!=published
            or set(files)!=expected):
        raise ValueError("published_git_first_add_roster_mismatch")
    days=set()
    for code in roster:
        if not RACE.fullmatch(code):
            raise ValueError("invalid_race")
        days.add(code[:8])
        path=f"four_mode_forecasts/{code}.json"
        first_bytes=run("show",commit+":"+path)
        local=Path(root)/path
        if (local.is_symlink() or not local.is_file() or
                first_bytes != local.read_bytes()):
            raise ValueError("first_add_original_bytes_mismatch")
    if len(days)!=1:
        raise ValueError("multiple_capture_days")
    return f"four_mode_all/{next(iter(days))}/run-{run_id}-attempt-{attempt}.json"


def remote_observe(repository, path):
    """Read back exact remote candidate JSON and an uncached GitHub server Date.

    This DOES NOT prove the first receipt and does not establish an official
    source timestamp. Fail closed on missing header, cache or byte mismatch.
    """
    if (type(repository) is not str or REPO.fullmatch(repository) is None or
            type(path) is not str or not path.startswith("four_mode_all/") or
            not re.fullmatch(r"four_mode_all/20[0-9]{6}/run-[1-9][0-9]*-attempt-[1-9][0-9]*\.json",path)):
        raise ValueError("invalid_remote_observation_target")
    token=os.environ.get("GH_TOKEN")
    if not token:
        raise ValueError("missing_github_token")
    endpoint=f"https://api.github.com/repos/{repository}/contents/{path}?ref={BRANCH}"
    req=urllib.request.Request(endpoint,headers={
        "Authorization":"Bearer "+token,
        "Accept":"application/vnd.github+json",
        "X-GitHub-Api-Version":"2022-11-28",
        "Cache-Control":"no-cache",
        "User-Agent":"boat-edge-all-mode-shadow-readback",
    })
    with urllib.request.urlopen(req,timeout=25) as response:
        if response.status!=200 or response.headers.get("Age") is not None:
            raise ValueError("remote_observation_invalid_or_cached")
        server=parsedate_to_datetime(response.headers.get("Date",""))
        if server.tzinfo is None or server.utcoffset()!=timedelta(0):
            raise ValueError("github_server_date_missing_or_not_utc")
        received=json.loads(response.read(3_000_000))
    if (type(received) is not dict or received.get("type")!="file" or
            received.get("path")!=path or received.get("encoding")!="base64" or
            type(received.get("content")) is not str):
        raise ValueError("invalid_remote_artifact_metadata")
    content=base64.b64decode(received["content"],validate=False)
    if not content or len(content)>2_000_000:
        raise ValueError("invalid_remote_artifact_size")
    expected_git_blob=hashlib.sha1(
        b"blob "+str(len(content)).encode("ascii")+b"\0"+content).hexdigest()
    if received.get("sha")!=expected_git_blob:
        raise ValueError("github_remote_blob_digest_mismatch")
    return server, content


def publish(raw, root, run_id, attempt, remote_read, remote_create, observer, git=None):
    path=prepare(raw, root, run_id, attempt, git=git)
    if path is None:
        return {"schema":"FOUR_MODE_ALL_REMOTE_LEDGER_V1",
                "status":"nothing_published_in_capture",
                "stored":False,"formal":False,
                "candidate_first_remote_receipt_verified":False,
                "observed_before_t_minus_12":0}
    previous=remote_read(path)
    if previous is None:
        remote_create(path, raw, run_id)
        status="new_append_only_candidate_preserved"
    elif previous == raw:
        status="existing_identical_candidate"
    else:
        raise ValueError("immutable_candidate_collision")
    if remote_read(path)!=raw:
        raise ValueError("candidate_remote_readback_mismatch")
    observed, bytes_from_remote=observer(path)
    if (type(bytes_from_remote) is not bytes or bytes_from_remote != raw
            or not isinstance(observed,datetime) or
            observed.utcoffset()!=timedelta(0)):
        raise ValueError("candidate_server_observation_not_verified")
    document=json.loads(raw)
    before=0; after=0
    rows=[]
    for row in document["records"]:
        if row["status"]!="frozen_local_before_T_minus_12_research_only":
            continue
        cutoff=datetime.fromisoformat(row["candidate_last_safe_jst"])
        generated=datetime.fromisoformat(row["frozen_at_jst"])
        state=("github_observed_candidate_before_T12" if
               generated + timedelta(seconds=1)<observed<cutoff else
               "candidate_observation_late_or_same_second")
        before+=int(state=="github_observed_candidate_before_T12")
        after+=int(state!="github_observed_candidate_before_T12")
        rows.append({"race_code":row["race_code"],"status":state})
    if len(rows)!=document["frozen_count"] or before+after!=len(rows):
        raise ValueError("remote_observation_partition_error")
    report = {"schema":"FOUR_MODE_ALL_REMOTE_LEDGER_V1","status":status,
            "stored":True,"formal":False,"model_promotion_allowed":False,
            "candidate_first_remote_receipt_verified":False,
            "candidate_github_server_observation_not_first_receipt":True,
            "capture_run_id":run_id,"capture_run_attempt":attempt,
            "branch":BRANCH,"path":path,"candidate_sha256":hashlib.sha256(raw).hexdigest(),
            "candidate_observed_github_server_date_utc":observed.isoformat(),
            "published_count":document["published_count"],
            "locally_frozen_count":document["frozen_count"],
            "observed_before_t_minus_12":before,
            "observed_late_or_ambiguous":after,"records":rows}
    # Preserve the observation separately so its *reported* GitHub server Date
    # cannot disappear when the Actions artifact expires after 30 days.
    # This is a readback observation, NOT proof of independent first receipt.
    note_path=path.replace("four_mode_all/","four_mode_all_observation/",1)
    old_note=remote_read(note_path)
    if old_note is None:
        frozen_note=(json.dumps(report,ensure_ascii=False,sort_keys=True,
                     separators=(",",":"))+"\n").encode("utf-8")
        remote_create(note_path,frozen_note,run_id)
        note_status="new_immutable_observation_note"
        if remote_read(note_path)!=frozen_note:
            raise ValueError("observation_note_remote_readback_mismatch")
    else:
        if type(old_note) is not bytes or len(old_note)>100_000:
            raise ValueError("invalid_prior_observation_note")
        try:
            previous=json.loads(old_note)
        except (ValueError,UnicodeError) as exc:
            raise ValueError("corrupt_prior_observation_note") from exc
        if (type(previous) is not dict or
                previous.get("schema")!="FOUR_MODE_ALL_REMOTE_LEDGER_V1" or
                previous.get("path")!=path or
                previous.get("candidate_sha256")!=report["candidate_sha256"] or
                previous.get("capture_run_id")!=run_id or
                previous.get("capture_run_attempt")!=attempt or
                previous.get("formal") is not False or
                previous.get("candidate_first_remote_receipt_verified") is not False or
                type(previous.get("records")) is not list or
                len(previous["records"])!=document["frozen_count"] or
                previous.get("observed_before_t_minus_12",0)+
                    previous.get("observed_late_or_ambiguous",0)!=document["frozen_count"]):
            raise ValueError("existing_observation_note_collision")
        try:
            prior_when=datetime.fromisoformat(previous["candidate_observed_github_server_date_utc"])
        except (ValueError,KeyError,TypeError) as exc:
            raise ValueError("existing_observation_time_invalid") from exc
        if prior_when.utcoffset()!=timedelta(0):
            raise ValueError("existing_observation_time_not_UTC")
        expected=[]
        for row in document["records"]:
            if row["status"]!="frozen_local_before_T_minus_12_research_only":
                continue
            cutoff=datetime.fromisoformat(row["candidate_last_safe_jst"])
            generated=datetime.fromisoformat(row["frozen_at_jst"])
            state=("github_observed_candidate_before_T12" if
                   generated+timedelta(seconds=1)<prior_when<cutoff else
                   "candidate_observation_late_or_same_second")
            expected.append({"race_code":row["race_code"],"status":state})
        if (previous["records"]!=expected or
                previous["observed_before_t_minus_12"]!=sum(
                    r["status"]=="github_observed_candidate_before_T12" for r in expected) or
                previous["observed_late_or_ambiguous"]!=sum(
                    r["status"]!="github_observed_candidate_before_T12" for r in expected)):
            raise ValueError("existing_observation_note_timing_inconsistent")
        if remote_read(note_path)!=old_note:
            raise ValueError("existing_observation_note_changed")
        report=previous
        note_status="existing_identical_observation_note"
    report["status"]=status
    report["immutable_observation_note_path"]=note_path
    report["immutable_observation_note_status"]=note_status
    return report


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--root",type=Path,default=Path("."))
    p.add_argument("--input",type=Path,default=Path("four-mode-evidence/all-mode-shadow.json"))
    p.add_argument("--output",type=Path,default=Path("four-mode-evidence/all-mode-shadow-ledger.json"))
    a=p.parse_args()
    try:
        if (a.input.is_symlink() or not a.input.is_file()
                or a.input.stat().st_size>2_000_000):
            raise ValueError("missing_or_unsafe_shadow_artifact")
        get,create=_github_ops(os.environ["GITHUB_REPOSITORY"])
        repo=os.environ["GITHUB_REPOSITORY"]
        verdict=publish(a.input.read_bytes(),a.root,os.environ["GITHUB_RUN_ID"],
            os.environ.get("GITHUB_RUN_ATTEMPT","1"),get,create,
            lambda path:remote_observe(repo,path))
    except (OSError,ValueError,TypeError,KeyError,UnicodeError,
            subprocess.SubprocessError) as exc:
        verdict={"schema":"FOUR_MODE_ALL_REMOTE_LEDGER_V1",
                 "status":"candidate_ledger_preservation_failed",
                 "stored":False,"formal":False,
                 "candidate_first_remote_receipt_verified":False,
                 "error_type":type(exc).__name__}
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(verdict,ensure_ascii=False,sort_keys=True,indent=2)+"\n",
                        encoding="utf-8")
    print("FOUR_MODE_ALL_CANDIDATE_LEDGER="+json.dumps(verdict,sort_keys=True))
    if verdict["status"]=="candidate_ledger_preservation_failed":
        raise SystemExit(2)


if __name__=="__main__":
    main()

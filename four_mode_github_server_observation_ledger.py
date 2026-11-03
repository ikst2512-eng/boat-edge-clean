"""Preserve GitHub API server-observation bytes as a write-once research record.

The ledger branch is separate from main. The GitHub response Date is an
observation, NOT a server first-receipt attestation. No formal accuracy.
"""
import argparse
import hashlib
import json
import os
import re
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

from third_rate_evidence_ledger import BRANCH, _github_ops

SCHEMA="FOUR_MODE_GITHUB_REMOTE_OBSERVATION_V1"
RUN=re.compile(r"[1-9][0-9]{0,16}\Z")
SHA=re.compile(r"[a-f0-9]{40}\Z")
HEX=re.compile(r"[a-f0-9]{64}\Z")
CODE=re.compile(r"20[0-9]{10}\Z")
JST=timezone(timedelta(hours=9))
VALID=("github_server_observed_before_t_minus_12",
       "github_server_observed_after_t_minus_12",
       "remote_observation_unverified")


def prepare(original,root,run_id,attempt,git=None):
    if (type(run_id) is not str or RUN.fullmatch(run_id) is None or
            type(attempt) is not str or RUN.fullmatch(attempt) is None):
        raise ValueError("invalid_run")
    if type(original) is not bytes or not original or len(original)>2_000_000:
        raise ValueError("invalid_observation_bytes")
    data=json.loads(original)
    if not isinstance(data,dict) or data.get("schema")!=SCHEMA or (
            data.get("formal") is not False or
            data.get("independent_first_remote_receipt_verified") is not False or
            data.get("github_server_observation_not_first_receipt") is not True or
            data.get("production_forecast_changed") is not False):
        raise ValueError("invalid_observation_schema")
    if data.get("status")=="no_confirmed_publication":
        if data.get("records")!=[]:raise ValueError("unexpected_unpublished_rows")
        return None
    count=data.get("publication_count")
    sha=data.get("publication_commit_sha")
    records=data.get("records")
    if (data.get("status")!="remote_observation_audited_nonformal" or
            type(count) is not int or not 1<=count<=500 or
            type(sha) is not str or SHA.fullmatch(sha) is None or
            type(records) is not list or len(records)!=count):
        raise ValueError("bad_observation_publication")
    # The independent future-only protocol starts on Nov 4. Older capture
    # runs are not failures and must not be stored as future evidence.
    if all(type(r) is dict and type(r.get("race_code")) is str and
           r["race_code"][:8]<"20261104" for r in records):
        return None
    git=git or (lambda *args: subprocess.check_output(
        ["git",*args],cwd=root,timeout=30))
    seen=set();by_status={name:0 for name in VALID}
    days=set()
    names=set(git("diff-tree","--no-commit-id","--name-only",
                  "--diff-filter=A","-r",sha,"--","four_mode_forecasts/").decode().splitlines())
    if len(names)!=count:raise ValueError("git_add_roster_mismatch")
    for row in records:
        if type(row) is not dict or type(row.get("race_code")) is not str:
            raise ValueError("invalid_observation_row")
        code=row["race_code"]
        state=row.get("status")
        if (CODE.fullmatch(code) is None or code in seen or
                code[:8]<"20261104" or state not in VALID):
            raise ValueError("invalid_race_or_status")
        seen.add(code);days.add(code[:8]);by_status[state]+=1
        name=f"four_mode_forecasts/{code}.json"
        if name not in names or row.get("first_add_commit")!=sha:
            raise ValueError("first_add_mismatch")
        source=Path(root)/name
        if source.is_symlink() or not source.is_file() or source.stat().st_size>30000:
            raise ValueError("missing_source_file")
        exact=git("show",sha+":"+name)
        if exact!=source.read_bytes():
            raise ValueError("original_git_blob_changed")
        if state=="remote_observation_unverified":
            continue
        if (row.get("first_add_blob_matches_remote") is not True or
                type(row.get("original_sha256")) is not str or
                HEX.fullmatch(row["original_sha256"]) is None or
                hashlib.sha256(exact).hexdigest()!=row["original_sha256"]):
            raise ValueError("remote_blob_digest_mismatch")
        event=datetime.fromisoformat(row["github_api_server_date_utc"])
        cutoff=datetime.fromisoformat(row["deadline_minus_12_jst"])
        # A forged cutoff can make a late server observation appear early.
        # Bind T-12 to the exact first-added Git blob, not the field reported
        # by the observation artifact itself.
        original_forecast=json.loads(exact)
        if (not isinstance(original_forecast,dict) or
                original_forecast.get("race_code")!=code or
                not isinstance(original_forecast.get("deadline_jst"),str)):
            raise ValueError("invalid_original_race_deadline")
        deadline=datetime.fromisoformat(original_forecast["deadline_jst"])
        if (deadline.utcoffset()!=timedelta(hours=9) or
                deadline.strftime("%Y%m%d")!=code[:8] or
                cutoff!=deadline-timedelta(minutes=12)):
            raise ValueError("observation_cutoff_disagrees_with_original")
        if (event.utcoffset()!=timedelta(0) or
                cutoff.utcoffset()!=timedelta(hours=9) or
                cutoff.strftime("%Y%m%d")!=code[:8]):
            raise ValueError("bad_remote_observation_time")
        expected=("github_server_observed_before_t_minus_12" if event<cutoff
                  else "github_server_observed_after_t_minus_12")
        if state!=expected:
            raise ValueError("false_early_observation_label")
    if len(days)!=1:
        raise ValueError("multi_day_observation_not_supported")
    for key,field in (("github_server_observed_before_t_minus_12",
                       "observed_before_t_minus_12"),
                      ("github_server_observed_after_t_minus_12",
                       "observed_after_t_minus_12"),
                      ("remote_observation_unverified","unverified_count")):
        if data.get(field)!=by_status[key]:
            raise ValueError("observation_count_mismatch")
    return f"github_server/{next(iter(days))}/run-{run_id}-attempt-{attempt}.json"


def publish(original,root,run_id,attempt,remote_read,remote_create,git=None):
    path=prepare(original,root,run_id,attempt,git)
    if path is None:
        return {"status":"no_published_forecast","stored":False,"formal":False}
    old=remote_read(path)
    if old is None:
        remote_create(path,original,run_id)
        verdict="new_append_only_observation"
    elif old==original:
        verdict="already_preserved_identical"
    else:
        raise ValueError("immutable_observation_collision")
    if remote_read(path)!=original:
        raise ValueError("observation_readback_mismatch")
    return {"status":verdict,"branch":BRANCH,"path":path,
            "sha256":hashlib.sha256(original).hexdigest(),
            "stored":True,"formal":False,
            "independent_first_remote_receipt_verified":False}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--root",type=Path,default=Path("."))
    parser.add_argument("--input",type=Path,default=Path(
        "four-mode-evidence/github-server-observation.json"))
    parser.add_argument("--output",type=Path,default=Path(
        "four-mode-evidence/github-server-observation-ledger.json"))
    args=parser.parse_args()
    try:
        if args.input.is_symlink() or not args.input.is_file():
            raise ValueError("observation_artifact_missing")
        get,put=_github_ops(os.environ["GITHUB_REPOSITORY"])
        result=publish(args.input.read_bytes(),args.root,
                       os.environ["GITHUB_RUN_ID"],
                       os.environ.get("GITHUB_RUN_ATTEMPT","1"),get,put)
    except (OSError,KeyError,ValueError,TypeError,subprocess.SubprocessError) as exc:
        result={"status":"observation_preservation_failed","stored":False,
                "formal":False,"error_type":type(exc).__name__}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,sort_keys=True)+"\n",
                           encoding="utf-8")
    print("GITHUB_SERVER_OBSERVATION_LEDGER="+json.dumps(result,sort_keys=True))
    if result["status"]=="observation_preservation_failed":
        raise SystemExit(2)

if __name__=="__main__":
    main()

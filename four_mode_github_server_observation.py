"""GitHub API server-Date observation of an already-published forecast blob.

A successful authenticated API GET with a GitHub-origin Date header can give
a bounded observation of remote availability. It does not prove the first
remote receipt, and a local/Git committer timestamp is never substituted.
"""
import base64
import hashlib
import json
import os
import re
import subprocess
import urllib.error
import urllib.request
from collections import Counter
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

SHA=re.compile(r"[a-f0-9]{40}\Z")
RACE=re.compile(r"four_mode_forecasts/(20[0-9]{10})\.json\Z")
REPO=re.compile(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+\Z")
JST=timezone(timedelta(hours=9))
SCHEMA="FOUR_MODE_GITHUB_REMOTE_OBSERVATION_V1"


def observe(root,publication,repository,request=None,git=None):
    root=Path(root)
    result={"schema":SCHEMA,"status":"no_confirmed_publication",
            "formal":False,"independent_first_remote_receipt_verified":False,
            "github_server_observation_not_first_receipt":True,
            "production_forecast_changed":False,
            "records":[],"observed_before_t_minus_12":0,
            "observed_after_t_minus_12":0,"unverified_count":0}
    if publication.get("outcome")!="pushed_to_main":
        return result
    sha=publication.get("commit_sha")
    count=publication.get("added_forecasts")
    if (type(sha) is not str or SHA.fullmatch(sha) is None or
            type(count) is not int or not 1<=count<=500 or
            type(repository) is not str or REPO.fullmatch(repository) is None):
        raise ValueError("invalid_publication_identity")
    result["publication_commit_sha"]=sha
    cmd=git or (lambda *args: subprocess.check_output(
        ["git",*args],cwd=root,timeout=30))
    paths=cmd("diff-tree","--no-commit-id","--name-only",
              "--diff-filter=A","-r",sha,"--","four_mode_forecasts/").decode().splitlines()
    if len(paths)!=count or len(set(paths))!=count or any(not RACE.fullmatch(x) for x in paths):
        raise ValueError("invalid_first_add_roster")
    if request is None:
        token=os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
        if not token:raise ValueError("missing_github_api_token")
        def request(path):
            endpoint="https://api.github.com/repos/"+repository+"/contents/"+path+"?ref="+sha
            req=urllib.request.Request(endpoint,headers={
                "Authorization":"Bearer "+token,
                "Accept":"application/vnd.github+json",
                "X-GitHub-Api-Version":"2022-11-28",
                "Cache-Control":"no-cache",
                "User-Agent":"boat-edge-remote-evidence"})
            with urllib.request.urlopen(req,timeout=25) as response:
                if response.status!=200:raise ValueError("remote_http_not_200")
                if response.headers.get("Age") is not None:
                    raise ValueError("cached_http_response_cannot_attest")
                return response.headers.get("Date"),response.read(120000)
    for path in sorted(paths):
        code=RACE.fullmatch(path).group(1)
        row={"race_code":code,"status":"remote_observation_unverified",
             "first_add_commit":sha,
             "independent_first_remote_receipt_verified":False}
        try:
            local=root/path
            if local.is_symlink() or not local.is_file() or local.stat().st_size>30000:
                raise ValueError("unsafe_local_forecast")
            original=cmd("show",sha+":"+path)
            if local.read_bytes()!=original:
                raise ValueError("first_add_bytes_changed")
            raw=json.loads(original)
            if raw.get("race_code")!=code or raw.get("schema")!="CLEAN_FOUR_MODES_PREDEADLINE_V1":
                raise ValueError("invalid_archive_identity")
            deadline=datetime.fromisoformat(raw["deadline_jst"])
            if deadline.utcoffset()!=timedelta(hours=9) or deadline.strftime("%Y%m%d")!=code[:8]:
                raise ValueError("invalid_race_deadline")
            cutoff=deadline-timedelta(minutes=12)
            date_header,response=request(path)
            if not isinstance(date_header,str):
                raise ValueError("github_server_date_missing")
            observed=parsedate_to_datetime(date_header)
            if observed.tzinfo is None or observed.utcoffset()!=timedelta(0):
                raise ValueError("github_server_date_invalid")
            payload=json.loads(response)
            if (payload.get("path")!=path or payload.get("type")!="file" or
                    payload.get("encoding")!="base64" or
                    not isinstance(payload.get("content"),str)):
                raise ValueError("github_remote_file_metadata_mismatch")
            remote=base64.b64decode(payload["content"],validate=False)
            if len(remote)>30000 or remote!=original:
                raise ValueError("github_remote_original_blob_mismatch")
            if payload.get("sha")!=hashlib.sha1(
                    b"blob "+str(len(original)).encode()+b"\0"+original).hexdigest():
                raise ValueError("github_remote_blob_sha_mismatch")
            row.update({
                "github_api_server_date_utc":observed.isoformat(),
                "deadline_minus_12_jst":cutoff.isoformat(),
                "original_sha256":hashlib.sha256(original).hexdigest(),
                "first_add_blob_matches_remote":True,
                "status":("github_server_observed_before_t_minus_12"
                          if observed<cutoff else "github_server_observed_after_t_minus_12"),
            })
        except (ValueError,TypeError,KeyError,OSError,subprocess.SubprocessError,
                urllib.error.URLError,UnicodeError) as error:
            row["error_type"]=type(error).__name__
        result["records"].append(row)
    states=Counter(row["status"] for row in result["records"])
    result["observed_before_t_minus_12"]=states["github_server_observed_before_t_minus_12"]
    result["observed_after_t_minus_12"]=states["github_server_observed_after_t_minus_12"]
    result["unverified_count"]=states["remote_observation_unverified"]
    if sum(states.values())!=count:raise ValueError("remote_observation_accounting")
    result["status"]="remote_observation_audited_nonformal"
    result["publication_count"]=count
    return result


def main():
    root=Path(".")
    location=Path("four-mode-evidence/publication.json")
    if location.is_symlink() or not location.is_file() or location.stat().st_size>50000:
        publication={"outcome":"no_confirmed_publication"}
    else:
        publication=json.loads(location.read_text(encoding="utf-8"))
    report=observe(root,publication,os.environ.get("GITHUB_REPOSITORY",""))
    path=Path("four-mode-evidence/github-server-observation.json")
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(report,ensure_ascii=False,sort_keys=True,indent=2)+"\n",
                    encoding="utf-8")
    print("FOUR_MODE_GITHUB_SERVER_OBSERVATION="+json.dumps(
        {k:v for k,v in report.items() if k!="records"},sort_keys=True))
    if report.get("unverified_count",0):
        print("::warning::Some frozen forecasts lack a usable GitHub server observation.")


if __name__=="__main__":
    main()

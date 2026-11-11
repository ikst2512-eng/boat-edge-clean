"""Read-only GitHub server witness for #1746 official source-bundle original.

This checks a REAL SOURCE ARCHIVE stored on entry-course-evidence-ledger,
NOT the separate (currently unpublished) signed-F 4-mode candidate. Even a
valid remote first-add in CURRENT Git history plus a pre-T12 server Date
cannot exclude force-pushes, identify HTTP source provenance, or prove the
first remote acceptance timestamp. Never promote a formal T-12 score.

No token, PUT, Cron, local writes, forecast generation, outcome or payout.
Mock tests must never be presented as a live witnessed source.
"""
import base64
import binascii
from datetime import timedelta, timezone
from email.utils import parsedate_to_datetime
import hashlib
import json
import re
import urllib.error
import urllib.parse
import urllib.request

from scenario_future_local_candidate_handoff import _git_blob_sha1
from scenario_signed_st_cross_ledger_audit import (
    audit_source_writer_against_signed_candidate, SOURCE_LEDGER, SOURCE_ROOT,
)

REPO="ikst2512-eng/boat-edge-clean"
API="https://api.github.com/repos/"+REPO
LIMIT=1_900_000
SHA40=re.compile(r"[0-9a-f]{40}\Z")
UTC=timedelta(0)


def _transport(req):
    try:
        with urllib.request.urlopen(req, timeout=12) as resp:
            return resp.status, dict(resp.headers.items()), resp.read(LIMIT+1)
    except urllib.error.HTTPError as exc:
        return exc.code, dict(exc.headers.items()), exc.read(LIMIT+1)


def _unique(pairs):
    obj={}
    for key,value in pairs:
        if key in obj:
            raise ValueError("remote_source_duplicate_json_field")
        obj[key]=value
    return obj


def _get(send,path,expected=200):
    if (not callable(send) or type(path) is not str
            or not path.startswith("/") or "//" in path
            or "\r" in path or "\n" in path
            or expected not in (200,404)):
        raise ValueError("remote_source_invalid_readonly_request")
    req=urllib.request.Request(
        API+path,
        headers={"Accept":"application/vnd.github+json",
                 "X-GitHub-Api-Version":"2022-11-28",
                 "Cache-Control":"no-cache",
                 "User-Agent":"boat-edge-F-source-cross-ledger-audit"},
        method="GET")
    response=send(req)
    if (type(response) is not tuple or len(response)!=3
            or type(response[0]) is not int
            or type(response[1]) is not dict
            or type(response[2]) is not bytes
            or len(response[2])>LIMIT):
        raise ValueError("remote_source_response_invalid")
    status,headers,body=response
    if any(key.lower() in ("age","x-cache") and (
          key.lower()=="age" or "HIT" in str(val).upper())
          for key,val in headers.items()):
        raise ValueError("remote_source_cached_response_forbidden")
    dates=[v for k,v in headers.items() if k.lower()=="date"]
    if len(dates)!=1 or type(dates[0]) is not str:
        raise ValueError("remote_source_server_date_missing")
    try:
        when=parsedate_to_datetime(dates[0])
    except (TypeError,ValueError,IndexError) as exc:
        raise ValueError("remote_source_server_date_invalid") from exc
    if when.tzinfo is None or when.utcoffset()!=UTC:
        raise ValueError("remote_source_server_date_not_utc")
    if status!=expected:
        raise ValueError("remote_source_http_status_"+str(status))
    if expected==404:
        return when,None,headers
    try:
        parsed=json.loads(body.decode("utf-8"),object_pairs_hook=_unique,
                           parse_constant=lambda x: (_ for _ in ()).throw(
                               ValueError("nonfinite_github_json")))
    except (UnicodeError,ValueError) as exc:
        raise ValueError("remote_source_http_json_unreadable") from exc
    return when,parsed,headers


def observe_exact_1746_source_first_add(prepared,source_bundle_raw,
                                        source_writer_receipt,*,send=None):
    """Verify GitHub CURRENT branch/source bytes, unique add, parent absence.

    If send is injected it is an algorithm test only. With real transport,
    server Date is a read-only point-in-time EXISTENCE witness. It is never
    a certified initial remote receipt, not even with source writer receipt.
    """
    contract=audit_source_writer_against_signed_candidate(
        prepared,source_bundle_raw,source_writer_receipt)
    race=contract["race_code"]
    filename=SOURCE_ROOT+race[:8]+"/"+race+".json"
    outcome=[x for x in source_writer_receipt["outcomes"]
             if x.get("race_code")==race][0]
    exact_commit=outcome["git_commit_sha"]
    if (type(exact_commit) is not str or not SHA40.fullmatch(exact_commit)
            or _git_blob_sha1(source_bundle_raw)!=
               contract["source_bundle_git_blob_sha1"]):
        raise ValueError("remote_source_claimed_first_add_sha_invalid")
    network=_transport if send is None else send
    if not callable(network):
        raise ValueError("remote_source_invalid_transport")
    ref_path="/git/ref/heads/"+SOURCE_LEDGER
    ref_time,ref,_=_get(network,ref_path)
    robj=ref.get("object") if type(ref) is dict else None
    head=robj.get("sha") if type(robj) is dict else None
    if (type(ref) is not dict or ref.get("ref")!="refs/heads/"+SOURCE_LEDGER
            or robj.get("type")!="commit"
            or type(head) is not str or SHA40.fullmatch(head) is None):
        raise ValueError("remote_source_branch_head_not_confirmed")
    pinned=urllib.parse.urlencode({"ref":head})
    blob_time,stored,meta=_get(network,"/contents/"+filename+"?"+pinned)
    if (type(stored) is not dict or stored.get("type")!="file"
            or stored.get("path")!=filename
            or stored.get("sha")!=_git_blob_sha1(source_bundle_raw)
            or stored.get("encoding")!="base64"
            or type(stored.get("content")) is not str):
        raise ValueError("remote_source_file_or_blob_mismatch")
    try:
        from_github=base64.b64decode(
            "".join(stored["content"].splitlines()),validate=True)
    except (ValueError,binascii.Error) as exc:
        raise ValueError("remote_source_file_base64_unreadable") from exc
    if from_github!=source_bundle_raw:
        raise ValueError("remote_source_original_bundle_bytes_differ")
    history_time,history,hheaders=_get(
        network,"/commits?"+urllib.parse.urlencode(
            {"sha":head,"path":filename,"per_page":100}))
    if (type(history) is not list or len(history)!=1
            or type(history[0]) is not dict
            or history[0].get("sha")!=exact_commit
            or any(k.lower()=="link" and 'rel="next"' in str(v)
                   for k,v in hheaders.items())):
        raise ValueError("remote_source_history_not_unique_add")
    detail_time,commit,_=_get(network,"/commits/"+exact_commit)
    if (type(commit) is not dict or commit.get("sha")!=exact_commit
            or type(commit.get("parents")) is not list
            or len(commit["parents"])!=1
            or type(commit["parents"][0]) is not dict):
        raise ValueError("remote_source_first_add_commit_not_confirmed")
    parent=commit["parents"][0].get("sha")
    if type(parent) is not str or SHA40.fullmatch(parent) is None:
        raise ValueError("remote_source_first_add_parent_invalid")
    files=commit.get("files")
    matches=[x for x in files if type(x) is dict
             and x.get("filename")==filename] if type(files) is list else []
    if (len(matches)!=1 or matches[0].get("status")!="added"
            or matches[0].get("sha")!=_git_blob_sha1(source_bundle_raw)):
        raise ValueError("remote_source_first_add_status_not_confirmed")
    parent_when,absent,_=_get(
        network,"/contents/"+filename+"?"+urllib.parse.urlencode({"ref":parent}),
        expected=404)
    if absent is not None:
        raise ValueError("remote_source_first_add_parent_not_empty")
    chronology=[ref_time,blob_time,history_time,detail_time,parent_when]
    if any(a>b for a,b in zip(chronology,chronology[1:])):
        raise ValueError("remote_source_github_server_time_regressed")
    candidate=json.loads(prepared["bytes"])
    cutoff=__import__("datetime").datetime.fromisoformat(
        candidate["T_minus_12_cutoff_jst"])
    # Real GitHub Date can witness existence only if GET actually occurred
    # before the cutoff. A later readback still shows current branch ancestry,
    # but can NEVER be marked a pre-cutoff live observation.
    before_cutoff=blob_time<cutoff.astimezone(timezone.utc)
    return {
        "schema":"SIGNED_F_SOURCE_LEDGER_REMOTE_GITHUB_READONLY_OBSERVATION_V1",
        "race_code":race,
        "observed_source_branch":SOURCE_LEDGER,
        "candidate_intended_branch":contract["F_candidate_intended_ledger_branch"],
        "observed_branch_head_sha":head,
        "source_file_path":filename,
        "verified_original_bundle_sha256":hashlib.sha256(source_bundle_raw).hexdigest(),
        "source_file_git_blob_sha1":_git_blob_sha1(source_bundle_raw),
        "current_branch_unique_path_add_verified":True,
        "observed_first_add_commit_sha":exact_commit,
        "first_add_parent_did_not_contain_source_file":True,
        "git_server_date_existing_at_utc":blob_time.isoformat(),
        "source_seen_at_observed_time_before_T12":before_cutoff if send is None else False,
        "mock_server_date_before_cutoff_not_evidence":before_cutoff if send is not None else None,
        "source_writer_receipt_independently_authenticated":False,
        "network_transport_is_direct_GitHub_HTTPS":send is None,
        "source_first_remote_acceptance_verified":False,
        "source_branch_forcepush_history_excluded":False,
        "official_HTTP_source_origin_independently_verified":False,
        "F_candidate_was_written_to_GitHub":False,
        "F_candidate_first_remote_receipt_verified":False,
        "eligible_for_300_plus_300":False,"formal":False,
        "production_changed":False,"accuracy_improvement_proven":False,
        "warning":"Even a real uncached GitHub GET/Date plus unique ADDED on CURRENT branch cannot prove independent initial remote acceptance, prior force-push absence or a stored F candidate.",
    }

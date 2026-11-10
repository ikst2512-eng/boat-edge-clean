"""Optional GitHub Contents API create-only wire for #1710 future research.

Only a caller invoking --publish with a real completed future gateway input
and GH_TOKEN can write. No scheduler, branch creation, official HTTP collector,
outcome reader, model tuning or production selector exists here.

A successful authenticated GitHub write/readback is an existence witness, NOT
independent FIRST remote receipt or first-add ancestry. Never credit 300+300.
"""
import argparse
import base64
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
import hashlib
import json
import os
from pathlib import Path
import re
import urllib.error
import urllib.parse
import urllib.request

from scenario_future_local_candidate_handoff import (
    PATH_PREFIX, RESEARCH_ONLY_LEDGER_BRANCH,
    prepare_local_candidate, publish_local_candidate_write_once,
    _git_blob_sha1,
)

REPO = "ikst2512-eng/boat-edge-clean"
API = "https://api.github.com/repos/" + REPO
MAX_HTTP_BYTES = 150_000
MAX_SOURCE_BYTES = 160_000
SHA40 = re.compile(r"[a-f0-9]{40}\Z")
CODE = re.compile(r"20\d{10}\Z")
JST = timezone(timedelta(hours=9))
LEDGER_BOOTSTRAP_HEAD_SHA = "72e1b3da1b71e75c8b3901d301ed69fca590694d"


def _json_no_duplicate_keys(pairs):
    out = {}
    for k,v in pairs:
        if k in out:
            raise ValueError("github_duplicate_json_key")
        out[k] = v
    return out


def _json(raw):
    if type(raw) is not bytes or len(raw) > MAX_HTTP_BYTES:
        raise ValueError("invalid_github_response_bytes")
    try:
        return json.loads(
            raw.decode("utf-8"), object_pairs_hook=_json_no_duplicate_keys,
            parse_constant=lambda _: (_ for _ in ()).throw(
                ValueError("github_nonfinite_json")))
    except (UnicodeError, ValueError) as exc:
        raise ValueError("unreadable_github_json") from exc


def _remote_path(path):
    if (type(path) is not str
            or not path.startswith(PATH_PREFIX)
            or not CODE.fullmatch(path[len(PATH_PREFIX):-5])
            or not path.endswith(".json")
            or path != PATH_PREFIX + path[len(PATH_PREFIX):-5] + ".json"):
        raise ValueError("unapproved_research_candidate_path")
    return path


def _wire_transport(request):
    """Real bounded GitHub HTTPS I/O; no browser/app or credential logging."""
    try:
        with urllib.request.urlopen(request, timeout=12) as resp:
            data=resp.read(MAX_HTTP_BYTES + 1)
            return resp.status, dict(resp.headers.items()), data
    except urllib.error.HTTPError as exc:
        return exc.code, dict(exc.headers.items()), exc.read(MAX_HTTP_BYTES + 1)


class GitHubOnlyCreateWire:
    """A strict branch/path-scoped adapter supplied to the existing #1710 guard."""
    def __init__(self, token, send=None):
        if (type(token) is not str or not token.strip()
                or any(ch in token for ch in ("\r", "\n", "\x00"))):
            raise ValueError("explicit_token_required_for_research_writer")
        self._token = token.strip()
        self._send = _wire_transport if send is None else send
        self.create_ack_observation = None
        self._last_put_server_date_utc = None
        if not callable(self._send):
            raise ValueError("invalid_github_transport")

    def _request(self, method, path, branch, raw=None):
        _remote_path(path)
        if branch != RESEARCH_ONLY_LEDGER_BRANCH:
            raise ValueError("research_only_ledger_branch_required")
        if method not in ("GET", "PUT"):
            raise ValueError("github_method_not_allowed")
        if method == "PUT":
            # Each create attempt has its own response evidence. Never reuse
            # the previous call's Date/commit if the next HTTP request fails.
            self.create_ack_observation = None
            self._last_put_server_date_utc = None
        url=API+"/contents/"+path
        if method=="GET":
            url+="?"+urllib.parse.urlencode({"ref":branch})
            body=None
        else:
            if type(raw) is not bytes or not 0 < len(raw) <= MAX_SOURCE_BYTES:
                raise ValueError("research_candidate_body_invalid")
            # Existing paths are never supplied a SHA and must be rejected
            # by GitHub Contents as 422/409, NOT silently overwritten.
            body=json.dumps({
                "message":"research(#1710): first create-only pre-T12 candidate "+path.split("/")[-1],
                "branch":branch,
                "content":base64.b64encode(raw).decode("ascii"),
            },ensure_ascii=True,separators=(",",":")).encode("utf-8")
        headers={
            "Authorization":"Bearer "+self._token,
            "Accept":"application/vnd.github+json",
            "X-GitHub-Api-Version":"2022-11-28",
            "Cache-Control":"no-cache",
            "User-Agent":"boat-edge-triple-research-create-only",
        }
        if method=="PUT":
            headers["Content-Type"]="application/json"
        req=urllib.request.Request(url,data=body,headers=headers,method=method)
        output=self._send(req)
        if (type(output) is not tuple or len(output)!=3
                or type(output[0]) is not int
                or type(output[1]) is not dict
                or type(output[2]) is not bytes
                or len(output[2]) > MAX_HTTP_BYTES):
            raise ValueError("github_transport_invalid_return")
        code, hs, payload=output
        # HTTP 404 can be a cached absence. Check cache headers first even
        # when the path is not found, otherwise an old 404 could misdirect a
        # create attempt and conceal a changed concurrent branch.
        if any(k.lower()=="age" for k in hs):
            raise ValueError("github_cached_response_forbidden")
        # GitHub REST 404 may mean a missing file (for an existing branch);
        # 401/403/409/422 are always hard failures, never file-missing.
        if method=="GET" and code==404:
            return None
        if (method=="GET" and code!=200 or
                method=="PUT" and code!=201):
            raise ValueError("github_research_create_or_read_http_"+str(code))
        if method == "PUT":
            # GitHub's HTTP response Date is an upper-bound observation of
            # remote acceptance, NOT an independent first-remote timestamp.
            # Fail closed on missing, ambiguous or cached server clock.
            text = _single_header(hs, "Date")
            try:
                server = parsedate_to_datetime(text)
            except (ValueError, TypeError, IndexError) as exc:
                raise ValueError("github_create_ack_invalid_server_date") from exc
            if server.tzinfo is None or server.utcoffset()!=timedelta(0):
                raise ValueError("github_create_ack_date_must_be_UTC")
            self._last_put_server_date_utc=server.isoformat()
        return _json(payload)

    def read(self, branch, path):
        response=self._request("GET",path,branch)
        if response is None:
            return None
        if (type(response) is not dict
                or response.get("type")!="file"
                or response.get("path")!=path
                or response.get("encoding")!="base64"
                or type(response.get("content")) is not str
                or type(response.get("sha")) is not str
                or not SHA40.fullmatch(response["sha"])):
            raise ValueError("github_contents_identity_invalid")
        try:
            raw=base64.b64decode(
                "".join(response["content"].splitlines()),validate=True)
        except (ValueError,base64.binascii.Error) as exc:
            raise ValueError("github_contents_base64_invalid") from exc
        if (not 0 < len(raw) <= MAX_SOURCE_BYTES
                or _git_blob_sha1(raw)!=response["sha"]):
            raise ValueError("github_contents_git_blob_or_length_mismatch")
        return raw

    def create(self, branch, path, raw):
        if (type(raw) is not bytes or not 0 < len(raw) <= MAX_SOURCE_BYTES):
            raise ValueError("github_candidate_create_bytes_invalid")
        data=self._request("PUT",path,branch,raw)
        expected=_git_blob_sha1(raw)
        content=data.get("content") if type(data) is dict else None
        commit=data.get("commit") if type(data) is dict else None
        if (type(content) is not dict or content.get("path")!=path
                or content.get("sha")!=expected
                or type(commit) is not dict
                or type(commit.get("sha")) is not str
                or not SHA40.fullmatch(commit["sha"])):
            raise ValueError("github_create_ack_not_matching_candidate")
        if self._last_put_server_date_utc is None:
            raise ValueError("github_create_ack_server_date_missing")
        try:
            frozen_payload=_json(raw)
            server_response=datetime.fromisoformat(self._last_put_server_date_utc)
            frozen_at=datetime.fromisoformat(
                frozen_payload["frozen_local_clock_self_report_jst"])
            cutoff=datetime.fromisoformat(
                frozen_payload["T_minus_12_cutoff_jst"])
        except (KeyError, ValueError, TypeError) as exc:
            raise ValueError("github_create_ack_frozen_cutoff_unreadable") from exc
        if (frozen_at.utcoffset()!=timedelta(hours=9)
                or cutoff.utcoffset()!=timedelta(hours=9)
                or server_response.utcoffset()!=timedelta(0)
                or not frozen_at.astimezone(timezone.utc)
                       <=server_response<cutoff.astimezone(timezone.utc)):
            # A local clock and an HTTP 201 alone never make a late write
            # admissible. The HTTP PUT might have already succeeded remotely
            # even when this conservative check fails; never erase it.
            raise ValueError("github_create_response_not_between_freeze_and_T12")
        self.create_ack_observation={
            "schema":"FOUR_MODE_RESEARCH_GITHUB_CREATE_201_RESPONSE_OBSERVATION_V1",
            "repository":REPO,
            "branch":branch,
            "candidate_path":path,
            "candidate_git_blob_sha1":expected,
            "candidate_sha256":hashlib.sha256(raw).hexdigest(),
            "create_response_commit_sha":commit["sha"],
            "github_create_response_date_utc":self._last_put_server_date_utc,
            "create_only_put_received_http_201":True,
            "first_remote_candidate_receipt_verified":False,
            "unique_first_add_git_history_verified":False,
            "official_source_first_remote_receipts_verified":False,
            "complete_attempt_inventory_verified":False,
            "eligible_for_300_plus_300":False,
            "formal":False,
            "promotion_allowed":False,
            "warning":"GitHub Date on the 201 creation response is an observed "
                      "server response time, NOT independent first-remote "
                      "acceptance or first-add ancestry proof.",
        }
        return None


def _read_limited_unlinked(path):
    p=Path(path)
    if p.is_symlink() or not p.is_file() or not 0 < p.stat().st_size <= MAX_SOURCE_BYTES:
        raise ValueError("gateway_file_missing_symlink_or_oversize")
    return _json(p.read_bytes())


def run_from_gateway_file(path, generated_at_jst, frozen_at_jst,
                          publish=False, token=None, send=None,
                          observe_first_add=False):
    """Validated offline, explicit create-only publish, or read-only witness."""
    from scenario_future_local_candidate_handoff import PROTOCOL_PATH
    protocol=_read_limited_unlinked(PROTOCOL_PATH)
    gateway=_read_limited_unlinked(path)
    prepared=prepare_local_candidate(gateway,protocol,generated_at_jst,frozen_at_jst)
    base={
        "schema":"FOUR_MODE_TRIPLE_SOURCE_GITHUB_CREATE_ONLY_CLI_V1",
        "race_code":prepared["race_code"],
        "candidate_path":prepared["path"],
        "candidate_sha256":prepared["sha256"],
        "candidate_git_blob_sha1":prepared["git_blob_sha1"],
        "research_branch":RESEARCH_ONLY_LEDGER_BRANCH,
        "formal":False,"promotion_allowed":False,
        "first_remote_candidate_receipt_verified":False,
        "model_improvement_proven":False,"production_changed":False,
    }
    if type(publish) is not bool or type(observe_first_add) is not bool:
        raise ValueError("only_explicit_boolean_action_modes")
    if publish and observe_first_add:
        raise ValueError("cannot_publish_and_observe_same_invocation")
    if observe_first_add:
        return inspect_candidate_observed_first_add(
            prepared,gateway,protocol,generated_at_jst,frozen_at_jst,
            send=send,
        )
    if publish is False:
        return dict(base,status="validated_local_only_no_github_write",
                    github_create_attempted=False)
    # This gateway JSON alone is a self-reported model output. It does NOT
    # include authenticated official HTTP source originals. Even a synthetic
    # gateway can satisfy the local structural signature checks, so direct
    # publishing here is unsafe. Keep read-only witness/dryrun, and require
    # the archived-three-original CLI (real pinned parsers) for every PUT.
    raise ValueError("gateway_only_publish_forbidden_use_archived_originals_runner")


def main():
    parser=argparse.ArgumentParser(
        description="Research branch-only write-once GitHub adapter; not formal")
    parser.add_argument("--gateway-json",required=True)
    parser.add_argument("--generated-at-jst",required=True)
    parser.add_argument("--frozen-at-jst",required=True)
    operation=parser.add_mutually_exclusive_group()
    operation.add_argument("--publish",action="store_true",
                           help="Opt-in actual create-only research candidate")
    operation.add_argument("--observe-first-add",action="store_true",
                           help="Read-only GitHub Date/commit/parent/ancestry witness")
    args=parser.parse_args()
    output=run_from_gateway_file(
        args.gateway_json,args.generated_at_jst,args.frozen_at_jst,
        publish=args.publish,
        token=os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN"),
        observe_first_add=args.observe_first_add)
    print(json.dumps(output,ensure_ascii=False,sort_keys=True))


if __name__=="__main__":
    main()


def _single_header(headers, name):
    if type(headers) is not dict:
        raise ValueError("github_witness_headers_invalid")
    values=[str(v) for k,v in headers.items() if k.lower()==name.lower()]
    if len(values)!=1:
        raise ValueError("github_witness_missing_or_duplicate_header:"+name)
    return values[0]


def _witness_get(send, path, expected_status=200):
    """One real REST GET (or a mock) with uncached GitHub server Date."""
    if (not callable(send) or type(path) is not str
            or not path.startswith("/")
            or "//" in path
            or "\r" in path or "\n" in path
            or type(expected_status) is not int):
        raise ValueError("invalid_readonly_witness_request")
    request=urllib.request.Request(
        API+path,
        headers={
            "Accept":"application/vnd.github+json",
            "X-GitHub-Api-Version":"2022-11-28",
            "Cache-Control":"no-cache",
            "User-Agent":"boat-edge-triple-research-readonly-witness",
        },
        method="GET",
    )
    result=send(request)
    if (type(result) is not tuple or len(result)!=3
            or type(result[0]) is not int
            or type(result[1]) is not dict
            or type(result[2]) is not bytes
            or len(result[2])>MAX_HTTP_BYTES):
        raise ValueError("invalid_github_witness_transport")
    status,headers,raw=result
    if any(k.lower()=="age" for k in headers):
        raise ValueError("github_witness_cached_response")
    when=_single_header(headers,"Date")
    try:
        server=parsedate_to_datetime(when)
    except (ValueError,TypeError,IndexError) as exc:
        raise ValueError("invalid_github_witness_server_date") from exc
    if server.tzinfo is None or server.utcoffset()!=timedelta(0):
        raise ValueError("github_witness_date_must_be_UTC")
    if status!=expected_status:
        raise ValueError("github_witness_HTTP_"+str(status))
    if expected_status==404:
        return server,None,headers
    return server,_json(raw),headers


def inspect_candidate_observed_first_add(
    prepared, gateway, registered_protocol, generated_at_jst, frozen_at_jst,
    send=None,
):
    """Read-only current-branch first-add and before-cutoff existence witness.

    To observe with *real* TLS responses omit send. Injected send means MOCK
    tests only. GitHub Date proves existence before cutoff when a real GET
    happens; it cannot independently establish the FIRST remote acceptance
    time or rule out earlier force-pushed history, so formal=False always.

    A complete result-last researcher must also attest initial source HTTP
    receipt, authenticated first remote delivery, the full run/dispatch
    inventory and an append-only branch policy separately.
    """
    recalculated=prepare_local_candidate(
        gateway,registered_protocol,generated_at_jst,frozen_at_jst)
    if type(prepared) is not dict or recalculated!=prepared:
        raise ValueError("github_witness_candidate_not_exact_frozen_bytes")
    path=_remote_path(recalculated["path"])
    raw=recalculated["bytes"]
    item=_json(raw)
    if (item.get("schema")!="FOUR_MODE_TRIPLE_SOURCE_LOCAL_FROZEN_CANDIDATE_V1"
            or item.get("first_remote_candidate_receipt_verified") is not False
            or item.get("formal") is not False):
        raise ValueError("github_witness_unexpected_frozen_candidate")
    cutoff=datetime.fromisoformat(item["T_minus_12_cutoff_jst"])
    frozen=datetime.fromisoformat(frozen_at_jst)
    if cutoff.utcoffset()!=timedelta(hours=9) or frozen.utcoffset()!=timedelta(hours=9):
        raise ValueError("github_witness_clock_invalid")
    send_fn=_wire_transport if send is None else send
    if not callable(send_fn):
        raise ValueError("github_witness_send_not_callable")
    ref_path="/git/ref/heads/"+RESEARCH_ONLY_LEDGER_BRANCH
    ref_when,reference,_=_witness_get(send_fn,ref_path)
    ref_obj=reference.get("object") if type(reference) is dict else None
    head=ref_obj.get("sha") if type(ref_obj) is dict else None
    if (reference.get("ref")!="refs/heads/"+RESEARCH_ONLY_LEDGER_BRANCH
            or ref_obj.get("type")!="commit"
            or type(head) is not str or not SHA40.fullmatch(head)):
        raise ValueError("github_witness_untrusted_branch_head")
    content_when,contents,_=_witness_get(
        send_fn,"/contents/"+path+"?"+urllib.parse.urlencode({"ref":head}))
    if (type(contents) is not dict
            or contents.get("path")!=path or contents.get("type")!="file"
            or contents.get("encoding")!="base64"
            or type(contents.get("content")) is not str
            or contents.get("sha")!=recalculated["git_blob_sha1"]):
        raise ValueError("github_witness_wrong_candidate_at_pinned_head")
    try:
        restored=base64.b64decode(
            "".join(contents["content"].splitlines()),validate=True)
    except (ValueError,base64.binascii.Error) as exc:
        raise ValueError("github_witness_invalid_candidate_base64") from exc
    if restored!=raw or hashlib.sha256(restored).hexdigest()!=recalculated["sha256"]:
        raise ValueError("github_witness_remote_candidate_bytes_differ")
    # A verified real 200/GET received prior to cutoff witnesses existence
    # before T-12, but NOT the first remote receipt.
    if (not frozen.astimezone(timezone.utc)<ref_when<=content_when
            or not content_when<cutoff.astimezone(timezone.utc)):
        raise ValueError("github_witness_not_observed_strictly_before_T12")
    history_when,history,history_headers=_witness_get(
        send_fn,"/commits?"+urllib.parse.urlencode({
            "sha":head,"path":path,"per_page":100}))
    if (not isinstance(history,list) or len(history)!=1
            or any(k.lower()=="link" and 'rel="next"' in v
                   for k,v in history_headers.items())):
        raise ValueError("github_witness_incomplete_or_mutated_candidate_history")
    initial=history[0].get("sha") if type(history[0]) is dict else None
    if type(initial) is not str or not SHA40.fullmatch(initial):
        raise ValueError("github_witness_invalid_first_add_commit")
    commit_when,commit,_=_witness_get(send_fn,"/commits/"+initial)
    parents=commit.get("parents") if type(commit) is dict else None
    files=commit.get("files") if type(commit) is dict else None
    if (commit.get("sha")!=initial or type(parents) is not list
            or len(parents)!=1 or type(parents[0]) is not dict
            or type(parents[0].get("sha")) is not str
            or not SHA40.fullmatch(parents[0]["sha"])
            or type(files) is not list or
            not any(type(f) is dict and f.get("filename")==path
                    and f.get("status")=="added"
                    and f.get("sha")==recalculated["git_blob_sha1"]
                    for f in files)):
        raise ValueError("github_witness_first_add_commit_not_authenticated")
    parent=parents[0]["sha"]
    absent_at,absent,_=_witness_get(
        send_fn,"/contents/"+path+"?"+urllib.parse.urlencode({"ref":parent}),
        expected_status=404)
    if absent is not None:
        raise ValueError("github_witness_parent_expected_missing")
    compare_when,comparison,comparison_headers=_witness_get(
        send_fn,"/compare/"+LEDGER_BOOTSTRAP_HEAD_SHA+"..."+head)
    if (type(comparison) is not dict
            or comparison.get("status")!="ahead"
            or comparison.get("behind_by")!=0
            or type(comparison.get("ahead_by")) is not int
            or not 1<=comparison["ahead_by"]<=200
            or comparison.get("total_commits")!=comparison["ahead_by"]
            or type(comparison.get("commits")) is not list
            or len(comparison["commits"])!=comparison["ahead_by"]
            or comparison.get("base_commit",{}).get("sha")!=LEDGER_BOOTSTRAP_HEAD_SHA
            or any(k.lower()=="link" and 'rel="next"' in v
                   for k,v in comparison_headers.items())):
        raise ValueError("github_witness_unproven_linear_current_branch")
    seen={x.get("sha") for x in comparison["commits"] if type(x) is dict}
    if initial not in seen or head not in seen or parent not in seen and parent!=LEDGER_BOOTSTRAP_HEAD_SHA:
        raise ValueError("github_witness_missing_commit_from_ancestry")
    # Inspection timestamps should not move backward between GitHub calls.
    times=(ref_when,content_when,history_when,commit_when,absent_at,compare_when)
    if any(a>b for a,b in zip(times,times[1:])):
        raise ValueError("github_witness_inconsistent_server_date_order")
    return {
        "schema":"FOUR_MODE_TRIPLE_SOURCE_READONLY_FIRST_ADD_OBSERVATION_V1",
        "status":"pinned_branch_unique_add_and_existence_preT12_unattested_first_receipt",
        "repository":REPO,
        "branch":RESEARCH_ONLY_LEDGER_BRANCH,
        "race_code":recalculated["race_code"],
        "candidate_path":path,
        "candidate_sha256":recalculated["sha256"],
        "candidate_git_blob_sha1":recalculated["git_blob_sha1"],
        "observed_branch_head_sha":head,
        "branch_initial_bootstrap_commit_sha":LEDGER_BOOTSTRAP_HEAD_SHA,
        "observed_first_add_commit_sha":initial,
        "observed_first_add_parent_sha":parent,
        "github_server_observed_existing_at_utc":content_when.isoformat(),
        "candidate_existed_before_T12_at_observation":True,
        "unique_candidate_path_add_in_current_history":True,
        "candidate_parent_did_not_contain_path":True,
        "observed_branch_ancestry_from_bootstrap":True,
        "github_network_responses_independently_authenticated":False,
        "first_remote_candidate_receipt_verified":False,
        "remote_branch_force_push_history_excluded":False,
        "upstream_first_source_receipts_authenticated":False,
        "complete_capture_and_rescue_run_inventory_verified":False,
        "eligible_for_300_plus_300":False,
        "formal":False,"model_improvement_proven":False,
        "promotion_allowed":False,"production_changed":False,
        "warning":"GitHub GET/Date shows existence, NOT first remote receipt. "
                  "Current linear branch history does not exclude previous "
                  "forced history rewrites or missed attempts. Mocked fetches "
                  "provide only algorithm tests. Formal scoring prohibited.",
    }

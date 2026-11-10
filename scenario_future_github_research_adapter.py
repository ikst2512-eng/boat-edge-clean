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
        if not callable(self._send):
            raise ValueError("invalid_github_transport")

    def _request(self, method, path, branch, raw=None):
        _remote_path(path)
        if branch != RESEARCH_ONLY_LEDGER_BRANCH:
            raise ValueError("research_only_ledger_branch_required")
        if method not in ("GET", "PUT"):
            raise ValueError("github_method_not_allowed")
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
        # GitHub REST 404 may mean a missing file (for an existing branch);
        # 401/403/409/422 are always hard failures, never file-missing.
        if method=="GET" and code==404:
            return None
        if (method=="GET" and code!=200 or
                method=="PUT" and code!=201):
            raise ValueError("github_research_create_or_read_http_"+str(code))
        if any(k.lower()=="age" for k in hs):
            raise ValueError("github_cached_response_forbidden")
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
        # Return is intentionally ignored by publisher; alone it's NOT
        # independent server first-add clock or branch history proof.
        return None


def _read_limited_unlinked(path):
    p=Path(path)
    if p.is_symlink() or not p.is_file() or not 0 < p.stat().st_size <= MAX_SOURCE_BYTES:
        raise ValueError("gateway_file_missing_symlink_or_oversize")
    return _json(p.read_bytes())


def run_from_gateway_file(path, generated_at_jst, frozen_at_jst,
                          publish=False, token=None, send=None):
    """Actual GitHub path available only when publish=True, token provided."""
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
    if publish is False:
        return dict(base,status="validated_local_only_no_github_write",
                    github_create_attempted=False)
    if publish is not True:
        raise ValueError("publish_must_be_explicit_boolean")
    wire=GitHubOnlyCreateWire(token,send)
    state=publish_local_candidate_write_once(
        prepared,gateway,protocol,generated_at_jst,frozen_at_jst,
        RESEARCH_ONLY_LEDGER_BRANCH,wire.read,wire.create,
        lambda:datetime.now(JST))
    return dict(base,status=state["status"],
                github_create_attempted=True,
                local_pre_T12_readback_observed=state["local_pre_T12_readback_observed"])


def main():
    parser=argparse.ArgumentParser(
        description="Research branch-only write-once GitHub adapter; not formal")
    parser.add_argument("--gateway-json",required=True)
    parser.add_argument("--generated-at-jst",required=True)
    parser.add_argument("--frozen-at-jst",required=True)
    parser.add_argument("--publish",action="store_true",
                        help="Opt-in real GitHub research-only create/readback")
    args=parser.parse_args()
    output=run_from_gateway_file(
        args.gateway_json,args.generated_at_jst,args.frozen_at_jst,
        publish=args.publish,
        token=os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN"))
    print(json.dumps(output,ensure_ascii=False,sort_keys=True))


if __name__=="__main__":
    main()

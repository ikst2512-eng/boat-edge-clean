"""GitHub server-Date observation of a previously committed Draft study protocol.

This attests that exact protocol bytes were retrievable on GitHub before
the predeclared *research registration* cutoff. NOT independent first remote
receipt for any four-mode forecast, not official accuracy or model promotion.
"""
import base64
import hashlib
import json
import os
import re
import urllib.request
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime
from pathlib import Path

from forward_hole_rank3_protocol import PROTOCOL, validate, _git_blob_sha1

HEAD = re.compile(r"[0-9a-f]{40}\Z")
REPO = re.compile(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+\Z")
CUTOFF = datetime.fromisoformat("2026-11-05T07:00:00+09:00")
REMOTE_PATH = "research/forward_hole_rank3_protocol_20261105.json"


def verify_remote_protocol(repo, head_sha, *, protocol=PROTOCOL, request=None):
    if (type(repo) is not str or REPO.fullmatch(repo) is None
            or type(head_sha) is not str or HEAD.fullmatch(head_sha) is None):
        raise ValueError("invalid_repository_or_commit")
    local = validate(path=protocol)
    p = Path(protocol)
    original = p.read_bytes()
    if request is None:
        token = os.environ.get("GITHUB_TOKEN")
        if not token:
            raise ValueError("missing_github_token")
        url = ("https://api.github.com/repos/" + repo
               + "/contents/" + REMOTE_PATH + "?ref=" + head_sha)
        def request_once():
            req = urllib.request.Request(url, headers={
                "Authorization": "Bearer " + token,
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
                "Cache-Control": "no-cache",
                "User-Agent": "boat-edge-frozen-protocol-observer",
            })
            with urllib.request.urlopen(req, timeout=25) as response:
                if response.status != 200:
                    raise ValueError("github_api_http_non_200")
                return {
                    "server_date": response.headers.get("Date"),
                    "cache_age": response.headers.get("Age"),
                    "body": response.read(45000),
                }
        request = request_once
    response = request()
    if type(response) is not dict or response.get("cache_age") is not None:
        raise ValueError("untrusted_or_cached_github_response")
    date_header = response.get("server_date")
    if type(date_header) is not str:
        raise ValueError("missing_github_server_date")
    try:
        server_date = parsedate_to_datetime(date_header)
    except (ValueError, TypeError) as exc:
        raise ValueError("invalid_github_server_date") from exc
    if (server_date.tzinfo is None
            or server_date.utcoffset() != timedelta(0)):
        raise ValueError("non_utc_github_server_date")
    if not server_date < CUTOFF:
        raise ValueError("protocol_remote_observation_after_cutoff")
    body = response.get("body")
    if type(body) is not bytes or len(body) > 40000:
        raise ValueError("invalid_remote_response")
    try:
        data = json.loads(body)
        if (type(data) is not dict or data.get("path") != REMOTE_PATH
                or data.get("type") != "file"
                or data.get("encoding") != "base64"
                or type(data.get("content")) is not str
                or data.get("sha") != _git_blob_sha1(original)):
            raise ValueError("invalid_protocol_api_metadata")
        remote = base64.b64decode(data["content"], validate=False)
    except (ValueError, TypeError, KeyError, UnicodeError) as exc:
        raise ValueError("remote_protocol_json_or_base64_invalid") from exc
    if remote != original or hashlib.sha256(remote).hexdigest() != local["protocol_sha256"]:
        raise ValueError("remote_protocol_bytes_mismatch")
    return {
        "schema": "FOUR_MODE_RESEARCH_PROTOCOL_GITHUB_SERVER_OBSERVATION_V1",
        "status": "research_protocol_on_github_before_study_cutoff",
        "protocol_commit_sha": head_sha,
        "protocol_file": REMOTE_PATH,
        "protocol_sha256": local["protocol_sha256"],
        "github_server_date_utc": server_date.isoformat(),
        "predeclared_observation_deadline_jst": CUTOFF.isoformat(),
        "server_response_not_first_receipt_proof": True,
        "observed_protocol_only_not_forecasts": True,
        "remote_forecasts_verified": False,
        "eligible_races_proven": False,
        "formal": False,
        "production_promotion_allowed": False,
        "warning": ("A GitHub API server Date shows the protocol bytes were "
                    "retrievable by this timestamp; no first remote arrival "
                    "or predeadline race-forecast content is attested.")
    }


def main():
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    sha = os.environ.get("GITHUB_PR_HEAD_SHA", "")
    report = verify_remote_protocol(repo, sha)
    output = Path("forward_protocol_github_observation.json")
    output.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print("FORWARD_PROTOCOL_REMOTE_OBSERVATION=" + json.dumps({
        key: report[key] for key in (
            "status", "protocol_commit_sha", "protocol_sha256",
            "github_server_date_utc", "predeclared_observation_deadline_jst",
            "formal", "remote_forecasts_verified")
    }, sort_keys=True))


if __name__ == "__main__":
    main()

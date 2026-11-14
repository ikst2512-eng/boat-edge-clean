"""Read back exact first-add V133 research bytes from GitHub, with server Date.

A GitHub API Date header is only the earliest *observed availability in this
run*, NOT an attestation of when GitHub originally first received the file.
Never promotes a record to formal T-12, calibrated or betting-approved status.
This script does not POST, modify original forecasts, or download results.
"""
import base64
import hashlib
import json
import os
import re
import subprocess
import urllib.error
import urllib.request
from datetime import timedelta
from email.utils import parsedate_to_datetime
from pathlib import Path

from capture_v133_policy import JST, verify_snapshot

REPO = re.compile(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+\Z")
COMMIT = re.compile(r"[0-9a-f]{40}\Z")
FIRST = re.compile(r"v133_policy_forecasts/(20[0-9]{10})\.json\Z")
SCHEMA = "V133_POLICY_GITHUB_API_READBACK_V1"


def observe(root, commit, repository, request=None, git=None):
    root = Path(root)
    if (not isinstance(commit, str) or not COMMIT.fullmatch(commit)
            or not isinstance(repository, str) or not REPO.fullmatch(repository)):
        raise ValueError("bad_first_add_reference")

    def local_git(*args):
        return subprocess.check_output(["git", *args], cwd=root, timeout=30)

    git = git or local_git
    names = git("diff-tree", "--no-commit-id", "--name-only",
                "--diff-filter=A", "-r", commit, "--", "v133_policy_forecasts/").decode().splitlines()
    if len(names) != len(set(names)) or len(names) > 24 or any(
            not FIRST.fullmatch(path) for path in names):
        raise ValueError("invalid_v133_first_add_roster")

    if request is None and names:
        token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
        if not token:
            raise ValueError("missing_github_token")

        def request(path):
            url = ("https://api.github.com/repos/" + repository + "/contents/"
                   + path + "?ref=" + commit)
            req = urllib.request.Request(url, headers={
                "Authorization": "Bearer " + token,
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
                "Cache-Control": "no-cache",
                "User-Agent": "boat-edge-v133-research-readback",
            })
            with urllib.request.urlopen(req, timeout=25) as response:
                if response.status != 200:
                    raise ValueError("github_remote_http_not_200")
                if response.headers.get("Age") is not None:
                    raise ValueError("cached_remote_response")
                return response.headers.get("Date"), response.read(120000)

    report = {
        "schema": SCHEMA,
        "status": "no_new_v133_forecasts" if not names else "remote_readback_inspected_nonformal",
        "commit_sha": commit,
        "formal": False,
        "calibrated": False,
        "production_buy_approved": False,
        "independent_first_remote_receipt_verified": False,
        "github_date_is_observation_not_first_receipt": True,
        "first_added_count": len(names),
        "early_tminus12_observed": 0,
        "after_tminus12_but_predeadline_observed": 0,
        "late_or_unverified": 0,
        "records": [],
    }

    for path in sorted(names):
        record = {"race_code": FIRST.fullmatch(path).group(1),
                  "file": path, "status": "remote_readback_unverified",
                  "independent_first_remote_receipt_verified": False}
        try:
            file = root / path
            if file.is_symlink() or not file.is_file() or file.stat().st_size > 55000:
                raise ValueError("missing_or_unsafe_v133_file")
            first_bytes = git("show", commit + ":" + path)
            if first_bytes != file.read_bytes():
                raise ValueError("v133_file_changed_since_first_add")
            body = json.loads(first_bytes)
            if body.get("race_code") != record["race_code"]:
                raise ValueError("first_add_race_mismatch")
            date_text, response = request(path)
            if not isinstance(date_text, str):
                raise ValueError("missing_github_server_date")
            stamp = parsedate_to_datetime(date_text)
            if stamp.tzinfo is None or stamp.utcoffset() != timedelta(0):
                raise ValueError("bad_github_server_clock")
            remote = json.loads(response)
            if (remote.get("path") != path or remote.get("type") != "file"
                    or remote.get("encoding") != "base64"
                    or not isinstance(remote.get("content"), str)):
                raise ValueError("remote_metadata_mismatch")
            remote_bytes = base64.b64decode(remote["content"])
            if remote_bytes != first_bytes:
                raise ValueError("remote_bytes_differ_from_first_add")
            git_blob = hashlib.sha1(
                b"blob " + str(len(first_bytes)).encode() + b"\0" + first_bytes
            ).hexdigest()
            if remote.get("sha") != git_blob:
                raise ValueError("github_blob_sha_mismatch")
            observed_jst = stamp.astimezone(JST)
            # Require source receipts, point counts and a strict predeadline
            # observation window. A late GET can never certify earlier receipt.
            verify_snapshot(file, now=observed_jst)
            deadline = __import__("datetime").datetime.fromisoformat(body["deadline_jst"])
            tminus12 = deadline - timedelta(minutes=12)
            record.update({
                "status": ("github_observed_before_tminus12" if observed_jst < tminus12
                           else "github_observed_predeadline_not_tminus12"),
                "observed_at_github_utc": stamp.isoformat(),
                "source_deadline_jst": deadline.isoformat(),
                "source_generated_at_jst": body["generated_at_jst"],
                "first_add_sha256": hashlib.sha256(first_bytes).hexdigest(),
                "remote_exact_blob_match": True,
            })
        except (OSError, ValueError, TypeError, KeyError, UnicodeError,
                subprocess.SubprocessError, urllib.error.URLError) as exc:
            record["reason"] = str(exc)[:120] or type(exc).__name__
        report["records"].append(record)

    report["early_tminus12_observed"] = sum(
        r["status"] == "github_observed_before_tminus12" for r in report["records"])
    report["after_tminus12_but_predeadline_observed"] = sum(
        r["status"] == "github_observed_predeadline_not_tminus12" for r in report["records"])
    report["late_or_unverified"] = sum(
        r["status"] == "remote_readback_unverified" for r in report["records"])
    if sum((report["early_tminus12_observed"],
            report["after_tminus12_but_predeadline_observed"],
            report["late_or_unverified"])) != len(names):
        raise ValueError("remote_observation_count_inconsistent")
    return report


def main():
    root = Path(".")
    commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], text=True, timeout=10).strip()
    report = observe(root, commit, os.getenv("GITHUB_REPOSITORY", ""))
    out = Path("v133-evidence/remote-readback.json")
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)
                   + "\n", encoding="utf-8")
    summary = {k: v for k, v in report.items() if k != "records"}
    print("V133_REMOTE_READBACK=" + json.dumps(summary, sort_keys=True), flush=True)
    for row in report["records"]:
        print("V133_FIRST_ADD_OBSERVED=" + json.dumps(row, sort_keys=True), flush=True)
    if report["late_or_unverified"]:
        raise ValueError("v133_remote_observation_missing_or_late")


if __name__ == "__main__":
    main()

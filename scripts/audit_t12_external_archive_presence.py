"""Read-only inventory of persisted official three-original observations by JST day.

A missing day directory is not a fetched source, nor proof of missing Actions
artifacts. A present directory is only a research candidate; it is NOT proof
of six-racer exhibition, 120 odds, model linkage, or first remote acceptance.
HTTP 403/500 and unexpected 404 are errors, never successful observations.
"""
import argparse
import json
import os
import re
from datetime import datetime
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

BRANCH = "research-t12-external-evidence"
ROOT = "external_three_t12"
REPO = re.compile(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+\Z")
DAY = re.compile(r"20[0-9]{6}\Z")
RACE = re.compile(r"20[0-9]{10}\Z")
SHA40 = re.compile(r"[a-f0-9]{40}\Z")


def _list_directory(data, *, prefix):
    if not isinstance(data, list) or len(data) >= 1000:
        raise ValueError("invalid or incomplete GitHub directory listing")
    names = []
    for entry in data:
        if (not isinstance(entry, dict) or entry.get("type") != "dir"
                or not isinstance(entry.get("name"), str)
                or entry.get("path") != prefix + "/" + entry["name"]):
            raise ValueError("unexpected GitHub directory member")
        names.append(entry["name"])
    if len(names) != len(set(names)):
        raise ValueError("duplicate GitHub directory member")
    return names


def inventory(repo, day, token=None, *, fetch=None):
    if not isinstance(repo, str) or not REPO.fullmatch(repo):
        raise ValueError("invalid repository")
    if not isinstance(day, str) or not DAY.fullmatch(day):
        raise ValueError("invalid JST day")
    try:
        if datetime.strptime(day, "%Y%m%d").strftime("%Y%m%d") != day:
            raise ValueError("invalid JST day")
    except ValueError as exc:
        raise ValueError("invalid JST day") from exc
    if fetch is None and (not isinstance(token, str) or not token):
        raise ValueError("GitHub token required")
    base = "https://api.github.com/repos/" + repo + "/"

    def get(endpoint):
        url = base + endpoint
        if fetch is not None:
            return fetch(url)
        headers = {
            "Authorization": "Bearer " + token,
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "Cache-Control": "no-cache",
            "User-Agent": "BOAT-EDGE-T12-PRESENCE-AUDIT",
        }
        with urlopen(Request(url, headers=headers), timeout=20) as response:
            if response.status != 200:
                raise ValueError("unexpected GitHub HTTP status")
            return json.load(response)

    ref = get("branches/" + BRANCH)
    sha = (ref.get("commit") or {}).get("sha") if isinstance(ref, dict) else None
    if not isinstance(sha, str) or not SHA40.fullmatch(sha):
        raise ValueError("evidence branch identity not verified")
    # Pin both listings to the SAME immutable branch commit, avoiding branch
    # movement between parent and date checks.
    arg = "?" + urlencode({"ref": sha})
    parent = get("contents/" + ROOT + arg)
    days = _list_directory(parent, prefix=ROOT)
    if any(DAY.fullmatch(name) is None for name in days):
        raise ValueError("unexpected non-day evidence directory")
    found = day in days
    races = []
    if found:
        observed = get("contents/" + ROOT + "/" + day + arg)
        races = _list_directory(observed, prefix=ROOT + "/" + day)
        if any(RACE.fullmatch(name) is None or not name.startswith(day)
               for name in races):
            raise ValueError("invalid saved race identity")
    return {
        "schema": "T12_EXTERNAL_ARCHIVE_DAY_PRESENCE_AUDIT_V1",
        "repo": repo,
        "day_jst": day,
        "evidence_branch": BRANCH,
        "evidence_branch_commit_sha": sha,
        "existing_day_directories": sorted(days),
        "day_directory_present": found,
        "race_directories": sorted(races),
        "race_directory_count": len(races),
        "status": ("persisted_race_directories_unverified"
                   if found else "no_persisted_three_original_day_directory"),
        "originals_replayed": False,
        "github_initial_remote_receipt_verified": False,
        "full_t12_source_certified": False,
        "formal": False,
        "t12_eligible": False,
        "accuracy_scoring_allowed": False,
        "note": ("Read-only GitHub branch directory inventory, not an exhaustive "
                 "inventory of Actions artifacts or temporary sources; "
                 "saved directories never count as certified T12 races."),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True)
    parser.add_argument("--day-jst", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    result = inventory(args.repo, args.day_jst, os.environ.get("GITHUB_TOKEN"))
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                   encoding="utf-8")
    print("T12_EXTERNAL_ARCHIVE_DAY_PRESENCE=" + json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()

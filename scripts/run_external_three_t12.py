"""External read-only T12 capture; atomically archive originals on a non-main Git branch.

For an independently scheduled runner (e.g. a configured Render Cron Job).
No forecast decisions, predictions, final-entry certification or production writes.
"""
import argparse
import base64
import hashlib
import json
import os
import re
import secrets
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from scripts.observe_three_official_t12_originals import observe

ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}\Z")
RACE = re.compile(r"20[0-9]{10}\Z")
REPO = re.compile(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+\Z")
BRANCH = re.compile(r"[A-Za-z0-9_.-][A-Za-z0-9_./-]{0,120}\Z")
SOURCE_NAMES = {
    "card": ("racelist.html", "manifest.json"),
    "before": ("beforeinfo.json", "manifest.json"),
    "odds": ("original.html", "manifest.json"),
}


def collected_files(root, race, obs_id, report):
    """Build immutable originals and declared report as one atomic commit payload."""
    if not RACE.fullmatch(race) or not ID.fullmatch(obs_id):
        raise ValueError("invalid research identity")
    if (report.get("race_code") != race or report.get("forecast_usable") is not False
            or report.get("full_t12_source_certified") is not False):
        raise ValueError("not a fail-closed original observation")
    prefix = f"external_three_t12/{race[:8]}/{race}/{obs_id}"
    files = {f"{prefix}/reports/three_originals.json":
             json.dumps(report, ensure_ascii=False, indent=2).encode("utf-8")}
    # If the observation stops before all three originals are available,
    # archive only its diagnostic report. Never publish partial evidence as
    # if it were a complete source set.
    successful_fetch = report.get("status") in (
        "research_components_complete_by_t12", "research_components_incomplete")
    if not successful_fetch:
        return files
    for part, names in SOURCE_NAMES.items():
        folder = Path(root) / "observations" / f"{part}{obs_id}" / race[:8] / race
        for name in names:
            local = folder / name
            if local.is_file():
                files[f"{prefix}/{part}/{name}"] = local.read_bytes()
    if report.get("status") in (
            "research_components_complete_by_t12", "research_components_incomplete"):
        if len(files) != 7:
            raise ValueError("complete fetch status requires all three original pairs")
        for part, names in SOURCE_NAMES.items():
            pair = {name: files[f"{prefix}/{part}/{name}"] for name in names}
            original, manifest_bytes = pair[names[0]], pair[names[1]]
            manifest = json.loads(manifest_bytes)
            if (manifest.get("race_code") != race
                    or manifest.get("sha256") != hashlib.sha256(original).hexdigest()
                    or manifest.get("bytes") != len(original)):
                raise ValueError("original bytes and manifest disagree")

    if sum(len(raw) for raw in files.values()) > 9_000_000:
        raise ValueError("excessive original evidence size")
    return files


def github_api(repo, token, method, endpoint, data=None):
    if not REPO.fullmatch(repo) or not token:
        raise ValueError("missing repository or token")
    uri = "https://api.github.com/repos/" + repo + "/" + endpoint
    body = json.dumps(data, separators=(",", ":")).encode() if data is not None else None
    request = Request(uri, data=body, method=method, headers={
        "Authorization": "Bearer " + token,
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "Content-Type": "application/json"})
    with urlopen(request, timeout=25) as response:
        return json.load(response)


def publish_originals(repo, branch, token, files, *, api=github_api):
    """Single non-force Git commit, optimistic ref update. No main branch writes."""
    # Writing to any arbitrary non-main branch is not safe: the evidence
    # runner must have exactly one preapproved destination.
    if branch != "research-t12-external-evidence":
        raise ValueError("invalid dedicated evidence branch")
    if not files or len(files) > 8:
        raise ValueError("invalid evidence count")
    # Blob objects are immutable; create them only once. A concurrent
    # observation may update the dedicated evidence branch after we read its
    # head, in which case rebuild the tree atop the *new* head and retry a
    # non-force ref update. Never overwrite or force-update another receipt.
    tree = []
    for path, data in sorted(files.items()):
        if (not isinstance(data, bytes) or len(data) > 2_000_000 or
                not path.startswith("external_three_t12/") or
                ".." in Path(path).parts):
            raise ValueError("invalid original evidence file")
        response = api(repo, token, "POST", "git/blobs", {
            "content": base64.b64encode(data).decode("ascii"),
            "encoding": "base64"})
        expected = hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()
        if response.get("sha") != expected:
            raise ValueError("Git blob hash differs from source evidence")
        tree.append({"path": path, "mode": "100644", "type": "blob",
                     "sha": response["sha"]})
    endpoint = "git/refs/heads/" + quote(branch, safe="/")
    for attempt in range(3):
        ref = api(repo, token, "GET", "git/ref/heads/" + quote(branch, safe="/"))
        base_sha = ref["object"]["sha"]
        base = api(repo, token, "GET", "git/commits/" + base_sha)
        new_tree = api(repo, token, "POST", "git/trees", {
            "base_tree": base["tree"]["sha"], "tree": tree})
        commit = api(repo, token, "POST", "git/commits", {
            "message": "research: archive external official T12 original receipts (no forecast)",
            "tree": new_tree["sha"], "parents": [base_sha]})
        try:
            api(repo, token, "PATCH", endpoint, {
                "sha": commit["sha"], "force": False})
            # An immutable Git SHA can be fetched even if no longer reachable
            # from the dedicated evidence branch. Check that the branch
            # points at this commit or at a descendant of it.
            actual = api(repo, token, "GET", "git/ref/heads/" +
                         quote(branch, safe="/"))["object"]["sha"]
            if actual != commit["sha"]:
                compare = api(repo, token, "GET",
                              "compare/" + commit["sha"] + "..." + actual)
                if (compare.get("status") != "ahead"
                        or compare.get("merge_base_commit", {}).get("sha") != commit["sha"]):
                    raise ValueError("archived evidence commit not reachable from branch")
            return commit["sha"]
        except HTTPError as exc:
            # Only a rejected optimistic ref update is retryable. A 401,
            # 403, 404 or any blob/tree/commit error must fail immediately.
            if exc.code not in (409, 422) or attempt == 2:
                raise
    raise AssertionError("unreachable retry state")

def run(race, root, obs_id, repo, branch, token, *, observer=observe,
        publisher=publish_originals, verifier=None):
    report = observer(race, root, obs_id)
    files = collected_files(root, race, obs_id, report)
    sha = publisher(repo, branch, token, files)
    if verifier is None:
        # Local import prevents dependency cycle with read-only re-auditor.
        from scripts.reaudit_external_three_t12 import reaudit_published
        verifier = reaudit_published
    verified = verifier(repo, token, sha, race, obs_id)
    if verified.get("status") not in (
            "independent_originals_reaudited", "observation_not_ready"):
        raise ValueError("remote evidence reinspection did not succeed")
    completed_locally = report["status"] in (
        "research_components_complete_by_t12", "research_components_incomplete")
    expected_remote_status = (
        "independent_originals_reaudited" if completed_locally
        else "observation_not_ready")
    local_complete = (report.get("audit") or {}).get(
        "all_research_components_observed_by_t12") is True
    if report["status"] == "research_components_complete_by_t12" and not local_complete:
        raise ValueError("local research completion claim lacks source audit proof")
    if report["status"] != "research_components_complete_by_t12" and local_complete:
        raise ValueError("local incomplete report contradicts source audit proof")
    if (verified.get("status") != expected_remote_status
            or verified.get("declared_status") != report["status"]
            or verified.get("research_complete") is not local_complete
            or verified.get("original_files_found") != len(files) - 1
            or verified.get("full_t12_source_certified") is not False
            or verified.get("forecast_usable") is not False):
        raise ValueError("remote evidence status does not agree with local report")
    return {"race_code": race, "status": report["status"],
            "archived_original_count": len(files) - 1,
            "evidence_commit": sha,
            "remote_originals_reaudited": verified["status"] == "independent_originals_reaudited",
            "research_complete": verified["research_complete"],
            "full_t12_source_certified": False, "forecast_usable": False}


def archival_exit_code(result):
    """Only seven reread, independently audited files qualify as runner success.

    Exhibition completeness is separate: research_components_incomplete with
    all seven files verified can still be a valid *research evidence* run.
    """
    if (not isinstance(result, dict)
            or result.get("remote_originals_reaudited") is not True
            or result.get("archived_original_count") != 6
            or result.get("full_t12_source_certified") is not False
            or result.get("forecast_usable") is not False):
        return 1
    return 0


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--race-code", required=True)
    p.add_argument("--repo", required=True)
    p.add_argument("--branch", default="research-t12-external-evidence")
    p.add_argument("--root", default="evidence")
    args = p.parse_args()
    if not RACE.fullmatch(args.race_code):
        p.error("invalid race code")
    token = os.getenv("GITHUB_EVIDENCE_TOKEN")
    if not token:
        p.error("GITHUB_EVIDENCE_TOKEN required for durable original evidence")
    obs_id = datetime.now(timezone.utc).strftime("ext%Y%m%dT%H%M%S") + secrets.token_hex(4)
    result = run(args.race_code, args.root, obs_id, args.repo,
                 args.branch, token)
    print(json.dumps(result, ensure_ascii=False))
    raise SystemExit(archival_exit_code(result))


if __name__ == "__main__":
    main()

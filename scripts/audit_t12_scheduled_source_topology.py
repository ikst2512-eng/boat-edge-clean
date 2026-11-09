"""Read-only pinned-main topology audit for the observed official T−12 path.

It reports the precise wiring gap in three selected GitHub Actions workflows
and the directly invoked official two-original capture module. This bounded
static audit does not claim that no other workflow exists in the repository,
or that a schedule actually fired, or that a forecast consumed raw sources.
"""
import argparse
import ast
import base64
import binascii
import hashlib
import json
import os
import re
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen

SHA = re.compile(r"[a-f0-9]{40}\Z")
REPO = re.compile(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+\Z")
PINNED_MAIN = "4bd080ad77778053575cf497c8a6b85b959ce173"
SCHEMA = "T12_PINNED_MAIN_SCHEDULED_SOURCE_TOPOLOGY_V1"
PATHS = (
    ".github/workflows/research-live-preview-evidence.yml",
    ".github/workflows/official-three-original-t12-observation.yml",
    ".github/workflows/official-racelist-live-dispatch.yml",
    "scripts/capture_joint_preview_batch.py",
    "scripts/observe_three_official_t12_originals.py",
)


def _events(source):
    lines = source.splitlines()
    if lines.count("on:") != 1:
        raise ValueError("workflow event declaration not uniquely identifiable")
    index = lines.index("on:") + 1
    events = set()
    while index < len(lines):
        line = lines[index]
        if line and not line[0].isspace() and not line.startswith("#"):
            break
        if not line.strip().startswith("#"):
            found = re.fullmatch(r"  ([a-z_]+):(?:[ ]*.*)?", line)
            if found:
                if found[1] in events:
                    raise ValueError("duplicate workflow event type")
                events.add(found[1])
        index += 1
    if not events:
        raise ValueError("missing workflow event types")
    return events


def inspect(files, commit=PINNED_MAIN):
    if not isinstance(commit, str) or not SHA.fullmatch(commit):
        raise ValueError("invalid pinned original commit")
    if not isinstance(files, dict) or set(files) != set(PATHS):
        raise ValueError("missing or extra pinned GitHub source paths")
    if any(not isinstance(value, str) or not value.strip() for value in files.values()):
        raise ValueError("empty original workflow/module source")
    pair, three, card, pair_module, three_module = (files[path] for path in PATHS)
    pair_events, three_events, card_events = map(_events, (pair, three, card))
    if (pair_events != {"pull_request", "schedule", "workflow_dispatch"}
            or three_events != {"pull_request", "workflow_dispatch"}
            or card_events != {"push", "workflow_dispatch"}):
        raise ValueError("pinned workflow event topology differs from observation")
    if not re.search(r"^\s+- cron: ['\"]\*/5 0-12 \* \* \*['\"]\s*$", pair, re.M):
        raise ValueError("bounded official pair schedule cron changed")
    if pair.count("run: python -m scripts.capture_joint_preview_batch") != 1:
        raise ValueError("scheduled pair collector was not wired exactly once")
    if ("scripts.observe_three_official_t12_originals" in pair or
            "scripts.capture_official_racelist_receipt" in pair):
        raise ValueError("scheduled collection gained a third-original invocation")
    if not re.search(
        r"^\s+if: github\.event_name == 'workflow_dispatch'\s*$", three, re.M
    ):
        raise ValueError("three-original observation no longer dispatch-gated")
    if "python -m scripts.observe_three_official_t12_originals" not in three:
        raise ValueError("three-original manual invocation missing")
    if "from scripts.capture_official_racelist_receipt import capture" not in card:
        raise ValueError("racelist-only workflow source changed")
    try:
        source_ast = ast.parse(pair_module)
        triad_ast = ast.parse(three_module)
    except SyntaxError as exc:
        raise ValueError("invalid pinned Python collector source") from exc
    imports = {
        node.module
        for node in ast.walk(source_ast)
        if isinstance(node, ast.ImportFrom) and node.module
    }
    needed = {
        "scripts.capture_official_beforeinfo_json",
        "scripts.capture_official_odds_receipt",
    }
    if (not needed.issubset(imports)
            or "scripts.capture_official_racelist_receipt" in imports
            or "scripts.observe_three_official_t12_originals" in imports
            or "capture_official_racelist_receipt" in pair_module):
        raise ValueError("two-original collector dependency map changed")
    triple_imports = {
        node.module
        for node in ast.walk(triad_ast)
        if isinstance(node, ast.ImportFrom) and node.module
    }
    if not (needed | {"scripts.capture_official_racelist_receipt"}).issubset(
        triple_imports
    ):
        raise ValueError("manual three-original script no longer captures triad")
    return {
        "schema": SCHEMA,
        "pinned_main_commit": commit,
        "verified_pinned_file_paths": list(PATHS),
        "direct_source_imports_official_pair": sorted(imports & needed),
        "official_pair_schedule_cron_utc": "*/5 0-12 * * *",
        "official_pair_has_scheduled_activation_config": True,
        "scheduled_official_pair_directly_captures_racelist": False,
        "scheduled_official_pair_directly_captures_beforeinfo": True,
        "scheduled_official_pair_directly_captures_odds": True,
        "dedicated_triple_observation_has_schedule": False,
        "dedicated_triple_observation_dispatch_only_job": True,
        "racelist_only_workflow_has_schedule": False,
        "racelist_only_workflow_also_has_path_scoped_push": True,
        "three_original_manual_capture_code_exists": True,
        "scheduled_two_original_path_proves_complete_same_race_triad": False,
        "workflow_run_event_observed_by_this_static_audit": False,
        "other_repository_workflows_exhaustively_audited": False,
        "actual_forecast_official_original_consumption_proven": False,
        "first_forecast_remote_git_acceptance_proven": False,
        "owner_to_fix": "source_collector_owner_1",
        "owner_required_change": (
            "Add and independently verify same-race official racelist, "
            "exhibition-complete beforeinfo, odds and downstream fresh forecast "
            "to a prospective reliable source-collection path; keep owner scopes."
        ),
        "new_formal_certifications": 0,
        "formal_accuracy_denominator": None,
        "formal": False,
        "t12_eligible": False,
        "accuracy_scoring_allowed": False,
    }


def _remote_original(repo, token, ref, path):
    url = (
        f"https://api.github.com/repos/{repo}/contents/{path}?ref={quote(ref)}"
    )
    request = Request(url, headers={
        "Authorization": "Bearer " + token,
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "Cache-Control": "no-cache",
        "User-Agent": "BOAT-EDGE-READ-ONLY-T12-TOPOLOGY-AUDIT",
    })
    with urlopen(request, timeout=25) as response:
        if response.status != 200:
            raise ValueError("pinned source GitHub API unavailable")
        payload = json.load(response)
    if (not isinstance(payload, dict) or payload.get("path") != path
            or payload.get("type") != "file"
            or payload.get("encoding") != "base64"
            or not isinstance(payload.get("content"), str)
            or not isinstance(payload.get("sha"), str)
            or not SHA.fullmatch(payload["sha"])):
        raise ValueError("remote original metadata identity invalid")
    try:
        original = base64.b64decode(
            re.sub(r"\s", "", payload["content"]), validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError("invalid original GitHub base64") from exc
    if not 0 < len(original) <= 100_000:
        raise ValueError("unexpected original workflow size")
    blob = hashlib.sha1(
        f"blob {len(original)}\0".encode() + original
    ).hexdigest()
    if blob != payload["sha"]:
        raise ValueError("pinned original Git blob SHA1 mismatch")
    try:
        return original.decode("utf-8"), blob
    except UnicodeDecodeError as exc:
        raise ValueError("original workflow not valid UTF-8") from exc


def audit(repo, token, ref=PINNED_MAIN, *, fetch=_remote_original):
    if (not isinstance(repo, str) or not REPO.fullmatch(repo)
            or any(p in (".", "..") for p in repo.split("/"))
            or not isinstance(token, str) or not token
            or not isinstance(ref, str) or not SHA.fullmatch(ref)):
        raise ValueError("authenticated pinned-main read required")
    files = {}
    hashes = {}
    for path in PATHS:
        received = fetch(repo, token, ref, path)
        if (not isinstance(received, tuple) or len(received) != 2
                or not isinstance(received[1], str)
                or not SHA.fullmatch(received[1])):
            raise ValueError("pinned Git original blob not returned")
        files[path], hashes[path] = received
    result = inspect(files, ref)
    result["remote_git_file_blob_sha1"] = hashes
    result["remote_git_file_sha1_checked"] = True if fetch is _remote_original else False
    return result


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--repo", required=True)
    p.add_argument("--main-commit", default=PINNED_MAIN)
    p.add_argument("--output", required=True)
    args = p.parse_args()
    result = audit(args.repo, os.environ.get("GITHUB_TOKEN"), args.main_commit)
    target = Path(args.output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                      encoding="utf-8")
    print("T12_SCHEDULED_TOPOLOGY=" + json.dumps(
        {k:v for k,v in result.items() if k!="remote_git_file_blob_sha1"},
        ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()

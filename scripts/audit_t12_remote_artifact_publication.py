"""Bounded audit of GitHub SERVER-side source-artifact archival timing at T−12.

Compares authenticated GitHub Actions run + artifact REST metadata against an
independently replayed same-race Nov9 official pair-source report. Artifact
created_at/updated_at is a remote publication observation, NOT a proof of the
first forecast Git remote acceptance, the original HTTP source receipt, or
consumption of the originals by any model. This cannot certify formal T−12.
"""
import argparse
import json
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.request import Request, urlopen

from scripts.audit_t12_nov09_real_pair_forecast_replay import (
    ARTIFACT_ID, RUN_ID, RACES, ZIP_SHA256,
)
from scripts.audit_t12_extracted_artifact_replay import artifact_metadata

SCHEMA = "T12_SOURCE_ARCHIVE_SERVER_TIME_AUDIT_V1"
INPUT = "T12_NOV09_REAL_OFFICIAL_PAIR_VS_FROZEN_FORECAST_V1"
REPO = re.compile(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+\Z")
SHA40 = re.compile(r"[a-f0-9]{40}\Z")
JST = timezone(timedelta(hours=9))
UTC = timezone.utc
Z = re.compile(r"20\d{2}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z\Z")


def _utc(raw):
    if not isinstance(raw, str) or not Z.fullmatch(raw):
        raise ValueError("GitHub UTC server timestamp must be explicit seconds-Z")
    try:
        return datetime.fromisoformat(raw[:-1] + "+00:00")
    except ValueError as exc:
        raise ValueError("invalid GitHub UTC timestamp") from exc


def _jst(raw, race):
    if not isinstance(raw, str):
        raise ValueError("missing source timestamp")
    try:
        when = datetime.fromisoformat(raw)
    except ValueError as exc:
        raise ValueError("invalid source timestamp") from exc
    if when.utcoffset() != timedelta(hours=9) or when.strftime("%Y%m%d") != race[:8]:
        raise ValueError("source timestamp not JST race date")
    return when.astimezone(UTC)


def inspect(replay, artifact, run):
    if not isinstance(replay, dict) or replay.get("schema") != INPUT:
        raise ValueError("independent source-versus-frozen replay required")
    if (replay.get("source_run_id") != RUN_ID
            or replay.get("source_artifact_id") != ARTIFACT_ID
            or replay.get("github_original_artifact_digest_from_metadata") != ZIP_SHA256
            or replay.get("extracted_official_source_originals_replayed") is not True
            or replay.get("github_original_zip_digest_locally_rehashed_by_ci") is not False
            or replay.get("two_original_complete_races") != 2
            or replay.get("matched_pinned_forecasts") != 4
            or replay.get("matched_forecasts_generated_after_sources") != 0
            or replay.get("three_official_original_races") != 0
            or replay.get("new_formal_certifications") != 0
            or replay.get("formal_accuracy_denominator") is not None
            or replay.get("formal") is not False
            or replay.get("accuracy_scoring_allowed") is not False):
        raise ValueError("upstream original-byte/forecast replay is not complete and nonformal")
    if (not isinstance(artifact, dict)
            or type(artifact.get("id")) is not int
            or artifact["id"] != ARTIFACT_ID
            or artifact.get("name") != f"independent-late-preview-{RUN_ID}"
            or artifact.get("digest") != "sha256:" + ZIP_SHA256
            or artifact.get("expired") is not False
            or type(artifact.get("size_in_bytes")) is not int
            or not 0 < artifact["size_in_bytes"] <= 20_000_000):
        raise ValueError("untrusted source artifact identity/digest")
    origin = artifact.get("workflow_run")
    if (not isinstance(origin, dict)
            or type(origin.get("id")) is not int or origin["id"] != RUN_ID
            or origin.get("head_branch") != "main"
            or not isinstance(origin.get("head_sha"), str)
            or not SHA40.fullmatch(origin["head_sha"])):
        raise ValueError("source artifact has wrong parent workflow run")
    if (not isinstance(run, dict)
            or type(run.get("id")) is not int or run["id"] != RUN_ID
            or run.get("event") != "schedule"
            or run.get("path") != ".github/workflows/research-live-preview-evidence.yml"
            or run.get("head_branch") != "main"
            or run.get("head_sha") != origin["head_sha"]
            or run.get("status") != "completed"
            or run.get("conclusion") != "success"):
        raise ValueError("GitHub source execution identity or scheduled provenance mismatch")
    created = _utc(artifact.get("created_at"))
    updated = _utc(artifact.get("updated_at"))
    started = _utc(run.get("run_started_at"))
    run_created = _utc(run.get("created_at"))
    run_updated = _utc(run.get("updated_at"))
    if not (run_created <= started <= created <= updated <= run_updated):
        raise ValueError("server-side Actions workflow/archive chronology mismatch")
    records = replay.get("race_rows")
    if (not isinstance(records, list) or len(records) != len(RACES)
            or sorted(row.get("race_code") if isinstance(row, dict) else None
                      for row in records) != list(RACES)):
        raise ValueError("same-race raw original evidence roster missing")
    rows = []
    for row in sorted(records, key=lambda item: item["race_code"]):
        code = row["race_code"]
        if (row.get("official_pair_originals_replayed_complete") is not True
                or row.get("racelist_official_original_present") is not False
                or row.get("formal") is not False
                or row.get("accuracy_scoring_allowed") is not False):
            raise ValueError("unreplayed source or overclaimed official originals")
        last = _jst(row.get("official_latest_original_received_jst"), code)
        cutoff = _jst(row.get("official_t12_cutoff_jst"), code)
        if not (started <= last <= cutoff):
            raise ValueError("source chronology outside workflow or T−12")
        # GitHub REST timestamps are only to the nearest second. Require at
        # least one full second of positive margin, never infer subsecond time.
        remote_archived_before_t12 = updated + timedelta(seconds=1) <= cutoff
        # Separate source's self-recorded HTTP receipt timestamp from GitHub
        # server's artifact creation and update timestamps.
        if created < last:
            raise ValueError("archive metadata predates final source receipt")
        forecasts = row.get("forecasts")
        if (not isinstance(forecasts, dict) or set(forecasts) !=
                {"clean", "v2_four_mode"}
                or any(not isinstance(f, dict) or
                       f.get("generated_strictly_after_official_pair") is not False
                       or f.get("first_git_remote_receipt_verified") is not False
                       or f.get("independent_actual_model_original_consumption_verified") is not False
                       or f.get("formal") is not False
                       for f in forecasts.values())):
            raise ValueError("frozen forecast lineage is unverified or post-source")
        rows.append({
            "race_code": code,
            "official_t12_cutoff_jst": cutoff.astimezone(JST).isoformat(),
            "last_official_original_receipt_self_recorded_jst": last.astimezone(JST).isoformat(),
            "github_artifact_updated_at_utc": updated.isoformat(),
            "github_artifact_updated_before_t12_one_sec_margin": remote_archived_before_t12,
            "github_archive_to_cutoff_margin_seconds": (cutoff-updated).total_seconds(),
            "two_official_original_bytes_replayed": True,
            "third_official_racelist_original_replayed": False,
            "forecast_generated_after_all_official_sources": False,
            "independent_first_forecast_git_remote_receipt_proven": False,
            "formal": False,
        })
    return {
        "schema": SCHEMA,
        "source_run_id": RUN_ID,
        "source_artifact_id": ARTIFACT_ID,
        "artifact_original_zip_sha256_from_github_metadata": ZIP_SHA256,
        "github_run_started_at_utc": started.isoformat(),
        "github_artifact_created_at_utc": created.isoformat(),
        "github_artifact_updated_at_utc": updated.isoformat(),
        "github_artifact_timestamp_origin": "authenticated_github_actions_rest",
        "original_actions_zip_rehashed_in_this_audit": False,
        "individual_official_original_bytes_replayed_by_upstream_audit": True,
        "race_rows": rows,
        "server_timestamp_artifact_archive_before_t12_races": sum(
            r["github_artifact_updated_before_t12_one_sec_margin"] for r in rows),
        "source_artifact_server_time_not_first_forecast_git_receipt": True,
        "official_three_originals_replayed": 0,
        "post_official_source_frozen_forecasts": 0,
        "new_formal_certifications": 0,
        "formal_accuracy_denominator": None,
        "formal": False,
        "t12_eligible": False,
        "accuracy_scoring_allowed": False,
        "scope_note": (
            "An authenticated GitHub Actions artifact server creation/update "
            "timestamp is positive remote archival-time evidence only. It "
            "does NOT establish precise first remote acceptance, independent "
            "HTTP-source receipt truth, third racelist, actual model consumption, "
            "forecast Git first receipt, or final race entries."),
    }


def _run_metadata(repo, token, run_id):
    endpoint = f"https://api.github.com/repos/{repo}/actions/runs/{run_id}"
    req = Request(endpoint, headers={
        "Authorization": "Bearer " + token,
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "Cache-Control": "no-cache",
        "User-Agent": "boat-edge-independent-source-remote-time",
    })
    with urlopen(req, timeout=20) as response:
        if response.status != 200:
            raise ValueError("GitHub source run metadata unavailable")
        return json.load(response)


def audit(repo, token, replay, *, get_artifact=artifact_metadata, get_run=_run_metadata):
    if (not isinstance(repo, str) or not REPO.fullmatch(repo)
            or any(part in (".", "..") for part in repo.split("/"))
            or not isinstance(token, str) or not token):
        raise ValueError("authenticated repository required")
    return inspect(replay, get_artifact(repo, token, ARTIFACT_ID),
                   get_run(repo, token, RUN_ID))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True)
    parser.add_argument("--replay", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    upstream = json.loads(Path(args.replay).read_text(encoding="utf-8"))
    result = audit(args.repo, os.environ.get("GITHUB_TOKEN"), upstream)
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8")
    print("T12_ARTIFACT_REMOTE_TIME=" + json.dumps({
        k: v for k, v in result.items() if k != "race_rows"
    }, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()

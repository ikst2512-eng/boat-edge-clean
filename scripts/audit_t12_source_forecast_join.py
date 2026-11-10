"""Read-only generic same-race source ZIP -> pinned Git forecast chronology.

Reuse the existing raw-original/manifest auditor and Git-content reader.
A source artifact time is NOT the independent first forecast Git acceptance.
No current/historical prediction can be upgraded to formal by this report.
"""
import argparse
import json
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

from scripts.audit_t12_archived_pair_forecast_replay import frozen_remote
from scripts.audit_t12_extracted_artifact_replay import artifact_metadata, replay_extracted
from scripts.audit_t12_remote_artifact_publication import _run_metadata

REPO = re.compile(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+\Z")
SHA = re.compile(r"[a-f0-9]{40}\Z")
SHA256 = re.compile(r"[a-f0-9]{64}\Z")
RACE = re.compile(r"20[0-9]{10}\Z")
JST = timedelta(hours=9)
WORKFLOW = ".github/workflows/research-live-preview-evidence.yml"


def stamp(value, *, offset=None):
    if not isinstance(value, str):
        raise ValueError("missing evidence timestamp")
    try:
        x = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("bad evidence timestamp") from exc
    if x.utcoffset() is None or (offset is not None and x.utcoffset() != offset):
        raise ValueError("wrong or missing evidence clock timezone")
    return x


def inspect(source, artifact, run, get_frozen, *, run_id, artifact_id,
            original_sha256, forecast_ref, expected_races):
    """All inputs are independently fetched; no inference from green job status."""
    if (type(run_id) is not int or run_id <= 0
            or type(artifact_id) is not int or artifact_id <= 0
            or not isinstance(original_sha256, str) or not SHA256.fullmatch(original_sha256)
            or not isinstance(forecast_ref, str) or not SHA.fullmatch(forecast_ref)
            or not isinstance(expected_races, (tuple, list))
            or not 1 <= len(expected_races) <= 2
            or any(not isinstance(r, str) or not RACE.fullmatch(r) for r in expected_races)
            or len(set(expected_races)) != len(expected_races)
            or len({r[:8] for r in expected_races}) != 1):
        raise ValueError("invalid pinned cohort identity")
    day = expected_races[0][:8]
    if (not isinstance(source, dict)
            or source.get("schema") != "T12_ACTUAL_SCHEDULED_SOURCE_PAIR_ZIP_REPLAY_V1"
            or source.get("run_id") != run_id or source.get("day_jst") != day
            or source.get("original_actions_artifact_sha256") != original_sha256
            or source.get("github_artifact_digest_metadata_matches") is not True
            or source.get("extracted_original_source_bytes_replayed") is not True
            or source.get("github_original_zip_digest_verified_by_local_hash") is not False
            or source.get("official_racelist_originals_verified") != 0
            or source.get("full_t12_source_certified") is not False
            or source.get("formal") is not False):
        raise ValueError("unreplayed or overclaimed original source ZIP")
    races = source.get("race_rows")
    if (not isinstance(races, list) or len(races) != len(expected_races)
            or sorted(r.get("race_code") if isinstance(r, dict) else ""
                      for r in races) != sorted(expected_races)
            or source.get("candidate_count") != len(expected_races)
            or type(source.get("two_original_complete_race_count")) is not int):
        raise ValueError("missing, duplicate, or substituted original-source race")
    if (not isinstance(artifact, dict)
            or artifact.get("id") != artifact_id
            or artifact.get("name") != "independent-late-preview-" + str(run_id)
            or artifact.get("digest") != "sha256:" + original_sha256
            or artifact.get("expired") is not False
            or (artifact.get("workflow_run") or {}).get("id") != run_id
            or type(artifact.get("size_in_bytes")) is not int
            or not 0 < artifact["size_in_bytes"] <= 20_000_000):
        raise ValueError("source ZIP server digest/identity not verified")
    if (not isinstance(run, dict) or run.get("id") != run_id
            or run.get("path") != WORKFLOW or run.get("event") != "schedule"
            or run.get("status") != "completed" or run.get("conclusion") != "success"):
        raise ValueError("source producer was not successful scheduled official collector")
    created = stamp(artifact.get("created_at"), offset=timedelta(0))
    published = stamp(artifact.get("updated_at"), offset=timedelta(0))
    run_created = stamp(run.get("created_at"), offset=timedelta(0))
    run_updated = stamp(run.get("updated_at"), offset=timedelta(0))
    if not run_created <= created <= published <= run_updated:
        raise ValueError("impossible GitHub source-archive publication chronology")
    items = []
    complete_pairs = 0
    forecast_cases = 0
    post_source = 0
    for source_row in sorted(races, key=lambda r: r["race_code"]):
        code = source_row["race_code"]
        complete = source_row.get("two_originals_complete_by_t12")
        if (type(complete) is not bool
                or source_row.get("official_beforeinfo_original_replayed") is not True
                or source_row.get("official_odds_original_replayed") is not True
                or source_row.get("official_racelist_original_replayed") is not False
                or source_row.get("formal") is not False):
            raise ValueError("invalid source-original component proof")
        cutoff = stamp(source_row.get("official_t12_cutoff_jst"), offset=JST)
        before = stamp(source_row.get("beforeinfo_received_jst"), offset=JST)
        last = stamp(source_row.get("last_source_received_jst"), offset=JST)
        if (cutoff.strftime("%Y%m%d") != day or before.strftime("%Y%m%d") != day
                or last.strftime("%Y%m%d") != day or before > last
                or published < last):
            raise ValueError("cross-day, reversed, or impossibly archived source")
        if complete and (last > cutoff
                         or source_row.get("official_odds_120_verified") is not True
                         or source_row.get("exhibition_time_observed_boats") != 6
                         or source_row.get("start_exhibition_six_valid_rows") is not True):
            raise ValueError("complete pair contradicts independently replayed raw fields")
        if (not complete and source_row.get("reported_status") == "pair_complete"):
            raise ValueError("reported positive pair contradicts independent replay")
        complete_pairs += int(complete)
        server_before_t12 = published + timedelta(seconds=1) <= cutoff
        mode_rows = {}
        for mode, folder in (("clean", "prospective_predictions"),
                             ("v2_four_mode", "four_mode_forecasts")):
            frozen, git = get_frozen(f"{folder}/{code}.json")
            if (not isinstance(frozen, dict) or frozen.get("race_code") != code
                    or not isinstance(git, dict)
                    or git.get("pinned_remote_commit") != forecast_ref
                    or not isinstance(git.get("remote_sha256"), str)
                    or not SHA256.fullmatch(git["remote_sha256"])
                    or not isinstance(git.get("remote_git_blob_sha1"), str)
                    or not SHA.fullmatch(git["remote_git_blob_sha1"])):
                raise ValueError("forecast remote immutable content not proven")
            values = [frozen[key] for key in ("generated_at", "generated_at_jst")
                      if frozen.get(key) is not None]
            if len(values) != 1:
                raise ValueError("ambiguous forecast generation timestamp")
            generated = stamp(values[0], offset=JST)
            if generated.strftime("%Y%m%d") != day:
                raise ValueError("forecast from wrong racing day")
            after = generated > last
            forecast_cases += 1
            post_source += int(after)
            mode_rows[mode] = {
                "generated_at_jst": generated.isoformat(),
                "generated_after_pair_sources": after,
                "generated_before_t12": generated <= cutoff,
                "source_input_declared": frozen.get("input_source_kind"),
                "beforeinfo_input_declared": frozen.get("beforeinfo"),
                "forecast_git_blob_sha1": git["remote_git_blob_sha1"],
                "forecast_sha256": git["remote_sha256"],
                "first_forecast_git_remote_acceptance_verified": False,
                "actual_model_official_original_bytes_consumption_verified": False,
                "formal": False,
            }
        items.append({
            "race_code": code,
            "source_pair_complete_by_t12": complete,
            "exhibition_time_observed_boats": source_row.get("exhibition_time_observed_boats"),
            "official_odds_120_verified": source_row.get("official_odds_120_verified") is True,
            "last_original_source_received_jst": last.isoformat(),
            "official_t12_cutoff_jst": cutoff.isoformat(),
            "github_source_archive_published_at_utc": published.isoformat(),
            "independent_source_zip_published_by_t12": server_before_t12,
            "official_racelist_original_replayed": False,
            "frozen_forecasts": mode_rows,
            "source_pair_first_blocker": (
                "official_racelist_original_missing" if complete else
                "source_exhibition_or_timing_incomplete"),
            "model_consumption_proven": False,
            "first_forecast_git_remote_acceptance_proven": False,
            "final_entry_verified": False,
            "formal": False,
        })
    if complete_pairs != source["two_original_complete_race_count"]:
        raise ValueError("source ZIP aggregate and row counts disagree")
    return {
        "schema": "T12_PINNED_SCHEDULED_PAIR_FROZEN_REPLAY_V1",
        "source_run_id": run_id, "source_artifact_id": artifact_id,
        "day_jst": day, "source_original_zip_sha256_from_metadata": original_sha256,
        "original_zip_directly_rehashed_inside_ci": False,
        "source_originals_individually_replayed": True,
        "github_server_source_archive_published_at_utc": published.isoformat(),
        "pinned_forecast_ref": forecast_ref,
        "original_source_candidate_races": len(items),
        "complete_two_original_races": complete_pairs,
        "matched_immutable_forecasts": forecast_cases,
        "forecasts_generated_after_originals": post_source,
        "same_race_complete_official_three_originals": 0,
        "verified_model_original_byte_consumption": 0,
        "verified_first_forecast_remote_acceptances": 0,
        "new_formal_certifications": 0,
        "formal_accuracy_denominator": None,
        "race_rows": items,
        "formal": False, "t12_eligible": False,
        "accuracy_scoring_allowed": False,
    }


def run(repo, token, root, *, run_id, artifact_id, digest, forecast_ref,
        expected_races, metadata_getter=artifact_metadata,
        extracted_auditor=replay_extracted, get_run=_run_metadata,
        frozen_getter=frozen_remote):
    if (not isinstance(repo, str) or not REPO.fullmatch(repo)
            or any(x in (".", "..") for x in repo.split("/"))
            or not isinstance(token, str) or not token):
        raise ValueError("authenticated read-only access required")
    artifact = metadata_getter(repo, token, artifact_id)
    source = extracted_auditor(
        root, run_id=run_id, artifact_id=artifact_id,
        digest=digest, metadata=artifact)
    return inspect(
        source, artifact, get_run(repo, token, run_id),
        lambda path: frozen_getter(repo, token, forecast_ref, path),
        run_id=run_id, artifact_id=artifact_id, original_sha256=digest,
        forecast_ref=forecast_ref, expected_races=expected_races)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True)
    parser.add_argument("--extracted-root", required=True)
    parser.add_argument("--run-id", required=True, type=int)
    parser.add_argument("--artifact-id", required=True, type=int)
    parser.add_argument("--digest", required=True)
    parser.add_argument("--forecast-ref", required=True)
    parser.add_argument("--expected-races", required=True,
                        help="comma-separated same-day race codes")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    result = run(
        args.repo, os.environ.get("GITHUB_TOKEN"), Path(args.extracted_root),
        run_id=args.run_id, artifact_id=args.artifact_id,
        digest=args.digest, forecast_ref=args.forecast_ref,
        expected_races=args.expected_races.split(","))
    target = Path(args.output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n",
                      encoding="utf-8")
    print("T12_PINNED_PAIR_FROZEN=" + json.dumps(
        {k: v for k, v in result.items() if k != "race_rows"},
        ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()

"""Audit real Nov 5-8 GitHub Actions official pair ZIPs vs exact main Git blobs.

This is bounded historical research. The downloaded ZIPs undergo independent
original/manifest/raw-source replay. Immutable forecast JSON is fetched at an
explicit pinned Git commit, with Git blob SHA1 verified against decoded bytes.
A green capture or predeadline forecast does NOT prove official-input use,
first Git remote acceptance, final entry, or formal T-12 eligibility.
"""
import argparse
import base64
import binascii
import hashlib
import json
import os
import re
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen

from scripts.audit_t12_scheduled_pair_zip import replay as replay_source_zip
from scripts.inspect_joint_t12_archive import load_archive

REPO_PATTERN = re.compile(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+\Z")
HEX40 = re.compile(r"[a-f0-9]{40}\Z")
DAY = re.compile(r"20[0-9]{6}\Z")
FORECAST_REF = "6b371040fd2fc4398bfa882e6557c333cc0800c8"
# All refs are stable historical 2026-11-05..08 GitHub-returned ZIPs and digests.
# Ingestion is never allowed to replace a missing artifact with a status flag.
ARTIFACTS = (
    (41976534374, 13391673467,
     "cdd941d41d43adcadbbc24224a94654ec76962616dd16ea995506a3fb8b670ce",
     "20261105"),
    (42170457446, 13480945699,
     "f6e167d79648bb67ec0a3727cc61272291ba00b11c67fad9a186c281e5db89c1",
     "20261106"),
    (42342115412, 13561893314,
     "730f703cb24599a6ef94de3c6e314f54d3f07110265e453794e0d64d38b1323f",
     "20261107"),
    (42450048245, 13604969020,
     "2bda1f350f18d7516ae685fd6a10094915fa00ae6cd8f3f3151b4bef651d2a5c",
     "20261108"),
)
JST = timedelta(hours=9)


def _timestamp(value, day):
    if not isinstance(value, str):
        raise ValueError("frozen or original timestamp missing")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("invalid frozen or original timestamp") from exc
    if parsed.utcoffset() != JST or parsed.strftime("%Y%m%d") != day:
        raise ValueError("forecast/source timestamp not same JST race day")
    return parsed


def frozen_remote(repo, token, ref, path):
    """Fetch a pinned GitHub JSON blob. A 403/404/timeout is an error, not data."""
    if (not isinstance(repo, str) or not REPO_PATTERN.fullmatch(repo)
            or not isinstance(ref, str) or not HEX40.fullmatch(ref)
            or not token):
        raise ValueError("invalid GitHub immutable archive credentials")
    if not re.fullmatch(
            r"(?:prospective_predictions|four_mode_forecasts)/20[0-9]{10}\.json",
            path):
        raise ValueError("unapproved immutable forecast path")
    url = ("https://api.github.com/repos/" + repo + "/contents/" + path
           + "?ref=" + quote(ref))
    req = Request(url, headers={
        "Authorization": "Bearer " + token,
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "Cache-Control": "no-cache",
        "User-Agent": "boat-edge-independent-historical-source-forecast-audit",
    })
    with urlopen(req, timeout=25) as response:
        if response.status != 200:
            raise ValueError("GitHub immutable forecast HTTP not 200")
        metadata = json.load(response)
    if (not isinstance(metadata, dict)
            or metadata.get("path") != path
            or metadata.get("type") != "file"
            or metadata.get("encoding") != "base64"
            or not isinstance(metadata.get("content"), str)):
        raise ValueError("GitHub returned nonmatching forecast file metadata")
    try:
        raw = base64.b64decode(metadata["content"], validate=False)
    except (ValueError, binascii.Error) as exc:
        raise ValueError("malformed remote Git base64") from exc
    if not raw or len(raw) > 120_000:
        raise ValueError("remote frozen blob size invalid")
    git_sha = hashlib.sha1(
        b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()
    if metadata.get("sha") != git_sha:
        raise ValueError("remote Git object SHA does not match original bytes")
    frozen = json.loads(raw)
    if not isinstance(frozen, dict):
        raise ValueError("remote immutable forecast not JSON object")
    return frozen, {
        "remote_git_blob_sha1": git_sha,
        "remote_sha256": hashlib.sha256(raw).hexdigest(),
        "pinned_remote_commit": ref,
    }


def reconcile(replays, *, get_frozen):
    """Derive causality only from independently replayed original ZIP reports."""
    if (not isinstance(replays, list) or len(replays) != len(ARTIFACTS)):
        raise ValueError("four real bounded historical source run reports required")
    by_run = {}
    for item in replays:
        if (not isinstance(item, dict)
                or item.get("run_id") in by_run
                or item.get("status") != "source_pairs_independently_replayed_nonformal"
                or item.get("full_t12_source_certified") is not False
                or item.get("formal") is not False
                or item.get("official_racelist_originals_verified") != 0):
            raise ValueError("ineligible original ZIP replay identity")
        by_run[item["run_id"]] = item
    rows = []
    source_pairs = 0
    checked_forecasts = 0
    post_source_forecasts = 0
    for run_id, _, digest, day in ARTIFACTS:
        item = by_run.get(run_id)
        if (item is None or item.get("day_jst") != day
                or item.get("artifact_sha256") != digest
                or type(item.get("candidate_count")) is not int
                or not isinstance(item.get("race_rows"), list)
                or len(item["race_rows"]) != item["candidate_count"]
                or type(item.get("two_original_complete_race_count")) is not int):
            raise ValueError("missing or substituted historical source ZIP replay")
        observed_complete = 0
        for pair in item["race_rows"]:
            if (not isinstance(pair, dict)
                    or not isinstance(pair.get("race_code"), str)
                    or not pair["race_code"].startswith(day)
                    or len(pair["race_code"]) != 12
                    or pair.get("formal") is not False):
                raise ValueError("invalid race-level original report")
            code = pair["race_code"]
            complete = pair.get("two_originals_complete_by_t12")
            if type(complete) is not bool:
                raise ValueError("missing independent complete-pair verdict")
            observed_complete += int(complete)
            row = {
                "race_code": code, "source_run_id": run_id,
                "original_pair_replayed_complete": complete,
                "official_racelist_original_replayed": False,
                "forecast_usable": False,
                "formal": False,
                "forecasts": {},
            }
            if not complete:
                row["status"] = "original_pair_incomplete"
                rows.append(row)
                continue
            source_pairs += 1
            cutoff = _timestamp(pair.get("official_t12_cutoff_jst"), day)
            before = _timestamp(pair.get("beforeinfo_received_jst"), day)
            latest = _timestamp(pair.get("last_source_received_jst"), day)
            if latest < before or latest > cutoff:
                raise ValueError("positive original pair contradictory timestamps")
            if pair.get("official_odds_120_verified") is not True:
                raise ValueError("positive original pair missing 120 unique odds")
            row["official_last_source_received_jst"] = latest.isoformat()
            row["official_t12_cutoff_jst"] = cutoff.isoformat()
            for mode, prefix in (
                ("clean", "prospective_predictions"),
                ("v2_four_mode", "four_mode_forecasts")
            ):
                path = f"{prefix}/{code}.json"
                frozen, git_evidence = get_frozen(path)
                if not isinstance(frozen, dict) or frozen.get("race_code") != code:
                    raise ValueError("frozen forecast race identity mismatch")
                stamps = [
                    frozen[k] for k in ("generated_at", "generated_at_jst")
                    if frozen.get(k) is not None
                ]
                if len(stamps) != 1:
                    raise ValueError("frozen forecast timestamp ambiguous")
                generated = _timestamp(stamps[0], day)
                is_later = generated > latest
                checked_forecasts += 1
                post_source_forecasts += int(is_later)
                if not isinstance(git_evidence, dict):
                    raise ValueError("frozen remote evidence unavailable")
                if (git_evidence.get("pinned_remote_commit") != FORECAST_REF
                        or not isinstance(git_evidence.get("remote_sha256"), str)
                        or not re.fullmatch(r"[a-f0-9]{64}",
                                            git_evidence["remote_sha256"])):
                    raise ValueError("unverified immutable original forecast blob")
                row["forecasts"][mode] = {
                    "remote_git_blob_sha1": git_evidence.get("remote_git_blob_sha1"),
                    "remote_sha256": git_evidence["remote_sha256"],
                    "pinned_commit": FORECAST_REF,
                    "generated_at_jst": generated.isoformat(),
                    "source_receipt_minus_generation_seconds":
                        round((latest - generated).total_seconds(), 3),
                    "generated_strictly_after_official_source": is_later,
                    "generated_by_official_t12": generated <= cutoff,
                    "declared_input_source_kind": frozen.get("input_source_kind"),
                    "declared_beforeinfo": frozen.get("beforeinfo"),
                    "independent_first_github_remote_receipt_verified": False,
                    "model_consumed_official_original_bytes_verified": False,
                    "formal": False,
                }
            row["status"] = "archived_frozen_forecasts_compared_nonformal"
            rows.append(row)
        if observed_complete != item["two_original_complete_race_count"]:
            raise ValueError("source-replay declared pair count contradictory")
    return {
        "schema": "T12_HISTORICAL_REAL_ZIP_VS_PINNED_FORECAST_V1",
        "day_scope": "20261105-20261108",
        "pinned_main_commit": FORECAST_REF,
        "four_archived_source_runs_replayed": len(replays),
        "source_pair_races": len(rows),
        "official_two_original_complete_races": source_pairs,
        "matched_immutable_forecasts": checked_forecasts,
        "forecasts_generated_after_sources": post_source_forecasts,
        "race_rows": rows,
        "official_three_original_races": 0,
        "independent_model_input_consumption_verified": False,
        "independent_first_remote_receipt_verified": False,
        "final_entry_verified": False,
        "full_t12_source_certified": False,
        "formal": False,
        "t12_eligible": False,
        "accuracy_scoring_allowed": False,
        "formal_accuracy_denominator": None,
        "note": ("Read-only immutable historical source-vs-forecast comparison; "
                 "Git contents API proves that bytes exist at pinned commit, "
                 "not first remote acceptance time or original-byte input use."),
    }


def run(repo, token, *, zip_loader=load_archive, frozen_getter=frozen_remote,
        zip_auditor=replay_source_zip):
    if not token or not isinstance(repo, str) or not REPO_PATTERN.fullmatch(repo):
        raise ValueError("read-only GitHub token and repository are required")
    replays = [
        zip_auditor(zip_loader(repo, token, artifact), run_id, digest)
        for run_id, artifact, digest, _ in ARTIFACTS
    ]
    return reconcile(
        replays,
        get_frozen=lambda path: frozen_getter(repo, token, FORECAST_REF, path),
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    result = run(args.repo, os.environ.get("GITHUB_TOKEN"))
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                   encoding="utf-8")
    print("T12_REAL_ZIP_FORECAST_REPLAY=" + json.dumps({
        k: v for k, v in result.items() if k != "race_rows"
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()

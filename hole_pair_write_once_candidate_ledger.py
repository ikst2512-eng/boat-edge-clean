"""Draft-only write-once hole-pair research evidence adapter.

Stores the exact candidate RECORD, not post-result recomputed tickets. Uses
the existing v2-third-rate-evidence-ledger branch, never main. This module is
NOT wired to a scheduled workflow or any production predictor.

A GitHub Date on a later GET is a remote AVAILABILITY observation, never
an authenticated *first acceptance* timestamp. All output remains nonformal.
"""
import argparse
import base64
import hashlib
import json
import os
import re
import urllib.request
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

from hole_pair_remote_receipt_evidence import (
    _validate_frozen, canonical_bytes, inspect,
)
from hole_future_locked_eval import verify_locked_selection

RACE = re.compile(r"20[0-9]{10}\Z")
REPO = re.compile(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+\Z")
LEDGER_BRANCH = "v2-third-rate-evidence-ledger"
SCHEMA = "HOLE_PAIR_CANDIDATE_REMOTE_OBSERVATION_V1"


def git_blob_sha1(raw):
    return hashlib.sha1(
        b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw
    ).hexdigest()


def prepare(record, root):
    """Verify original forecast + frozen selector, before touching a ledger."""
    code, _ = _validate_frozen(record)
    if type(record.get("source_git_blob_sha1")) is not str:
        raise ValueError("original_git_blob_missing")
    root = Path(root)
    source = root / "four_mode_forecasts" / (code + ".json")
    if (source.is_symlink() or not source.is_file()
            or source.stat().st_size > 30000):
        raise ValueError("original_forecast_missing_or_unsafe")
    raw_source = source.read_bytes()
    if (hashlib.sha256(raw_source).hexdigest() != record["source_sha256"]
            or git_blob_sha1(raw_source) != record["source_git_blob_sha1"]):
        raise ValueError("original_forecast_fingerprint_mismatch")
    try:
        archive = json.loads(raw_source)
        if (type(archive) is not dict or archive.get("race_code") != code
                or archive.get("deadline_jst") != record["deadline_jst"]
                or archive.get("model_version") != record["model_version"]):
            raise ValueError("original_forecast_identity_mismatch")
        created = datetime.fromisoformat(archive["generated_at_jst"])
        started = datetime.fromisoformat(record["local_start_jst"])
        if (created.utcoffset() != timedelta(hours=9)
                or created >= started):
            raise ValueError("source_created_after_candidate")
        from hole_future_pair_precommit import select
        if select(archive) != record["candidates"]:
            raise ValueError("frozen_selector_replay_mismatch")
    except (TypeError, KeyError, AttributeError, json.JSONDecodeError) as exc:
        raise ValueError("original_forecast_untrusted") from exc
    # Compare the code actually running with the originally frozen method and
    # every precommitted selector blob, not just the record's self-reported hash.
    method_path = Path(__file__).resolve().parent / "hole_future_pair_precommit.py"
    if (method_path.is_symlink() or not method_path.is_file()
            or hashlib.sha256(method_path.read_bytes()).hexdigest()
            != record["method_source_sha256"]
            or record.get("locked_selector_git_blobs")
            != verify_locked_selection()):
        raise ValueError("locked_selector_or_method_source_mismatch")
    path = "hole_pair_candidates/" + code[:8] + "/" + code + ".json"
    return path, canonical_bytes(record)


def _observation(record, when, remotely_received):
    if (not isinstance(when, datetime) or when.utcoffset() != timedelta(0)
            or type(remotely_received) is not bytes):
        raise ValueError("remote_response_invalid")
    raw = canonical_bytes(record)
    return inspect(record, {
        "kind": "github_api_readback_not_first_receipt",
        "race_code": record["race_code"],
        "candidate_record_sha256": hashlib.sha256(raw).hexdigest(),
        "github_blob_sha1": git_blob_sha1(remotely_received),
        "remote_bytes": remotely_received,
        "server_observed_at_utc": when.isoformat(),
    })


def publish_one(record, root, remote_read, remote_create, remote_observe, *, now=None):
    """Create-only / byte-identical replay; observations are NEVER formal.

    All remote functions are injected. remote_create must use a create-only
    API that omits an existing content SHA; never update an existing file.
    """
    path, raw = prepare(record, root)
    cutoff = datetime.fromisoformat(record["t_minus_12_jst"])
    clock = datetime.now(timezone.utc) if now is None else now
    if not isinstance(clock, datetime) or clock.utcoffset() is None:
        raise ValueError("untrusted_write_clock")
    old = remote_read(path)
    if old is None:
        # Local clock is a necessary negative gate, NOT evidence of independent
        # server first acceptance. A strictly earlier margin avoids same-second
        # ambiguity; in live use recheck immediately before the create call.
        if clock + timedelta(seconds=1) >= cutoff or (
                now is None and datetime.now(timezone.utc) +
                timedelta(seconds=1) >= cutoff):
            raise ValueError("new_candidate_remote_write_too_late")
        remote_create(path, raw, "hole-pair-research-candidate")
        status = "new_write_once_candidate"
    elif old == raw:
        status = "existing_identical_candidate"
    else:
        raise ValueError("immutable_candidate_collision")
    if remote_read(path) != raw:
        raise ValueError("candidate_remote_readback_mismatch")
    note_path = path.replace(
        "hole_pair_candidates/", "hole_pair_observations/", 1)
    old_note = remote_read(note_path)
    if old_note is None:
        when, remote_bytes = remote_observe(path)
        verdict = _observation(record, when, remote_bytes)
        note = {
            "schema": SCHEMA,
            "race_code": record["race_code"],
            "candidate_path": path,
            "candidate_sha256": hashlib.sha256(raw).hexdigest(),
            "observed_at_utc": when.isoformat(),
            "observation_status": verdict["status"],
            "independent_first_receipt_verified": False,
            "official_t12_complete_verified": False,
            "formal": False,
            "production_promotion_allowed": False,
        }
        note_raw = canonical_bytes(note)
        remote_create(note_path, note_raw, "hole-pair-research-observation")
        if remote_read(note_path) != note_raw:
            raise ValueError("observation_remote_readback_mismatch")
        note_status = "new_write_once_observation"
    else:
        if type(old_note) is not bytes or len(old_note) > 10000:
            raise ValueError("previous_observation_untrusted")
        try:
            note = json.loads(old_note)
            if (type(note) is not dict or note.get("schema") != SCHEMA
                    or note.get("race_code") != record["race_code"]
                    or note.get("candidate_path") != path
                    or note.get("candidate_sha256")
                    != hashlib.sha256(raw).hexdigest()
                    or any(note.get(k) is not False for k in (
                        "independent_first_receipt_verified",
                        "official_t12_complete_verified",
                        "formal", "production_promotion_allowed"))):
                raise ValueError("previous_observation_conflict")
            verified = _observation(
                record, datetime.fromisoformat(note["observed_at_utc"]), raw)
            if verified["status"] != note.get("observation_status"):
                raise ValueError("previous_observation_time_conflict")
        except (KeyError, TypeError, UnicodeError, json.JSONDecodeError) as exc:
            raise ValueError("previous_observation_untrusted") from exc
        if remote_read(note_path) != old_note:
            raise ValueError("previous_observation_changed")
        note_status = "existing_identical_observation"
    return {
        "schema": "HOLE_PAIR_WRITE_ONCE_LEDGER_REPORT_V1",
        "race_code": record["race_code"],
        "status": status,
        "observation_status": note["observation_status"],
        "observation_record_status": note_status,
        "candidate_path": path,
        "observation_path": note_path,
        "candidate_sha256": hashlib.sha256(raw).hexdigest(),
        "independent_first_receipt_verified": False,
        "official_t12_complete_verified": False,
        "formal": False,
        "production_promotion_allowed": False,
    }


def github_observe(repository, path):
    """Authenticated GitHub GET Date; NOT independent first acceptance."""
    if (type(repository) is not str or not REPO.fullmatch(repository)
            or type(path) is not str
            or not re.fullmatch(
                r"hole_pair_candidates/20[0-9]{6}/20[0-9]{10}\.json",
                path)):
        raise ValueError("invalid_remote_target")
    token = os.environ.get("GH_TOKEN")
    if not token:
        raise ValueError("missing_github_token")
    url = ("https://api.github.com/repos/" + repository
           + "/contents/" + path + "?ref=" + LEDGER_BRANCH)
    request = urllib.request.Request(url, headers={
        "Authorization": "Bearer " + token,
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "Cache-Control": "no-cache",
        "User-Agent": "hole-pair-research-observation",
    })
    with urllib.request.urlopen(request, timeout=25) as response:
        if response.status != 200 or response.headers.get("Age") is not None:
            raise ValueError("uncached_github_readback_unavailable")
        timestamp = parsedate_to_datetime(response.headers.get("Date", ""))
        if timestamp.utcoffset() != timedelta(0):
            raise ValueError("invalid_server_date")
        obj = json.loads(response.read(180000))
    if (type(obj) is not dict or obj.get("type") != "file"
            or obj.get("path") != path or obj.get("encoding") != "base64"
            or type(obj.get("content")) is not str):
        raise ValueError("github_candidate_response_invalid")
    remote_bytes = base64.b64decode(obj["content"], validate=False)
    if (not remote_bytes or len(remote_bytes) > 100000
            or obj.get("sha") != git_blob_sha1(remote_bytes)):
        raise ValueError("github_candidate_blob_mismatch")
    return timestamp, remote_bytes


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--record", type=Path, required=True)
    p.add_argument("--root", type=Path, default=Path("."))
    p.add_argument("--publish", action="store_true")
    args = p.parse_args()
    if args.record.is_symlink() or args.record.stat().st_size > 100000:
        raise ValueError("unsafe_record_file")
    record = json.loads(args.record.read_bytes())
    path, raw = prepare(record, args.root)
    if not args.publish:
        print(json.dumps({
            "status": "locally_verified_not_remotely_published",
            "candidate_path": path,
            "candidate_sha256": hashlib.sha256(raw).hexdigest(),
            "formal": False,
        }, sort_keys=True))
        return
    if (os.environ.get("GITHUB_EVENT_NAME") != "workflow_dispatch"
            or os.environ.get("HOLE_PAIR_LEDGER_MANUAL_APPROVAL") != "YES"
            or os.environ.get("GITHUB_REF")
            != "refs/heads/research/hole-pair-future-precommit-20261105"):
        raise ValueError("manual_dispatch_approval_required")
    from third_rate_evidence_ledger import _github_ops
    repository = os.environ["GITHUB_REPOSITORY"]
    if not REPO.fullmatch(repository):
        raise ValueError("invalid_github_repository")
    get, create = _github_ops(repository)
    result = publish_one(record, args.root, get, create,
                         lambda location: github_observe(repository, location))
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()

"""Append-only long-term copy of the *original* same-job third-rate shadow.

Uses a separate GitHub branch, never main forecast files or post-result
recomputed picks. The GitHub commit is a durable copy, NOT independent
pre-cutoff receipt or a formally untouched prospective holdout.
"""
import base64
import hashlib
import json
import os
import re
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

from four_mode_v2_third_rate_shadow import PROTOCOL

BRANCH = "v2-third-rate-evidence-ledger"
SCHEMA = "V2_THIRD_RATE_SAME_JOB_FROZEN_SHADOW_V1"
RUN = re.compile(r"[1-9][0-9]{0,16}\Z")
SHA = re.compile(r"[a-f0-9]{40}\Z")
HEX = re.compile(r"[a-f0-9]{64}\Z")
CODE = re.compile(r"20[0-9]{10}\Z")
REPO = re.compile(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+\Z")
JST = timezone(timedelta(hours=9))


def prepare(original, root, run_id, attempt):
    """Validate original byte-for-byte artifact and return immutable branch path.

    A new ledger entry can be created only for a capture run with at least
    one frozen, before-T-12 prediction. Other rows remain in the original
    evidence to preserve explicit noneligibility and audit failures.
    """
    if (type(run_id) is not str or not RUN.fullmatch(run_id)
            or type(attempt) is not str or not RUN.fullmatch(attempt)):
        raise ValueError("invalid_run_identity")
    if len(original) > 2_000_000 or not original:
        raise ValueError("invalid_evidence_size")
    data = json.loads(original)
    if (type(data) is not dict or data.get("schema") != SCHEMA
            or data.get("protocol") != PROTOCOL
            or data.get("formal") is not False
            or data.get("independent_remote_first_seen_verified") is not False
            or data.get("production_forecast_changed") is not False):
        raise ValueError("invalid_frozen_evidence_header")
    count = data.get("published_forecasts")
    frozen = data.get("frozen_before_t_minus_12")
    errors = data.get("validation_error_count", 0)
    rows = data.get("records")
    if (type(count) is not int or not 0 <= count <= 500
            or type(frozen) is not int or not 0 <= frozen <= count
            or type(errors) is not int or not 0 <= errors <= count
            or type(rows) is not list or len(rows) != count):
        raise ValueError("invalid_record_counts")
    if frozen == 0:
        return None
    sha = data.get("publication_commit_sha")
    if (data.get("status") != "captured_local_after_push_not_remote_proven"
            or type(sha) is not str or not SHA.fullmatch(sha)):
        raise ValueError("invalid_publication_claim")
    if sum(type(r) is dict and r.get("status") == "frozen_in_same_job_before_t_minus_12"
           for r in rows) != frozen:
        raise ValueError("frozen_count_mismatch")
    seen = set()
    days = set()
    for row in rows:
        if type(row) is not dict or type(row.get("race_code")) is not str:
            raise ValueError("invalid_race_row")
        race = row["race_code"]
        if not CODE.fullmatch(race) or race in seen:
            raise ValueError("duplicate_or_invalid_race")
        seen.add(race)
        if row.get("status") != "frozen_in_same_job_before_t_minus_12":
            continue
        days.add(race[:8])
        if race[:8] < "20261104" or row.get("protocol") != PROTOCOL:
            raise ValueError("development_or_wrong_protocol")
        if row.get("source_commit_sha") != sha:
            raise ValueError("source_commit_mismatch")
        from four_mode_v2_frozen_third_artifact_score import _tickets
        if not (_tickets(row.get("baseline_top10"))
                and _tickets(row.get("candidate_top10"))):
            raise ValueError("bad_frozen_tickets")
        try:
            created = datetime.fromisoformat(row["frozen_at_utc"])
            cutoff = datetime.fromisoformat(row["t_minus_12_jst"])
        except (ValueError, TypeError, KeyError) as exc:
            raise ValueError("invalid_frozen_timestamp") from exc
        if (created.utcoffset() is None or cutoff.utcoffset() != timedelta(hours=9)
                or created >= cutoff or cutoff.strftime("%Y%m%d") != race[:8]):
            raise ValueError("late_or_inconsistent_frozen_timestamp")
        path = Path(root) / "four_mode_forecasts" / (race + ".json")
        digest = row.get("source_forecast_sha256")
        if (type(digest) is not str or not HEX.fullmatch(digest)
                or path.is_symlink() or not path.is_file()
                or path.stat().st_size > 30000
                or hashlib.sha256(path.read_bytes()).hexdigest() != digest):
            raise ValueError("frozen_source_digest_mismatch")
    if len(days) != 1:
        raise ValueError("multi_day_capture_not_supported")
    race_day = next(iter(days))
    name = f"third_rate/{race_day}/run-{run_id}-attempt-{attempt}.json"
    return name


def publish(original, root, run_id, attempt, remote_read, remote_create):
    path = prepare(original, root, run_id, attempt)
    if path is None:
        return {"status": "no_eligible_frozen_predictions",
                "stored": False, "formal": False}
    digest = hashlib.sha256(original).hexdigest()
    old = remote_read(path)
    if old is not None:
        if old != original:
            raise ValueError("immutable_ledger_collision")
        status = "already_preserved_identical"
    else:
        remote_create(path, original, run_id)
        status = "new_immutable_ledger_entry"
    if remote_read(path) != original:
        raise ValueError("ledger_readback_mismatch")
    return {"status": status, "branch": BRANCH, "path": path,
            "original_sha256": digest, "stored": True,
            "formal": False, "independent_remote_first_seen_verified": False}


def _api(args):
    result = subprocess.run(["gh", "api", *args],
                            capture_output=True, timeout=30)
    return result


def _github_ops(repository):
    if not REPO.fullmatch(repository):
        raise ValueError("invalid_repository")
    def get(path):
        r = _api(["-X", "GET",
                  f"repos/{repository}/contents/{path}?ref={BRANCH}"])
        if r.returncode:
            if b"HTTP 404" in r.stderr:
                return None
            raise ValueError("github_read_failed")
        payload = json.loads(r.stdout)
        if payload.get("type") != "file":
            raise ValueError("github_ledger_entry_not_file")
        return base64.b64decode(payload["content"], validate=False)
    def put(path, original, run_id):
        encoded = base64.b64encode(original).decode("ascii")
        r = _api(["-X", "PUT",
                  f"repos/{repository}/contents/{path}",
                  "-f", f"message=research: preserve third-rate frozen shadow from capture run {run_id}",
                  "-f", f"branch={BRANCH}", "-f", f"content={encoded}"])
        if r.returncode:
            raise ValueError("github_append_only_write_failed")
    return get, put


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--evidence", type=Path,
                        default=Path("four-mode-evidence/third-rate-shadow.json"))
    parser.add_argument("--output", type=Path,
                        default=Path("four-mode-evidence/third-rate-ledger.json"))
    args = parser.parse_args()
    verdict = None
    try:
        if not args.evidence.is_file() or args.evidence.is_symlink():
            raise ValueError("missing_original_shadow")
        original = args.evidence.read_bytes()
        remote_read, remote_create = _github_ops(os.environ["GITHUB_REPOSITORY"])
        verdict = publish(original, args.root, os.environ["GITHUB_RUN_ID"],
                          os.environ.get("GITHUB_RUN_ATTEMPT", "1"),
                          remote_read, remote_create)
    except (OSError, KeyError, ValueError, TypeError,
            subprocess.SubprocessError) as exc:
        verdict = {"status": "ledger_preservation_failed", "stored": False,
                   "formal": False, "error_type": type(exc).__name__}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(verdict, ensure_ascii=False,
                                     sort_keys=True, indent=2) + "\n",
                           encoding="utf-8")
    print("THIRD_RATE_DURABLE_LEDGER=" + json.dumps(verdict, sort_keys=True))
    if verdict["status"] == "ledger_preservation_failed":
        raise SystemExit(2)


if __name__ == "__main__":
    main()

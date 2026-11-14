"""Result-blind, offline whole-day batch candidate export for #1698.

Produces a COMPLETE source-to-shadow intake manifest from two pinned fetched
Git snapshots. This module never publishes, dispatches, fetches race results,
edits main or changes a predictor. A generated candidate is locally frozen,
NOT independently received remotely and NOT a formal forward sample.

CLI emits JSONL only when explicitly requested. Its outputs MAY support a
separate, manually reviewed create-only research-branch upload.
"""
import argparse
import base64
from datetime import datetime, timedelta
import hashlib
import json
from pathlib import Path

from four_mode_position_sensitive_forward import JST, freeze_candidate
from position_sensitive_append_only_research import prepare_candidate
from position_sensitive_candidate_delivery_gap import (
    _git, audit_delivery_gap,
)

SCHEMA = "POSITION_SENSITIVE_BATCH_LOCAL_EXPORT_V1"
MIN_PRET12_UPLOAD_MARGIN_SECONDS = 600
MAX_BATCH = 600


def plan_batch(git, day, observed_now, min_margin_seconds=MIN_PRET12_UPLOAD_MARGIN_SECONDS):
    """Recompute every valid missing future candidate WITHOUT any remote write."""
    if (not callable(git) or type(observed_now) is not datetime
            or observed_now.utcoffset() != timedelta(hours=9)
            or type(min_margin_seconds) is not int
            or min_margin_seconds < MIN_PRET12_UPLOAD_MARGIN_SECONDS):
        raise ValueError("unsafe_batch_clock_or_margin")
    audited = audit_delivery_gap(git, day, observed_now)
    rows = audited["per_race_complete_saved_original_roster"]
    if len(rows) > MAX_BATCH:
        raise ValueError("too_many_candidate_opportunities")
    planned = []
    skipped = []
    candidates_original_sha = {}
    for row in rows:  # Already sorted by (deadline, race code).
        code = row["race_code"]
        if row["candidate_saved"]:
            skipped.append({"race_code": code, "reason": "candidate_already_saved"})
            continue
        status = row["status"]
        if status != "missing_candidate_local_window_still_open":
            skipped.append({"race_code": code, "reason": status})
            continue
        cutoff = datetime.fromisoformat(row["T_minus_12_jst"])
        if cutoff - observed_now <= timedelta(seconds=min_margin_seconds):
            skipped.append({"race_code": code, "reason": "insufficient_upload_margin"})
            continue
        original = git(
            "show", audited["main_git_snapshot_sha"] +
            ":four_mode_forecasts/" + code + ".json")
        if type(original) is not bytes or not 0 < len(original) <= 30000:
            raise ValueError("original_bytes_invalid_during_batch")
        if hashlib.sha256(original).hexdigest() != row["original_sha256"]:
            raise ValueError("original_changed_during_batch")
        snapshot = freeze_candidate(original, observed_now)
        candidate = (json.dumps(snapshot, ensure_ascii=False, sort_keys=True,
                                indent=2) + "\n").encode("utf-8")
        # Check the exact immutable byte content again just after freeze; the
        # adapter's own NOW > freeze precondition must remain strictly true.
        prepared = prepare_candidate(
            original, candidate, observed_now + timedelta(microseconds=1))
        if (prepared["candidate_sha256"] != hashlib.sha256(candidate).hexdigest()
                or prepared["original_sha256"] != row["original_sha256"]):
            raise ValueError("batch_candidate_hash_drift")
        planned.append({
            "race_code": code,
            "path": prepared["path"],
            "original_sha256": prepared["original_sha256"],
            "candidate_sha256": prepared["candidate_sha256"],
            "candidate_git_blob_sha1": prepared["candidate_git_blob_sha1"],
            "frozen_at_jst": snapshot["candidate_locally_frozen_at_jst"],
            "cutoff_T_minus_12_jst": cutoff.isoformat(),
            "candidate_text": candidate.decode("utf-8"),
        })
        candidates_original_sha[code] = row["original_sha256"]
    if len(planned) + len(skipped) != len(rows):
        raise ValueError("incomplete_source_to_candidate_batch_accounting")
    return {
        "schema": SCHEMA,
        "status": "locally_frozen_offline_candidates_NOT_remote_publications",
        "day_jst": day,
        "generated_at_jst": observed_now.isoformat(),
        "main_git_snapshot_sha": audited["main_git_snapshot_sha"],
        "ledger_git_snapshot_sha": audited["ledger_git_snapshot_sha"],
        "source_to_candidate_roster_sha256": audited["pinned_snapshot_roster_sha256"],
        "original_exact_replays": audited["eligible_original_exact_replays"],
        "previously_saved_candidates": audited["candidate_exact_original_replays"],
        "planned_local_only": len(planned),
        "skipped": skipped,
        "candidates": planned,
        "candidate_first_remote_receipts_independently_verified": 0,
        "formal_forward_eligible_races": 0,
        "official_T12_six_boats_120_odds_verified": False,
        "complete_capture_and_rescue_run_inventory_verified": False,
        "formal": False,
        "model_improvement_proven": False,
        "promotion_allowed": False,
        "production_changed": False,
        "warning": (
            "All candidate_text values are LOCAL pre-result research snapshots. "
            "This command performed NO remote publication. A local freeze "
            "clock/sha does NOT prove remote first receipt. All expired and "
            "already saved original records are counted but never generated."
        ),
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--day", default=None)
    p.add_argument("--output", type=Path)
    p.add_argument("--emit-candidate-lines", action="store_true",
                   help="Emit exact JSON candidate bytes for approved manual research-only use")
    args = p.parse_args()
    now = datetime.now(JST)
    day = args.day or now.strftime("%Y%m%d")
    plan = plan_batch(_git, day, now)
    # A manuscript or artifact may contain all exact candidate bytes. No
    # result fields or user credentials are included.
    payload = json.dumps(plan, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    if args.output:
        if args.output.is_symlink() or args.output.exists():
            raise ValueError("output_must_be_new_non_symlink")
        args.output.write_text(payload, encoding="utf-8")
    else:
        print(json.dumps({
            key: value for key, value in plan.items() if key != "candidates"
        }, sort_keys=True))
    if args.emit_candidate_lines:
        # Never assert publication: this is a local source-bound candidate
        # handoff for a *separate* create-only research-branch operation.
        for item in plan["candidates"]:
            print("POSITION_SENSITIVE_OFFLINE_CANDIDATE=" +
                  json.dumps(item, ensure_ascii=False, sort_keys=True))
    print("POSITION_SENSITIVE_BATCH_LOCAL_ONLY=" +
          json.dumps({"day": day,
                      "planned_local_only": plan["planned_local_only"],
                      "already_saved": plan["previously_saved_candidates"],
                      "total_original": plan["original_exact_replays"],
                      "formal": False,
                      "promotion_allowed": False}, sort_keys=True))


if __name__ == "__main__":
    main()

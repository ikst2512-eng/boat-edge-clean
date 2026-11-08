"""Read-only comparison of Nov5-8 published result CSV against CLEAN archives.

This is an observation of a NEWLY FETCHED public CSV snapshot. The CSV can
change after archived JSON was saved. Different whole-file SHA256 across these
snapshots is NOT evidence of a bad saved result, and current CSV content does
not reconstruct a missing historical snapshot. Does not write confirmed results,
rerank predictions, certify official T-12, or score prospective candidates.
"""
import argparse
import hashlib
import json
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.request import Request, urlopen

from collect_clean_results import BASE, build_records, source_gap_reasons
from four_mode_nov05_08_daily_reference_audit import ROOT, DAYS, audit

JST = timezone(timedelta(hours=9))
MAX_BYTES = 2_000_000
ALLOWED_GAP = timedelta(minutes=3)
CLASSES = (
    "not_in_published_csv", "invalid_or_unfinished_finish",
    "missing_source_timestamp", "invalid_source_timestamp",
    "future_source_timestamp", "duplicate_source_rows",
    "source_timestamp_not_post_deadline",
    "valid_published_row_not_yet_archived", "unclassified_pending_source",
)


def fetch_public_raw(day, *, opener=urlopen):
    """Use the original documented source URL; record the receipt clock."""
    url = BASE + f"{day[:4]}/{day[4:6]}/{day[6:]}.csv"
    with opener(Request(url, headers={"User-Agent": "BOAT-EDGE-CLEAN-RESEARCH-AUDIT/1.0"}), timeout=15) as response:
        if getattr(response, "status", None) != 200:
            raise ValueError("non_200_csv_source")
        raw = response.read(MAX_BYTES + 1)
    fetched_at = datetime.now(JST)
    if len(raw) > MAX_BYTES:
        raise ValueError("oversized_csv_source")
    return raw, fetched_at


def compare_one(day, root, pending, raw, fetched_at):
    if fetched_at.utcoffset() != timedelta(hours=9):
        raise ValueError("fetch_receipt_not_jst")
    # Fail closed on absent/malformed headers, duplicates and impossible times.
    valid = build_records(day, raw, fetched_at)
    gaps = source_gap_reasons(day, raw, pending, collected_at=fetched_at)
    digest = hashlib.sha256(raw).hexdigest()
    observed = dict.fromkeys(CLASSES, 0)
    pending_examples = {key: [] for key in CLASSES}
    for code in pending:
        reason = gaps[code]
        if reason == "row_present_requires_review":
            record = valid.get(code)
            if record is None:
                reason = "unclassified_pending_source"
            else:
                forecast = json.loads((root / "four_mode_forecasts" / (code + ".json")).read_text(encoding="utf-8"))
                deadline = datetime.fromisoformat(forecast["deadline_jst"])
                source_stamp = datetime.fromisoformat(record["confirmed_at_jst"])
                if deadline.tzinfo is None or source_stamp <= deadline:
                    reason = "source_timestamp_not_post_deadline"
                else:
                    reason = "valid_published_row_not_yet_archived"
        if reason not in observed:
            reason = "unclassified_pending_source"
        observed[reason] += 1
        pending_examples[reason].append(code)
    if sum(observed.values()) != len(pending):
        raise AssertionError("pending_partition_mismatch")
    # Rechecking latest publish *order* != replaying the stored historical CSV.
    saved_paths = sorted((root / "confirmed_results").glob(day + "*.json"))
    archived = Counter()
    conflicts = []
    for path in saved_paths:
        if path.stem not in valid:
            archived["no_valid_current_published_row"] += 1
            continue
        record = json.loads(path.read_text(encoding="utf-8"))
        current = valid[path.stem]
        if record.get("finish_order") != current["finish_order"]:
            archived["finish_order_conflicts_with_latest_source"] += 1
            conflicts.append(path.stem)
        else:
            archived["finish_order_matches_current_source"] += 1
        if record.get("source_sha256") == digest:
            archived["stored_digest_equals_current_snapshot"] += 1
        else:
            archived["historical_whole_file_digest_differs"] += 1
    return {
        "day": day, "source_url": BASE + f"{day[:4]}/{day[4:6]}/{day[6:]}.csv",
        "current_snapshot_sha256": digest,
        "current_snapshot_bytes": len(raw),
        "fetched_at_jst": fetched_at.isoformat(),
        "currently_valid_published_races": len(valid),
        "pending_saved_forecast_results": len(pending),
        "pending_classes": observed,
        "pending_codes_by_class": {k: v for k, v in pending_examples.items() if v},
        "existing_result_files_examined": len(saved_paths),
        "archived_to_current_comparison": dict(archived),
        "finish_conflict_race_codes": conflicts,
        "historical_snapshot_digest_match_is_required": False,
        "historical_snapshot_digest_drift_is_a_conflict": False,
        "old_raw_csv_snapshot_reconstructed": False,
    }


def observe(root=ROOT, days=DAYS, fetcher=fetch_public_raw):
    root = Path(root)
    reference = audit(root, days)
    by_day = {}
    errors = {}
    for day in days:
        pending = reference["by_day"][day]["pending_result_codes"]
        try:
            raw, fetched_at = fetcher(day)
            by_day[day] = compare_one(day, root, pending, raw, fetched_at)
        except (OSError, UnicodeError, ValueError, TypeError, KeyError, AssertionError) as exc:
            # Do not assert a 404, timeout, invalid CSV or future stamp is a success.
            errors[day] = {"type": type(exc).__name__, "reason": str(exc)[:200]}
    observed = len(by_day)
    status = ("ALL_SOURCE_SNAPSHOTS_OBSERVED" if observed == len(days) and not errors
              else "SOURCE_OBSERVATION_INCOMPLETE")
    conflicts = sum(len(x["finish_conflict_race_codes"]) for x in by_day.values())
    return {
        "schema": "FOUR_MODE_NOV05_08_POSTRACE_RAW_SOURCE_OBSERVATION_V1",
        "status": status,
        "days": list(days),
        "source_observation_days": observed,
        "source_errors": errors,
        "by_day": by_day,
        "archived_v2_forecasts": reference["totals"]["forecast_files"],
        "reference_results_already_saved": reference["totals"]["evaluated"],
        "unresolved_saved_result_files": reference["totals"]["pending_results"],
        "source_conflict_count": conflicts,
        "source_finish_order_conflicts_need_manual_review": conflicts > 0,
        "comparison_only_not_storage_repair": True,
        "raw_csv_new_snapshot_hash_is_not_historical_archive_hash": True,
        "upstream_is_not_official_boatrace_t12": True,
        "formal": False, "formally_eligible_races": 0,
        "prospective_candidate_pairs": 0, "model_promotion_allowed": False,
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", type=Path, default=ROOT)
    p.add_argument("--output", type=Path)
    a = p.parse_args()
    result = observe(a.root)
    if a.output:
        a.output.write_text(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print("FOUR_MODE_POSTRACE_SOURCE_OBSERVATION=" + json.dumps(result, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()

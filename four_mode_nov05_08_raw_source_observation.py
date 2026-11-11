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
from four_mode_nov05_08_daily_reference_audit import ROOT, DAYS, MODES, TOPS, BUDGETS, VERSION, audit
from four_mode_archive_api import archived_four_modes

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


def _saved_original_shadow_rank(root, code, winning):
    """Rank only immutable original tickets, not a newly generated candidate."""
    status, forecast = archived_four_modes(code, root)
    if status != 200 or forecast.get("model_version") != VERSION:
        raise ValueError("shadow_forecast_not_verified_v2")
    values = {}
    for mode in MODES:
        tickets = [x["combo"] for x in forecast["modes"][mode]["tickets"]]
        if len(tickets) != BUDGETS[mode] or len(set(tickets)) != len(tickets):
            raise ValueError("shadow_forecast_ticket_budget_or_duplicates")
        values[mode] = tickets.index(winning) + 1 if winning in tickets else None
    return values


def compare_one(day, root, pending, raw, fetched_at):
    if fetched_at.utcoffset() != timedelta(hours=9):
        raise ValueError("fetch_receipt_not_jst")
    # Fail closed on absent/malformed headers, duplicates and impossible times.
    valid = build_records(day, raw, fetched_at)
    gaps = source_gap_reasons(day, raw, pending, collected_at=fetched_at)
    digest = hashlib.sha256(raw).hexdigest()
    observed = dict.fromkeys(CLASSES, 0)
    pending_examples = {key: [] for key in CLASSES}
    shadow_hits = {mode: {f"top{n}": 0 for n in TOPS} for mode in MODES}
    public_shadow_codes = []
    shadow_full_covered = {mode: 0 for mode in MODES}
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
                    if (root / "confirmed_results" / (code + ".json")).exists():
                        raise ValueError("shadow_candidate_already_saved")
                    reason = "valid_published_row_not_yet_archived"
                    winning = "-".join(map(str, record["finish_order"]))
                    ranks = _saved_original_shadow_rank(root, code, winning)
                    public_shadow_codes.append(code)
                    for mode, rank in ranks.items():
                        shadow_full_covered[mode] += int(rank is not None)
                        for n in TOPS:
                            shadow_hits[mode][f"top{n}"] += int(rank is not None and rank <= n)
        if reason not in observed:
            reason = "unclassified_pending_source"
        observed[reason] += 1
        pending_examples[reason].append(code)
    if sum(observed.values()) != len(pending):
        raise AssertionError("pending_partition_mismatch")
    if len(public_shadow_codes) != observed["valid_published_row_not_yet_archived"]:
        raise AssertionError("public_shadow_race_membership_mismatch")
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
        "unarchived_published_shadow_only": {
            "race_count": len(public_shadow_codes),
            "race_codes": public_shadow_codes,
            "original_saved_top_hits": shadow_hits,
            "original_saved_full_list_covered": shadow_full_covered,
            "score_source": "new_public_csv_snapshot_not_clean_persisted_result",
            "counts_added_to_formal_or_saved_reference": False,
        },
        "existing_result_files_examined": len(saved_paths),
        "archived_to_current_comparison": dict(archived),
        "finish_conflict_race_codes": conflicts,
        "historical_snapshot_digest_match_is_required": False,
        "historical_snapshot_digest_drift_is_a_conflict": False,
        "old_raw_csv_snapshot_reconstructed": False,
    }


def observe(root=ROOT, days=DAYS, fetcher=fetch_public_raw, raw_dir=None):
    root = Path(root)
    reference = audit(root, days)
    by_day = {}
    errors = {}
    retained_source_codes = []
    for day in days:
        pending = reference["by_day"][day]["pending_result_codes"]
        try:
            raw, fetched_at = fetcher(day)
            row = compare_one(day, root, pending, raw, fetched_at)
            if raw_dir is not None:
                # CI artifact only: exact original public bytes, append-only per run.
                # Never write CLEAN confirmed_results or a model/candidate file.
                target_dir = Path(raw_dir)
                target_dir.mkdir(parents=True, exist_ok=True)
                with (target_dir / (day + ".csv")).open("xb") as output:
                    output.write(raw)
                if hashlib.sha256((target_dir / (day + ".csv")).read_bytes()).hexdigest() != row["current_snapshot_sha256"]:
                    raise ValueError("retained_public_source_byte_integrity_failed")
                retained_source_codes.append(day)
            by_day[day] = row
        except (OSError, UnicodeError, ValueError, TypeError, KeyError, AssertionError) as exc:
            # Do not assert a 404, timeout, invalid CSV or future stamp is a success.
            errors[day] = {"type": type(exc).__name__, "reason": str(exc)[:200]}
    observed = len(by_day)
    shadow_total = sum(row["unarchived_published_shadow_only"]["race_count"] for row in by_day.values())
    shadow_top_hits = {mode: {f"top{n}": sum(row["unarchived_published_shadow_only"]["original_saved_top_hits"][mode][f"top{n}"]
                                       for row in by_day.values()) for n in TOPS} for mode in MODES}
    shadow_codes = [code for row in by_day.values() for code in row["unarchived_published_shadow_only"]["race_codes"]]
    if len(set(shadow_codes)) != shadow_total:
        raise AssertionError("duplicate_public_shadow_race_code")
    if shadow_total > reference["totals"]["pending_results"]:
        raise AssertionError("public_shadow_exceeds_missing_saved_result_roster")
    # Current public-source-only completed results may supplement the descriptive
    # original-model historical view, but MUST NEVER change saved-only scores.
    # Any not-yet-published result remains an unknown outcome, not a loss.
    saved_valid = reference["totals"]["evaluated"]
    pending = reference["totals"]["pending_results"]
    historical_original_observed = saved_valid + shadow_total
    unknown_results = pending - shadow_total
    possible_total = historical_original_observed + unknown_results
    if possible_total != saved_valid + pending:
        raise AssertionError("historical_union_denominator_drift")
    historical_original = {}
    for mode in MODES:
        hits = {}
        fractions = {}
        bounds = {}
        for n in TOPS:
            key = f"top{n}"
            saved = reference["reference_overall"]["mode"][mode]["top_hits"][key]
            public = shadow_top_hits[mode][key]
            combined = saved + public
            if not (0 <= combined <= historical_original_observed):
                raise AssertionError("historical_union_hits_outside_observed:" + mode + ":" + key)
            hits[key] = {"saved_only": saved, "public_unarchived_only": public,
                         "combined_observed": combined}
            fractions[key] = (round(100 * combined / historical_original_observed, 2)
                              if historical_original_observed else None)
            bounds[key] = {
                "lower_if_all_unknown_miss_pct": (round(100 * combined / possible_total, 2)
                                                   if possible_total else None),
                "upper_if_all_unknown_hit_pct": (round(100 * (combined + unknown_results) / possible_total, 2)
                                                  if possible_total else None),
            }
        if not (hits["top1"]["combined_observed"] <= hits["top3"]["combined_observed"]
                <= hits["top5"]["combined_observed"] <= hits["top10"]["combined_observed"]):
            raise AssertionError("historical_union_topn_nonmonotone:" + mode)
        historical_original[mode] = {
            "top_hits_by_evidence_class": hits,
            "top_pct_of_currently_observed_outcomes_reference_only": fractions,
            "top_bounds_on_saved_archive_roster_not_confidence_intervals": bounds,
        }
    status = ("ALL_SOURCE_SNAPSHOTS_OBSERVED" if observed == len(days) and not errors
              else "SOURCE_OBSERVATION_INCOMPLETE")
    conflicts = sum(len(x["finish_conflict_race_codes"]) for x in by_day.values())
    source_observation_complete = observed == len(days) and not errors
    union_source_conflict_free = conflicts == 0
    union_state = ("COMPLETE_PUBLIC_SNAPSHOT_AND_CONFLICT_FREE" if
                   source_observation_complete and union_source_conflict_free else
                   "UNVERIFIED_INCOMPLETE_OR_CONFLICTING_SOURCE")
    return {
        "schema": "FOUR_MODE_NOV05_08_POSTRACE_RAW_SOURCE_OBSERVATION_V1",
        "status": status,
        "days": list(days),
        "source_observation_days": observed,
        "source_errors": errors,
        "public_raw_csv_retained_for_exact_replay": raw_dir is not None and len(retained_source_codes) == len(days),
        "public_raw_csv_retained_day_codes": retained_source_codes,
        "public_raw_csv_evidence_is_ci_artifact_only": raw_dir is not None,
        "by_day": by_day,
        "archived_v2_forecasts": reference["totals"]["forecast_files"],
        "reference_results_already_saved": reference["totals"]["evaluated"],
        "unresolved_saved_result_files": reference["totals"]["pending_results"],
        "source_conflict_count": conflicts,
        "historical_original_union_reference_only": {
            "status": union_state,
            "valid_saved_forecasts_with_persisted_or_public_result": historical_original_observed,
            "persisted_result_count": saved_valid,
            "newly_observed_public_unarchived_result_count": shadow_total,
            "unknown_or_unobserved_result_count": unknown_results,
            "eligible_archive_roster_without_exclusions": possible_total,
            "modes": historical_original,
            "not_official_and_not_prospective": True,
            "do_not_replace_persisted_denominator": True,
            "incomplete_or_conflicting_source_cannot_be_promoted": True,
        },
        "unarchived_published_shadow_only": {
            "races": shadow_total, "race_codes": shadow_codes,
            "original_saved_top_hits": shadow_top_hits,
            "denominator": shadow_total,
            "separate_from_persisted_reference": True,
            "persisted_reference_denominator": saved_valid,
            "eligible_for_formal_admission": False,
            "not_a_prospective_candidate_comparison": True,
        },
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
    p.add_argument("--source-raw-dir", type=Path, help="Retain original public CSV bytes in ephemeral CI artifact, not git/main")
    a = p.parse_args()
    result = observe(a.root, raw_dir=a.source_raw_dir)
    if a.output:
        a.output.write_text(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print("FOUR_MODE_POSTRACE_SOURCE_OBSERVATION=" + json.dumps(result, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()

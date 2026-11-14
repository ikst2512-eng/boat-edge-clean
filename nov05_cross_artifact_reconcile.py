"""Independently reconcile Nov 5 saved-hole shadow outcomes with 4-mode originals.

Both inputs are existing, read-only CI evidence from the *same current main*
worktree. This checks numerical and race-level consistency only. It does not
certify first remote receipt, completeness of scheduled collection, or ROI.
"""
import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

TOPS = ("top1", "top3", "top5", "top10")
CATEGORIES = {"covered", "winner_head_absent", "winner_second_pair_absent",
              "winner_third_absent"}
EXPECTED_DAY = "20261105"
EXPECTED_RUN = 41953950959
EXPECTED_N = 106


def _rows(value, key):
    rows = value.get(key)
    if type(rows) is not list or len(rows) != EXPECTED_N:
        raise ValueError("incomplete_cross_report_roster")
    by_code = {}
    for row in rows:
        if type(row) is not dict or type(row.get("race_code")) is not str:
            raise ValueError("untrusted_cross_report_row")
        code = row["race_code"]
        if (len(code) != 12 or not code.startswith(EXPECTED_DAY)
                or not code.isascii() or not code.isdecimal() or code in by_code):
            raise ValueError("invalid_or_duplicate_cross_race")
        by_code[code] = row
    return by_code


def reconcile(saved, snapshot):
    if (type(saved) is not dict or type(snapshot) is not dict
            or saved.get("schema") != "HOLE_NOV05_SAME_JOB_DIAGNOSTIC_V1"
            or saved.get("status") != "saved_candidate_result_comparison_research_only"
            or saved.get("capture_run_id") != EXPECTED_RUN
            or saved.get("published_frozen") != EXPECTED_N
            or saved.get("pre_result_consistent") != EXPECTED_N
            or saved.get("confirmed_result_content_scored") != EXPECTED_N
            or saved.get("pending_result_codes") != []
            or saved.get("invalid_result_evidence") != []
            or saved.get("formal") is not False
            or saved.get("model_improvement_proven") is not False
            or saved.get("pre_result_roster_committed_before_results") is not False
            or type(saved.get("pre_result_ticket_roster_sha256")) is not str
            or len(saved["pre_result_ticket_roster_sha256"]) != 64
            or snapshot.get("schema") != "FOUR_MODE_NOV05_MAIN_SNAPSHOT_HISTORICAL_AUDIT_V1"
            or snapshot.get("status") != "main_snapshot_research_comparable"
            or snapshot.get("day_jst") != EXPECTED_DAY
            or snapshot.get("four_mode_original_files") != EXPECTED_N
            or snapshot.get("four_mode_result_filename_intersection") != EXPECTED_N
            or snapshot.get("result_content_comparable_count") != EXPECTED_N
            or snapshot.get("untrusted_or_invalid_result_rows") != []
            or snapshot.get("forecasts_without_result_filename") != []
            or snapshot.get("formal") is not False
            or snapshot.get("prospective_accuracy_verified") is not False):
        raise ValueError("cross_report_not_fully_research_comparable")
    stored = _rows(saved, "per_race_result_diagnostic")
    calculated = _rows(snapshot, "historical_per_race")
    if set(stored) != set(calculated):
        raise ValueError("different_saved_and_snapshot_races")
    if (type(snapshot.get("intersection_race_codes")) is not list
            or sorted(snapshot["intersection_race_codes"]) != sorted(stored)):
        raise ValueError("cross_report_intersection_mismatch")
    rank_miss = Counter()
    gained_by_reason = Counter()
    lost_by_reason = Counter()
    totals = {key: Counter() for key in TOPS}
    per_race = []
    for code in sorted(stored):
        original = stored[code]
        other = calculated[code]
        modes = other.get("modes")
        if (original.get("status") != "matched_saved_shadow_and_remote_observation_research_only"
                or original.get("formal") is not False
                or original.get("independent_first_receipt_verified") is not False
                or original.get("complete_capture_run_inventory_verified") is not False
                or original.get("official_six_boat_beforeinfo_verified") is not False
                or type(modes) is not dict or set(modes) !=
                {"narrow", "hit", "balance", "hole"}
                or original.get("winning_ticket") != other.get("winning_ticket")):
            raise ValueError("race_provenance_or_result_mismatch")
        miss = modes["hole"].get("coverage_diagnostic")
        if miss not in CATEGORIES:
            raise ValueError("untrusted_hole_miss_reason")
        rank_miss[miss] += 1
        verdict = {"race_code": code, "hole_miss_reason": miss, "topn": {}}
        for key in TOPS:
            a = original.get("topn", {}).get(key)
            if (type(a) is not dict
                    or any(type(a.get(k)) is not bool
                           for k in ("baseline", "candidate", "gained", "lost"))):
                raise ValueError("untrusted_paired_bit")
            old, new = a["baseline"], a["candidate"]
            if (old != (modes["hole"].get(key) is True)
                    or a["gained"] != (new and not old)
                    or a["lost"] != (old and not new)):
                raise ValueError("saved_shadow_vs_four_mode_disagrees")
            for item, flag in (("baseline", old), ("candidate", new),
                               ("gained", a["gained"]), ("lost", a["lost"])):
                totals[key][item] += int(flag)
            verdict["topn"][key] = a
        if verdict["topn"]["top10"]["gained"]:
            gained_by_reason[miss] += 1
        if verdict["topn"]["top10"]["lost"]:
            lost_by_reason[miss] += 1
        per_race.append(verdict)
    for key in TOPS:
        row = saved.get("paired_historical_topn", {}).get(key)
        if type(row) is not dict:
            raise ValueError("missing_saved_topn")
        for tag, field in (("baseline", "baseline_hits"),
                           ("candidate", "candidate_hits"),
                           ("gained", "gained"), ("lost", "lost")):
            if totals[key][tag] != row.get(field):
                raise ValueError("saved_total_disagrees_with_race_evidence")
        if (totals[key]["baseline"] !=
                snapshot.get("historical_topn_hits", {}).get("hole", {}).get(key)
                or totals[key]["candidate"] - totals[key]["baseline"]
                   != totals[key]["gained"] - totals[key]["lost"]):
            raise ValueError("snapshot_total_or_gain_loss_mismatch")
    misses = snapshot.get("historical_coverage_miss_reasons", {}).get("hole")
    if type(misses) is not dict or dict(rank_miss) != misses:
        raise ValueError("snapshot_hole_miss_partition_mismatch")
    digest = hashlib.sha256(
        ("\n".join(sorted(stored)) + "\n").encode("ascii")).hexdigest()
    if digest != snapshot["intersection_sha256"]:
        raise ValueError("cross_report_cohort_digest_mismatch")
    return {
        "schema": "HOLE_NOV05_SAVED_VS_MAIN_CROSS_AUDIT_V1",
        "status": "cross_source_consistent_research_only",
        "examined_main_sha": snapshot["examined_main_sha"],
        "capture_run_id": EXPECTED_RUN,
        "race_day_jst": EXPECTED_DAY,
        "common_result_validated_races": EXPECTED_N,
        "same_race_roster_sha256": digest,
        "captured_pre_result_ticket_sha256": saved["pre_result_ticket_roster_sha256"],
        "per_race_source_and_winner_equal": True,
        "miss_reason_counts": dict(rank_miss),
        "top10_gained_by_prior_miss_reason": dict(gained_by_reason),
        "top10_lost_by_prior_miss_reason": dict(lost_by_reason),
        "topn": {key: {**dict(counts),
                       "net": counts["candidate"] - counts["baseline"],
                       "denominator": EXPECTED_N}
                 for key, counts in totals.items()},
        "per_race": per_race,
        "formal": False,
        "independent_first_remote_receipt_verified": False,
        "capture_run_inventory_exhaustive": False,
        "complete_forward_300_enrollment_verified": False,
        "model_improvement_proven": False,
        "production_forecast_changed": False,
        "warning": ("Read-only consistency between frozen same-job candidate evidence "
                    "and current-main original forecast/result files. No independent "
                    "first remote receipt, complete source coverage or trial efficacy.")
    }


def read(path):
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 5_000_000:
        raise ValueError("untrusted_cross_input_file")
    return json.loads(path.read_text(encoding="utf-8"))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--saved", default="nov05_saved_hole_shadow_audit.json")
    p.add_argument("--snapshot", default="nov05_four_mode_snapshot_audit.json")
    p.add_argument("--output", default="nov05_cross_artifact_reconcile.json")
    args = p.parse_args()
    report = reconcile(read(args.saved), read(args.snapshot))
    Path(args.output).write_text(
        json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8")
    print("NOV05_CROSS_ARTIFACT=" + json.dumps({
        k: report[k] for k in
        ("status", "examined_main_sha", "common_result_validated_races",
         "miss_reason_counts", "top10_gained_by_prior_miss_reason",
         "top10_lost_by_prior_miss_reason", "topn", "formal")
    }, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()

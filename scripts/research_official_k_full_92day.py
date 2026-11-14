#!/usr/bin/env python3
"""Research-only official K primary-source audit of the full frozen 92-day period.

Read-only official archives and SHA-frozen secondary postrace CSVs.
Records incomplete/mismatching days without silently excluding records.
Does not prove BOAT RACE's rolling 3-month statistical denominator or T-12 data.
"""
from __future__ import annotations

import argparse
import collections
import csv
import datetime as dt
import hashlib
import json
from pathlib import Path

if __package__:
    from .research_official_k_receipt import get_archive
    from .research_official_k_one_day_compare import (
        RACE, compare, git_blob_sha, parse_k, unpack_lha)
else:
    from research_official_k_receipt import get_archive
    from research_official_k_one_day_compare import (
        RACE, compare, git_blob_sha, parse_k, unpack_lha)

START, END = dt.date(2026, 8, 1), dt.date(2026, 10, 31)
STATUS = {
    "reconciled": "all_primary_and_secondary_codes_and_common_fields_equal",
    "primary_extra": "primary_codes_missing_from_secondary_but_common_fields_equal",
    "secondary_extra": "secondary_codes_missing_from_primary_not_claimed_equal",
    "field_mismatch": "common_field_differences_present",
    "failed_closed": "missing_or_invalid_input_no_success_claim",
}


def validate_evidence(evidence: dict) -> list[dict]:
    sources = evidence.get("sources")
    if evidence.get("period") != "2026-08-01/2026-10-31" or not isinstance(sources, list):
        raise ValueError("unfrozen_or_missing_manifest")
    expected = [(START + dt.timedelta(days=n)).isoformat()
                for n in range((END - START).days + 1)]
    if [s.get("day") for s in sources] != expected:
        raise ValueError("frozen_days_missing_duplicate_or_unordered")
    if len(sources) != 92 or sum(s["rows"] for s in sources) != 14109:
        raise ValueError("original_study_universe_not_14109")
    return sources


def reconcile_one(source: dict, secondary_dir: Path, raw_dir: Path) -> dict:
    date = dt.date.fromisoformat(source["day"])
    day = date.strftime("%Y%m%d")
    csv_path = secondary_dir / ("secondary_" + day + ".csv")
    if not csv_path.is_file() or csv_path.is_symlink():
        raise FileNotFoundError("missing_or_symlink_secondary:" + day)
    source_raw = csv_path.read_bytes()
    if git_blob_sha(source_raw) != source["sha"]:
        raise ValueError("frozen_git_blob_mismatch:" + day)
    rows = list(csv.DictReader(source_raw.decode("utf-8-sig").splitlines()))
    by_code = {r.get("レースコード", ""): r for r in rows}
    if len(rows) != source["rows"] or len(by_code) != len(rows) or not rows:
        raise ValueError("secondary_count_duplicate_or_empty:" + day)
    if any(not code.startswith(day) for code in by_code):
        raise ValueError("secondary_day_code_mismatch:" + day)
    receipt = get_archive(date, raw_dir)
    raw = (raw_dir / receipt["filename"]).read_bytes()
    if hashlib.sha256(raw).hexdigest() != receipt["sha256"]:
        raise ValueError("official_receipt_sha_mismatch:" + day)
    unpacked = unpack_lha(raw, day=day)
    text = unpacked.decode("cp932")
    headers = sum(bool(RACE.match(line)) for line in text.splitlines())
    official = parse_k(text, day=day, expected_races=headers, allow_unsettled=True)
    primary_only = sorted(set(official) - set(by_code))
    secondary_only = sorted(set(by_code) - set(official))
    if secondary_only:
        # Existing compare() requires equality of the frozen secondary universe.
        # Keep the original file unchanged and refuse falsely positive matching.
        return {
            "day": day, "status": "secondary_extra",
            "official_K_races": len(official), "secondary_races": len(rows),
            "primary_only_race_codes": primary_only,
            "secondary_only_race_codes": secondary_only,
            "official_K_sha256": receipt["sha256"],
            "decoded_sha256": hashlib.sha256(unpacked).hexdigest(),
            "secondary_git_blob_sha": source["sha"],
            "fully_compared_races": 0, "field_discrepancies": None,
        }
    common_official = {code: race for code, race in official.items()
                       if code in by_code}
    result = compare(common_official, source_raw, source["sha"], day=day)
    field_discrepancies = result["field_discrepancy_count"]
    status = ("field_mismatch" if field_discrepancies else
              "primary_extra" if primary_only else "reconciled")
    return {
        "day": day, "status": status,
        "official_K_races": len(official), "secondary_races": len(rows),
        "primary_only_race_codes": primary_only,
        "secondary_only_race_codes": secondary_only,
        "official_K_sha256": receipt["sha256"],
        "decoded_sha256": hashlib.sha256(unpacked).hexdigest(),
        "secondary_git_blob_sha": source["sha"],
        "fully_compared_races": result["official_races"],
        "field_discrepancies": field_discrepancies,
        "field_mismatch_details": result["field_discrepancies"][:200],
        "field_match_counts": result["field_match_counts"],
        "not_all_course_or_st_comparable": result["course_not_fully_comparable_race_codes"],
        "official_special_status_counts": result["official_special_status_counts"],
    }


def run(secondary_dir: Path, raw_dir: Path, frozen_evidence: Path) -> dict:
    sources = validate_evidence(json.loads(frozen_evidence.read_text(encoding="utf-8")))
    output = []
    for source in sources:
        day = source["day"].replace("-", "")
        try:
            result = reconcile_one(source, secondary_dir, raw_dir)
        except Exception as exc:
            result = {
                "day": day, "status": "failed_closed",
                "error_type": type(exc).__name__, "error_detail": str(exc)[:300],
                "fully_compared_races": 0,
            }
        output.append(result)
        print(json.dumps({
            "day": day, "status": result["status"],
            "compared_races": result["fully_compared_races"],
            "field_discrepancies": result.get("field_discrepancies"),
        }, ensure_ascii=False), flush=True)
    counted = collections.Counter(r["status"] for r in output)
    counts = {
        "fully_matched_days": counted["reconciled"],
        "official_extra_days": counted["primary_extra"],
        "secondary_extra_days": counted["secondary_extra"],
        "field_mismatch_days": counted["field_mismatch"],
        "failed_days": counted["failed_closed"],
        "official_K_days_verified_decoded": len(output) - counted["failed_closed"],
        "total_common_races_field_checked": sum(
            r.get("fully_compared_races", 0) for r in output),
        "official_only_race_codes": sorted(
            code for r in output for code in r.get("primary_only_race_codes", [])),
        "secondary_only_race_codes": sorted(
            code for r in output for code in r.get("secondary_only_race_codes", [])),
        "field_discrepancy_count": sum(
            r.get("field_discrepancies") or 0 for r in output),
    }
    return {
        "schema": "BOAT_EDGE_OFFICIAL_K_FROZEN_92_DAY_PRIMARY_COMPARISON_V1",
        "classification": "research_postrace_primary_comparison_not_T12",
        "study_period": "2026-08-01/2026-10-31",
        "days_attempted": 92,
        "official_source_day_complete_match": counted["reconciled"] == 92,
        "secondary_source_is_not_official_primary": True,
        "official_rolling_course_statistic_denominator_verified": False,
        "forecast_improvement_proved": False,
        "authorized_for_production": False,
        **counts,
        "results": output,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--secondary-dir", required=True, type=Path)
    ap.add_argument("--raw-dir", required=True, type=Path)
    ap.add_argument("--frozen-evidence", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    args = ap.parse_args()
    result = run(args.secondary_dir, args.raw_dir, args.frozen_evidence)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                        encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k in (
        "days_attempted", "fully_matched_days", "official_extra_days",
        "secondary_extra_days", "field_mismatch_days", "failed_days",
        "total_common_races_field_checked", "field_discrepancy_count",
        "official_rolling_course_statistic_denominator_verified",
    )}, ensure_ascii=False))
    if (result["failed_days"] or result["field_mismatch_days"]
            or result["secondary_extra_days"]):
        raise SystemExit(1)


if __name__ == "__main__":
    main()

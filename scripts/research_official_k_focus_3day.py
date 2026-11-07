#!/usr/bin/env python3
"""Research-only independent official K vs frozen CSV reconciliation (3 August dates).

Never import post-race data into prediction, T-12, model, or live scoring.
Attempts all fixed dates; no success claim for any failed or incomplete day.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from pathlib import Path

if __package__:
    from .research_official_k_receipt import get_archive
    from .research_official_k_one_day_compare import (
        compare, git_blob_sha, parse_k, unpack_lha,
    )
else:
    from research_official_k_receipt import get_archive
    from research_official_k_one_day_compare import (
        compare, git_blob_sha, parse_k, unpack_lha,
    )

TARGETS = {
    "20260802": [("202608020609", "転")],
    "20260821": [("202608212302", "転")],
    "20260826": [("202608260307", "F"), ("202608261704", "転")],
}


# Demonstrated original-K races absent from the frozen BoatraceCSV secondary source.
# Keep them as omissions, never delete their official records or alter study N.
OFFICIAL_ONLY_RACES = {
    "20261012": {"202610121912"},  # Shimonoseki 12R
    "20261018": {"202610181912"},  # Shimonoseki 12R
    "20261023": {"202610232012"},  # Wakamatsu 12R
}

def status_compatible(page_symbol: str, k_code: str) -> bool:
    """Broad category only: page is accident type; K is liability/status code.

    This must not be used to infer that K itself confirms 'capsize' etc.
    """
    if page_symbol == "F":
        return k_code == "F"
    if page_symbol in {"転", "落", "沈", "エ"}:
        return k_code in {"S0", "S1"}
    if page_symbol == "妨":
        return k_code == "S2"
    return False

def expected_blob_sha(day: str, frozen: dict) -> str:
    if frozen.get("period") != "2026-08-01/2026-10-31":
        raise ValueError("frozen_period_wrong")
    sources = frozen.get("sources", [])
    if len(sources) != 92 or len(set(x["day"] for x in sources)) != 92:
        raise ValueError("frozen_days_not_92")
    match = [x for x in sources if x["day"] == f"{day[:4]}-{day[4:6]}-{day[6:]}"]
    if len(match) != 1:
        raise ValueError("frozen_day_not_unique:" + day)
    return match[0]["sha"]

def reconcile_day(day: str, source_dir: Path, raw_dir: Path, frozen: dict, targets: dict | None = None) -> dict:
    import datetime as dt
    focus = TARGETS if targets is None else targets
    if day not in focus:
        raise ValueError("day_outside_locked_test_cohort")
    p = source_dir / f"secondary_{day}.csv"
    if p.is_symlink() or not p.is_file():
        raise FileNotFoundError("missing_sha_verified_secondary_day:" + str(p))
    secondary = p.read_bytes()
    expected = expected_blob_sha(day, frozen)
    if git_blob_sha(secondary) != expected:
        raise ValueError("secondary_frozen_git_sha_mismatch:" + day)
    rows = list(csv.DictReader(secondary.decode("utf-8-sig").splitlines()))
    by_code = {x.get("レースコード"): x for x in rows}
    if len(by_code) != len(rows) or len(rows) < 1:
        raise ValueError("secondary_duplicate_or_empty:" + day)
    from_date = dt.date(int(day[:4]), int(day[4:6]), int(day[6:]))
    receipt = get_archive(from_date, raw_dir)
    archive = raw_dir / receipt["filename"]
    raw = archive.read_bytes()
    sha = hashlib.sha256(raw).hexdigest()
    if sha != receipt["sha256"]:
        raise ValueError("official_archive_sha_mismatch:" + day)
    decoded = unpack_lha(raw, day=day)
    anticipated_official_only = OFFICIAL_ONLY_RACES.get(day, set())
    official = parse_k(
        decoded.decode("cp932"), day=day,
        expected_races=len(rows) + len(anticipated_official_only),
    )
    unexpected = set(official) - set(by_code)
    missing_from_primary = set(by_code) - set(official)
    if unexpected != anticipated_official_only or missing_from_primary:
        raise ValueError(
            "unexplained_source_universe_mismatch:" + day +
            ":official_only=" + repr(sorted(unexpected)) +
            ":secondary_only=" + repr(sorted(missing_from_primary))
        )
    matched_official = {code: race for code, race in official.items() if code in by_code}
    compare_report = compare(
        matched_official, secondary, expected_secondary_sha=expected, day=day,
    )
    compare_report["official_archive_races_total"] = len(official)
    compare_report["official_only_race_codes_preserved"] = sorted(unexpected)
    compare_report["full_official_vs_secondary_race_universe_equal"] = not unexpected
    checks = []
    for code, expected_status in focus[day]:
        if code not in official or code not in by_code:
            raise ValueError("focus_race_missing:" + code)
        first = (by_code[code].get("1コース_艇番") or "").strip()
        matching = [e for e in official[code]["entries"] if str(e["boat"]) == first]
        if len(matching) != 1:
            raise ValueError("focus_first_boat_not_unique:" + code)
        actual_status = matching[0]["status"]
        checks.append({
            "race_code": code, "first_course_boat": first,
            "official_K_status": actual_status,
            "official_page_accident_symbol": expected_status,
            "broad_status_compatible": status_compatible(expected_status, actual_status),
            "K_encodes_exact_page_accident_type": False,
            "K_liability_class": (
                "non_racer_fault" if actual_status == "S0" else
                "racer_fault" if actual_status in {"S1", "S2"} else
                "start_fault_or_other"
            ),
        })
    complete = (compare_report["field_discrepancy_count"] == 0
                and all(x["broad_status_compatible"] for x in checks))
    status = (
        "focus_reconciled_secondary_universe_gap"
        if complete and anticipated_official_only else
        "reconciled" if complete else
        "unreconciled_differences"
    )
    return {
        "day": day, "status": status,
        "official_K_receipt": receipt, "secondary_git_blob_sha": expected,
        "official_K_decoded_sha256": hashlib.sha256(decoded).hexdigest(),
        "comparison": compare_report, "focus": checks,
        "full_92days_officially_reconciled": False,
        "official_three_month_course_rate_denominator_verified": False,
    }

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", required=True, type=Path)
    parser.add_argument("--frozen-evidence", required=True, type=Path)
    parser.add_argument("--raw-dir", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    frozen = json.loads(args.frozen_evidence.read_text(encoding="utf-8"))
    results = []
    for day in TARGETS:
        try:
            result = reconcile_day(day, args.source_dir, args.raw_dir, frozen)
        except Exception as exc:
            result = {
                "day": day, "status": "failed_closed",
                "failure_type": type(exc).__name__,
                "failure_reason": str(exc)[:300],
                "full_92days_officially_reconciled": False,
                "official_three_month_course_rate_denominator_verified": False,
            }
        results.append(result)
    report = {
        "schema": "OFFICIAL_K_FOCUS_3DAY_PRIMARY_RECONCILIATION_V1",
        "classification": "postrace_research_only_not_T12",
        "fixed_days": sorted(TARGETS),
        "days_attempted": len(TARGETS),
        "days_reconciled": sum(r["status"] == "reconciled" for r in results),
        "days_failed_or_incomplete": sum(r["status"] != "reconciled" for r in results),
        "primary_92day_reconciliation_complete": False,
        "official_venue_statistical_denominator_verified": False,
        "candidate_model_or_wind_factor_adopted": False,
        "results": results,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                        encoding="utf-8")
    print(json.dumps({
        "attempted": report["days_attempted"],
        "reconciled": report["days_reconciled"],
        "failed_or_incomplete": report["days_failed_or_incomplete"],
        "focus_verified": sum(
            len(r.get("focus", [])) for r in results if r["status"] == "reconciled"
        ),
        "out": str(args.out),
    }, ensure_ascii=False))
    if report["days_failed_or_incomplete"]:
        raise SystemExit(1)

if __name__ == "__main__":
    main()

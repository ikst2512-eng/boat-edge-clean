#!/usr/bin/env python3
"""Read-only 140-race official-K / secondary omission profile for frozen 92 days.

A postrace data-quality artifact, never a T-12 feature or wind coefficient.
"""
from __future__ import annotations

import argparse
import collections
import datetime as dt
import hashlib
import json
from pathlib import Path

if __package__:
    from .research_official_k_one_day_compare import parse_k, unpack_lha
else:
    from research_official_k_one_day_compare import parse_k, unpack_lha

FIRST = dt.date(2026, 8, 1)
LAST = dt.date(2026, 10, 31)


def profile_races(races: list[dict]) -> dict:
    seen, venues, bands, winners, status, by_date = (
        set(), collections.Counter(), collections.Counter(),
        collections.Counter(), collections.Counter(), collections.Counter()
    )
    records = []
    for r in races:
        code = r["race_code"]
        if len(code) != 12 or not code.isdigit():
            raise ValueError("invalid_primary_race_code:" + str(code))
        day = dt.date.fromisoformat(code[:4] + "-" + code[4:6] + "-" + code[6:8])
        if not FIRST <= day <= LAST or code in seen:
            raise ValueError("duplicate_or_out_of_period_race:" + code)
        seen.add(code)
        wind = r["wind_m"]
        if type(wind) is not int or not 0 <= wind <= 30:
            raise ValueError("invalid_primary_postrace_wind:" + code)
        entries = r["entries"]
        if len(entries) != 6 or {x["boat"] for x in entries} != set(range(1, 7)):
            raise ValueError("missing_or_duplicate_boat:" + code)
        first = [x for x in entries if x["course"] == 1]
        if len(first) != 1:
            raise ValueError("actual_first_course_missing_or_ambiguous:" + code)
        winning = [x for x in entries if x["status"] == "01"]
        if len(winning) > 1:
            raise ValueError("multiple_primary_winners:" + code)
        if not winning and not r.get("unsettled", False):
            raise ValueError("no_winner_without_primary_unsettled:" + code)
        band = "0-2m" if wind <= 2 else "3-4m" if wind <= 4 else "5m+"
        outcome = ("none" if not winning else
                   "1C" if winning[0]["boat"] == first[0]["boat"] else "non1C")
        venue, date = code[8:10], code[:8]
        venues[venue] += 1
        bands[band] += 1
        winners[outcome] += 1
        status[first[0]["status"]] += 1
        by_date[date] += 1
        records.append({
            "race_code": code, "venue": venue,
            "official_result_wind_m": wind, "postrace_wind_band": band,
            "actual_first_course_boat": first[0]["boat"],
            "actual_first_course_status": first[0]["status"],
            "first_course_outcome": outcome,
            "official_K_unsettled": bool(r.get("unsettled", False)),
        })
    return {
        "missing_races": len(records), "by_venue": dict(sorted(venues.items())),
        "by_postrace_wind_band": {b: bands[b] for b in ("0-2m", "3-4m", "5m+")},
        "actual_first_course_result_counts": {k: winners[k] for k in ("1C", "non1C", "none")},
        "actual_first_course_status_counts": dict(sorted(status.items())),
        "by_date": dict(sorted(by_date.items())),
        "records": sorted(records, key=lambda r: r["race_code"]),
    }


def run(report_file: Path, k_dir: Path) -> dict:
    report = json.loads(report_file.read_text(encoding="utf-8"))
    if (report.get("schema") != "BOAT_EDGE_OFFICIAL_K_FROZEN_92_DAY_PRIMARY_COMPARISON_V1"
            or report.get("study_period") != "2026-08-01/2026-10-31"
            or report.get("days_attempted") != 92
            or report.get("failed_days") != 0
            or report.get("secondary_extra_days") != 0):
        raise ValueError("invalid_or_incomplete_frozen_primary_reconciliation")
    dates = {x["day"]: x for x in report["results"]}
    expected_days = {(FIRST + dt.timedelta(days=n)).strftime("%Y%m%d")
                     for n in range((LAST - FIRST).days + 1)}
    if set(dates) != expected_days or len(report["results"]) != 92:
        raise ValueError("missing_or_duplicate_reconciliation_day")
    codes = report.get("official_only_race_codes", [])
    if len(codes) != len(set(codes)) or len(codes) != 140:
        raise ValueError("official_missing_140_cohort_changed")
    by_date = collections.defaultdict(list)
    for code in codes:
        if len(code) != 12 or not code.isdigit() or code[:8] not in dates:
            raise ValueError("invalid_official_only_code:" + str(code))
        by_date[code[:8]].append(code)
    missing, manifest = [], []
    for date, group in sorted(by_date.items()):
        entry = dates[date]
        if (entry.get("status") != "primary_extra"
                or sorted(entry.get("primary_only_race_codes", [])) != sorted(group)):
            raise ValueError("daily_primary_missing_set_mismatch:" + date)
        source = k_dir / ("k" + date[2:] + ".lzh")
        if source.is_symlink() or not source.is_file():
            raise FileNotFoundError("missing_or_symlink_official_K:" + date)
        raw = source.read_bytes()
        sha = hashlib.sha256(raw).hexdigest()
        if sha != entry["official_K_sha256"]:
            raise ValueError("official_K_receipt_SHA_mismatch:" + date)
        decoded = unpack_lha(raw, day=date)
        officials = parse_k(decoded.decode("cp932"), day=date,
                            expected_races=entry["official_K_races"], allow_unsettled=True)
        for code in group:
            record = officials.get(code)
            if record is None:
                raise ValueError("expected_missing_race_not_in_K:" + code)
            missing.append({**record, "race_code": code})
        manifest.append({
            "day": date, "archive_sha256": sha,
            "official_races": len(officials), "secondary_missing_races": len(group)
        })
    summary = profile_races(missing)
    if (summary["missing_races"] != 140
            or summary["by_date"].get("20260829") != 121
            or summary["actual_first_course_result_counts"]["none"] != 2):
        raise ValueError("expected_primary_gap_breakdown_changed")
    return {
        "schema": "BOAT_EDGE_K_PRIMARY_ONLY_140_POSTRACE_PROFILE_V1",
        "classification": "postrace_primary_data_quality_only",
        "frozen_period": report["study_period"], "primary_source_day_count": 92,
        "source_days_with_missing_secondary_races": len(by_date),
        "official_K_selected_source_receipts": manifest,
        "official_three_month_denominator_rule_certified": False,
        "wind_factor_or_model_training_authorized": False, "T12_eligible": False,
        **summary,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--official-comparison", required=True, type=Path)
    ap.add_argument("--official-k-dir", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    a = ap.parse_args()
    result = run(a.official_comparison, a.official_k_dir)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        k: v for k, v in result.items() if k in (
            "missing_races", "source_days_with_missing_secondary_races",
            "by_postrace_wind_band", "actual_first_course_result_counts",
            "wind_factor_or_model_training_authorized")
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()

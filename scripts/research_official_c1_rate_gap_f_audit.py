#!/usr/bin/env python3
"""Read-only audit: how much can first-course F explain official rate gaps?

Input: local, complete 2026-08-01..10-31 BoatraceCSV result files.
Compares distinct, valid 1C starts with the frozen official 24-venue baseline.
No network, no forecast input, no model training and no T-12 certification.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
from collections import Counter
from pathlib import Path

from venue_environment_observational import parse_result

FOCUS = ("03", "06", "17", "23")
START = dt.date(2026, 8, 1)
END = dt.date(2026, 10, 31)


def audit(root: Path, baseline: Path):
    with baseline.open(encoding="utf-8-sig", newline="") as f:
        base = list(csv.DictReader(f))
    by_code = {x["venue_code"]: x for x in base}
    if len(base) != 24 or len(by_code) != 24:
        raise ValueError("baseline_requires_exactly_24_venues")
    for code in FOCUS:
        item = by_code[code]
        if item["start_date"] != str(START) or item["end_date"] != str(END):
            raise ValueError(f"baseline_period_mismatch_{code}")
    records = {}
    counters = {code: Counter() for code in FOCUS}
    manifest = []
    for offset in range((END - START).days + 1):
        day = START + dt.timedelta(days=offset)
        p = root / f"data/results/realtime/{day:%Y}/{day:%m}/{day:%d}.csv"
        if p.is_symlink() or not p.is_file():
            raise FileNotFoundError(f"missing_or_symlink_source:{p}")
        raw = p.read_bytes()
        if not raw:
            raise ValueError(f"empty_source:{p}")
        rows_today = 0
        with p.open(encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            required = {"レースコード", "1着_艇番", "1コース_F", "1コース_スタートタイミング"}
            required.update(f"{i}コース_艇番" for i in range(1, 7))
            required.update(f"{i}着_艇番" for i in range(1, 7))
            if not required.issubset(reader.fieldnames or ()):
                raise ValueError(f"missing_result_columns:{p}")
            for row in reader:
                rows_today += 1
                key = (row.get("レースコード") or "").strip()
                if not key.startswith(day.strftime("%Y%m%d")):
                    raise ValueError(f"date_mismatch:{day}:{key}")
                code = key[8:10]
                if code not in FOCUS:
                    continue
                if key in records:
                    raise ValueError(f"duplicate_race_code:{key}")
                records[key] = True
                c = counters[code]
                c["raw"] += 1
                try:
                    parsed = parse_result(row)
                except ValueError:
                    c["excluded_from_earlier_wind_study"] += 1
                    continue
                c["eligible"] += 1
                c["first_course_wins"] += int(parsed["winner_course"] == 1)
                flying = (row.get("1コース_F") or "").strip() == "F"
                c["first_course_F_mark"] += int(flying)
                first_course_boat = (row.get("1コース_艇番") or "").strip()
                ranked = any((row.get(f"{i}着_艇番") or "").strip() == first_course_boat
                             for i in range(1, 7))
                c["first_course_ranked"] += int(ranked)
                c["first_course_unranked_nonF"] += int(not ranked and not flying)
                c["first_course_ranked_F_conflicts"] += int(ranked and flying)
                st = (row.get("1コース_スタートタイミング") or "").strip()
                try:
                    negative = float(st) < 0
                except ValueError:
                    negative = False
                c["first_course_negative_ST"] += int(negative)
                if flying != negative:
                    c["F_mark_ST_sign_conflict"] += 1
        manifest.append({"date": str(day), "source_git_snapshot_unverified": True,
                         "sha256": hashlib.sha256(raw).hexdigest(),
                         "raw_rows": rows_today})
    result = []
    for code in FOCUS:
        c = counters[code]
        n, wins, f = c["eligible"], c["first_course_wins"], c["first_course_F_mark"]
        if n == 0 or f >= n:
            raise ValueError(f"invalid_denominator_{code}")
        ranked = c["first_course_ranked"]
        if ranked == 0 or ranked > n or wins > ranked:
            raise ValueError(f"invalid_ranked_denominator_{code}")
        official = float(by_code[code]["c1_win_pct"])
        raw = 100 * wins / n
        without_f = 100 * wins / (n - f)
        ranked_only = 100 * wins / ranked
        result.append({
            "code": code, "name": by_code[code]["venue_name"],
            "raw_rows": c["raw"], "study_eligible": n, "excluded": c["excluded_from_earlier_wind_study"],
            "c1_wins": wins, "c1_F_mark": f, "c1_negative_ST": c["first_course_negative_ST"],
            "F_vs_negative_ST_conflicts": c["F_mark_ST_sign_conflict"],
            "c1_ranked_finish_n": ranked,
            "c1_unranked_nonF": c["first_course_unranked_nonF"],
            "c1_ranked_F_conflicts": c["first_course_ranked_F_conflicts"],
            "study_c1_win_pct": round(raw, 2),
            "excluding_c1_F_c1_win_pct": round(without_f, 2),
            "only_c1_with_ranked_finish_win_pct": round(ranked_only, 2),
            "official_c1_win_pct": official,
            "original_gap_official_minus_study_pt": round(official - raw, 2),
            "remaining_gap_after_F_exclusion_pt": round(official - without_f, 2),
            "remaining_gap_after_ranked_finish_subset_pt": round(official - ranked_only, 2),
            "cause_established": False,
        })
    return {
        "schema": "OFFICIAL_C1_RATE_GAP_DENOMINATOR_SENSITIVITY_RESEARCH_V2",
        "research_only": True, "approved_for_forecasting": False,
        "source": "BoatraceCSV post-race result CSV, source-origin unverified",
        "official_primary_result_rows_reconciled": False,
        "official_course_baseline_period": f"{START}..{END}",
        "sampling_rule": "same source eligibility as venue_environment_observational.parse_result; compares all, excluding F and 1C with recorded 1-6 finish; not asserted official formula",
        "official_formula_verified": False,
        "finding": "Removing first-course F and separately restricting to first-course ranked finishes shrink but do not eliminate official rate gaps; status/original result reconciliation remains unresolved",
        "venues": result, "source_manifest": manifest,
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source-root", required=True, type=Path)
    p.add_argument("--official-baseline", required=True, type=Path)
    p.add_argument("--output", required=True, type=Path)
    a = p.parse_args()
    result = audit(a.source_root, a.official_baseline)
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"venues": result["venues"], "days": len(result["source_manifest"])}, ensure_ascii=False))


if __name__ == "__main__":
    main()

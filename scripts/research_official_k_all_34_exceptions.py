#!/usr/bin/env python3
"""Research-only BOAT RACE K primary-source audit of 34 exception races / 28 days.

The official K F/S0/S1/S2 codes are liability/result classifications; public
race-page 転/エ/沈/落/妨 are accident types. Never equate exact strings.
"""
from __future__ import annotations

import argparse
import collections
import json
import re
from pathlib import Path

if __package__:
    from .research_official_k_focus_3day import reconcile_day
else:
    from research_official_k_focus_3day import reconcile_day

PAGE_SYMBOLS = {"Ｆ", "F", "転", "エ", "沈", "落", "妨"}

def frozen_targets(candidate_file: Path, page_doc: Path) -> dict:
    ledger = json.loads(candidate_file.read_text(encoding="utf-8"))
    if (ledger.get("period") != "2026-08-01/2026-10-31"
            or ledger.get("source_days_sha_verified") != 92
            or ledger.get("official_K_rows_reconciled") != 0
            or ledger.get("T12_eligible") is not False):
        raise ValueError("candidate_ledger_unfrozen_or_not_secondary")
    candidates = ledger["exceptions"]
    if len(candidates) != 34:
        raise ValueError("expected_34_secondary_candidates")
    by_code = {}
    for row in candidates:
        code = row["race_code"]
        if code in by_code or not re.fullmatch(r"2026(?:08|09|10)\d{6}", code):
            raise ValueError("duplicate_or_invalid_exception_code:" + code)
        by_code[code] = row
    page_symbols = {}
    for line in page_doc.read_text(encoding="utf-8").splitlines():
        cells = [s.strip() for s in line.strip().strip("|").split("|")]
        if len(cells) != 4 or not re.fullmatch(r"20\d{10}", cells[1]):
            continue
        venue, code, symbol, link = cells
        if (code in page_symbols or symbol not in PAGE_SYMBOLS
                or venue != code[8:10] or "boatrace.jp" not in link):
            raise ValueError("invalid_page_row:" + code)
        page_symbols[code] = "F" if symbol == "Ｆ" else symbol
    if len(page_symbols) != 34 or set(page_symbols) != set(by_code):
        raise ValueError("page_evidence_cohort_differs_from_frozen_candidates")
    groups = collections.defaultdict(list)
    for code in sorted(by_code):
        row = by_code[code]
        status = page_symbols[code]
        if bool(row["first_course_f_mark"]) != (status == "F"):
            raise ValueError("first_course_F_page_status_disagreement:" + code)
        groups[code[:8]].append((code, status))
    if len(groups) != 28:
        raise ValueError("expected_28_exception_days")
    return dict(sorted(groups.items()))

def run(source_dir: Path, raw_dir: Path, frozen_evidence: Path,
        exception_ledger: Path, page_doc: Path) -> dict:
    targets = frozen_targets(exception_ledger, page_doc)
    frozen = json.loads(frozen_evidence.read_text(encoding="utf-8"))
    results = []
    for day in targets:
        try:
            record = reconcile_day(day, source_dir, raw_dir, frozen, targets=targets)
        except Exception as exc:
            record = {
                "day": day, "status": "failed_closed", "error_type": type(exc).__name__,
                "error_summary": str(exc)[:250],
                "official_3month_denominator_established": False,
                "official_primary_92day_reconciliation_complete": False,
            }
        results.append(record)
        print(json.dumps({
            "day": day, "status": record["status"], "focus_races": len(targets[day]),
            "official_rows_compared": record.get("comparison", {}).get("official_races", 0)
                if record["status"] in {"reconciled", "focus_reconciled_secondary_universe_gap"} else 0,
            "field_discrepancies": record.get("comparison", {}).get("field_discrepancy_count")
                if record["status"] in {"reconciled", "focus_reconciled_secondary_universe_gap"} else None,
        }, ensure_ascii=False), flush=True)
    reconciled = [r for r in results if r["status"] == "reconciled"]
    partial = [r for r in results if r["status"] == "focus_reconciled_secondary_universe_gap"]
    focus_confirmed = reconciled + partial
    unexplained = [r for r in results if r not in focus_confirmed]
    report = {
        "schema": "OFFICIAL_K_34_EXCEPTIONS_28DAY_RECONCILIATION_V1",
        "classification": "official_primary_postrace_only_not_T12",
        "exception_races_in_frozen_secondary_cohort": 34,
        "official_K_days_attempted": len(targets),
        "official_K_days_reconciled": len(reconciled),
        "official_K_races_fully_matched": sum(r["comparison"]["official_races"] for r in reconciled),
        "first_course_exceptions_with_K_status_and_page_category_aligned":
            sum(len(r["focus"]) for r in focus_confirmed),
        "days_with_exception_status_reconciled": len(focus_confirmed),
        "days_with_secondary_race_universe_gaps": len(partial),
        "primary_only_race_codes_preserved": sorted(
            x for r in partial for x in r["comparison"]["official_only_race_codes_preserved"]),
        "official_K_races_common_fields_matched": sum(
            r["comparison"]["official_races"] for r in focus_confirmed),
        "days_unreconciled": len(unexplained),
        "official_source_92_days_fully_reconciled": False,
        "official_course_statistic_denominator_verified": False,
        "T12_eligible": False,
        "forecast_model_change_authorized": False,
        "results": results,
    }
    return report

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source-dir", type=Path, required=True)
    p.add_argument("--raw-dir", type=Path, required=True)
    p.add_argument("--frozen-evidence", type=Path, required=True)
    p.add_argument("--exception-ledger", type=Path, required=True)
    p.add_argument("--page-evidence", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    report = run(args.source_dir, args.raw_dir, args.frozen_evidence,
                 args.exception_ledger, args.page_evidence)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2)
                        + "\n", encoding="utf-8")
    print(json.dumps({key: report[key] for key in (
        "official_K_days_reconciled", "official_K_days_attempted",
        "official_K_races_fully_matched",
        "first_course_exceptions_with_K_status_and_page_category_aligned",
        "days_unreconciled", "days_with_secondary_race_universe_gaps",
        "official_K_races_common_fields_matched")}, ensure_ascii=False))
    if report["days_unreconciled"]:
        raise SystemExit(1)

if __name__ == "__main__":
    main()

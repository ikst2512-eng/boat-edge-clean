"""Read-only V2 missing-outcome coverage by venue and JST date.

Separates result availability from hit rate; no official or production claims.
"""
import argparse
import json
import re
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

from four_mode_archive_api import archived_four_modes
from four_mode_frozen_diagnostic import compare_race
from four_mode_v2_predeclared_shadow import (
    VERSION, COUNT_POLICY, MODES, TOPS, candidate_order, missing_result_phase,
)

ROOT = Path(__file__).resolve().parent

def venue_audit(root=ROOT, now=None):
    root = Path(root)
    now = now or datetime.now(timezone(timedelta(hours=9)))
    directory = root / "four_mode_forecasts"
    by_venue = defaultdict(lambda: {
        "saved": 0, "confirmed": 0, "mature_confirmed": 0,
        "missing_before_deadline": 0, "missing_within_60m": 0,
        "missing_over_60m": 0,
        "overdue_example_race_codes": [],
        "missing_file_absent": 0,
        "missing_file_present_but_unavailable": 0,
        "topn": {m: {f"top{n}": 0 for n in TOPS} for m in MODES},
    })
    rejected = defaultdict(int)
    overdue_roster = []
    if not directory.is_dir():
        return {"status": "no_forecast_directory", "formal": False,
                "venues": {}, "rejected": {}}
    for path in sorted(directory.glob("*.json")):
        code = path.stem
        if not re.fullmatch(r"20[0-9]{10}", code):
            continue
        if path.is_symlink() or path.stat().st_size > 30000:
            rejected["unsafe_file"] += 1
            continue
        try:
            obj = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError):
            rejected["invalid_json"] += 1
            continue
        if obj.get("model_version") != VERSION:
            continue
        status, archive = archived_four_modes(code, root)
        if status != 200 or archive.get("model_version") != VERSION:
            rejected["invalid_v2_archive"] += 1
            continue
        if any(len(archive["modes"][m]["tickets"]) != size for m,size in COUNT_POLICY.items()):
            rejected["invalid_v2_counts"] += 1
            continue
        try:
            candidate_order(archive["modes"]["hit"]["tickets"],
                            obj["input_national_win_rates"])
        except (ValueError, TypeError, KeyError):
            rejected["invalid_shadown_inputs"] += 1
            continue
        key = f"{code[:8]}:{code[8:10]}"
        stats = by_venue[key]
        stats["saved"] += 1
        result = compare_race(code,root)
        if result.get("status") == "result_unavailable":
            try:
                phase = missing_result_phase(archive["deadline_jst"], now)
            except (ValueError, TypeError, KeyError, OverflowError):
                rejected["invalid_deadline"] += 1
                continue
            field = {"before_deadline": "missing_before_deadline",
                     "within_60m_after_deadline": "missing_within_60m",
                     "over_60m_after_deadline": "missing_over_60m"}[phase]
            stats[field] += 1
            if phase == "over_60m_after_deadline":
                examples = stats["overdue_example_race_codes"]
                if len(examples) < 3:
                    examples.append(code)
                result_path = root / "confirmed_results" / (code + ".json")
                file_exists = not result_path.is_symlink() and result_path.is_file()
                overdue_roster.append({"race_code": code, "venue_code": code[8:10],
                                       "date_jst": code[:8],
                                       "result_file_present": file_exists})
                if not file_exists:
                    stats["missing_file_absent"] += 1
                else:
                    # compare_race() may reject oversized / inaccessible
                    # result files as unavailable. Never count as a valid result.
                    stats["missing_file_present_but_unavailable"] += 1
            continue
        if result.get("status") != "historical_comparison_only":
            rejected["invalid_or_untrusted_result"] += 1
            continue
        try:
            flags = {m: {f"top{n}": result["modes"][m][f"top{n}"] for n in TOPS}
                     for m in MODES}
            if any(type(flag) is not bool for mode in flags.values()
                   for flag in mode.values()):
                raise ValueError("invalid_flags")
            phase = missing_result_phase(archive["deadline_jst"], now)
        except (ValueError, TypeError, KeyError, OverflowError):
            rejected["invalid_result_flags"] += 1
            continue
        stats["confirmed"] += 1
        stats["mature_confirmed"] += int(phase == "over_60m_after_deadline")
        for m in MODES:
            for n in TOPS:
                stats["topn"][m][f"top{n}"] += int(flags[m][f"top{n}"])
    for venue in by_venue.values():
        if venue["missing_file_absent"] + venue["missing_file_present_but_unavailable"] != venue["missing_over_60m"]:
            raise ValueError("overdue_file_accounting_mismatch")
        total_mature = venue["mature_confirmed"] + venue["missing_over_60m"]
        venue["mature_coverage"] = (
            round(venue["mature_confirmed"] / total_mature, 6)
            if total_mature else None)
        venue["mature_denominator"] = total_mature
    groups = dict(sorted(by_venue.items()))
    if len(overdue_roster) != sum(row["missing_over_60m"] for row in groups.values()):
        raise ValueError("overdue_roster_count_mismatch")
    return {"status": "venue_outcome_coverage_only", "formal": False,
            "verified_first_remote_publication": False,
            "evaluated_at_jst": now.isoformat(), "venues": groups,
            "distinct_venues_with_confirmed": sum(row["confirmed"] > 0 for row in groups.values()),
            "distinct_venues_with_mature_missing": sum(row["missing_over_60m"] > 0 for row in groups.values()),
            "total_saved": sum(row["saved"] for row in groups.values()),
            "overdue_roster": overdue_roster,
            "total_confirmed": sum(row["confirmed"] for row in groups.values()),
            "total_overdue_missing": sum(row["missing_over_60m"] for row in groups.values()),
            "total_missing_file_absent": sum(row["missing_file_absent"] for row in groups.values()),
            "total_missing_file_present_but_unavailable": sum(
                row["missing_file_present_but_unavailable"] for row in groups.values()),
            "rejected": dict(rejected),
            "warning": "Missingness may depend on venue; never treat missing results as losses. Research only."}

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--roster-output", type=Path)
    args = parser.parse_args()
    report = venue_audit()
    if args.roster_output:
        payload = {"schema": "V2_RESEARCH_OVERDUE_ROSTER_V1",
                   "evaluated_at_jst": report.get("evaluated_at_jst"),
                   "formal": False, "result_collection_requested": False,
                   "overdue_race_codes": report.get("overdue_roster", []),
                   "count": len(report.get("overdue_roster", [])),
                   "warning": "Research diagnostics only; never treat missing results as losses."}
        args.roster_output.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n",
                                      encoding="utf-8")
    print("V2_VENUE_COVERAGE=" + json.dumps(report, sort_keys=True))

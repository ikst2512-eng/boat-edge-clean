"""Read-only V2 missing-outcome coverage by venue and JST date.

Separates result availability from hit rate; no official or production claims.
"""
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
        "topn": {m: {f"top{n}": 0 for n in TOPS} for m in MODES},
    })
    rejected = defaultdict(int)
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
        total_mature = venue["mature_confirmed"] + venue["missing_over_60m"]
        venue["mature_coverage"] = (
            round(venue["mature_confirmed"] / total_mature, 6)
            if total_mature else None)
        venue["mature_denominator"] = total_mature
    groups = dict(sorted(by_venue.items()))
    return {"status": "venue_outcome_coverage_only", "formal": False,
            "verified_first_remote_publication": False,
            "evaluated_at_jst": now.isoformat(), "venues": groups,
            "distinct_venues_with_confirmed": sum(row["confirmed"] > 0 for row in groups.values()),
            "distinct_venues_with_mature_missing": sum(row["missing_over_60m"] > 0 for row in groups.values()),
            "total_saved": sum(row["saved"] for row in groups.values()),
            "total_confirmed": sum(row["confirmed"] for row in groups.values()),
            "total_overdue_missing": sum(row["missing_over_60m"] for row in groups.values()),
            "rejected": dict(rejected),
            "warning": "Missingness may depend on venue; never treat missing results as losses. Research only."}

if __name__ == "__main__":
    print("V2_VENUE_COVERAGE=" + json.dumps(venue_audit(), sort_keys=True))

#!/usr/bin/env python3
"""Research-only selection-bias sensitivity of 140 secondary omissions by venue/wind.

All weather is official POSTRACE wind. Does not estimate an eligible T-12 effect.
Compares identical official-K races, once complete and once omitting only the
140 independently identified primary-only race codes. Not the 13,970-row
secondary study with additional filtering; never call those denominators equal.
"""
from __future__ import annotations

import argparse
import collections
import datetime as dt
import hashlib
import json
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

if __package__:
    from .research_official_k_one_day_compare import RACE, parse_k, unpack_lha
    from .research_official_k_c1_24venue_reproduction import (
        EXCLUDED_C1_STATUSES, frozen_baseline)
    from .research_official_k_full_92day import validate_evidence
else:
    from research_official_k_one_day_compare import RACE, parse_k, unpack_lha
    from research_official_k_c1_24venue_reproduction import (
        EXCLUDED_C1_STATUSES, frozen_baseline)
    from research_official_k_full_92day import validate_evidence

START, END = dt.date(2026, 8, 1), dt.date(2026, 10, 31)
BANDS = ("0-2m", "3-4m", "5m+")


def band_of(wind: int) -> str:
    if type(wind) is not int or not 0 <= wind <= 30:
        raise ValueError("invalid_official_postrace_wind")
    return "0-2m" if wind <= 2 else "3-4m" if wind <= 4 else "5m+"


def observation(code: str, race: dict, omitted: bool) -> dict:
    if len(code) != 12 or not code.isdecimal() or race["venue"] != code[8:10]:
        raise ValueError("primary_race_code_or_venue_invalid:" + code)
    entries = race["entries"]
    if len(entries) != 6 or {e["boat"] for e in entries} != set(range(1, 7)):
        raise ValueError("primary_boat_universe_invalid:" + code)
    first = [e for e in entries if e["course"] == 1]
    if len(first) != 1:
        raise ValueError("primary_actual_course1_not_unique:" + code)
    winners = [e for e in entries if e["status"] == "01"]
    if len(winners) > 1 or (not winners and not race["unsettled"]):
        raise ValueError("primary_winner_invalid:" + code)
    if winners and race["unsettled"]:
        raise ValueError("unsettled_but_has_winner:" + code)
    winner_1c = bool(winners and winners[0]["boat"] == first[0]["boat"])
    eligible = first[0]["status"] not in EXCLUDED_C1_STATUSES
    if not eligible and winner_1c:
        raise ValueError("primary_C1_won_with_excluded_status:" + code)
    return {
        "code": code, "venue": race["venue"], "band": band_of(race["wind_m"]),
        "omitted": omitted, "eligible": eligible, "winner_1c": winner_1c,
        "status_c1": first[0]["status"],
        "first_boat": first[0]["boat"],
        "wind_m": race["wind_m"], "unsettled": race["unsettled"],
    }


def _rate(wins: int, n: int):
    return float((Decimal(100 * wins) / Decimal(n)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)) if n else None


def cohort_summary(rows: list[dict], key: str) -> dict:
    n_all = len(rows)
    missing = [r for r in rows if r["omitted"]]
    full = [r for r in rows if r["eligible"]]
    kept = [r for r in full if not r["omitted"]]
    a, b = len(full), len(kept)
    wa = sum(r["winner_1c"] for r in full)
    wb = sum(r["winner_1c"] for r in kept)
    full_rate, kept_rate = _rate(wa, a), _rate(wb, b)
    delta = (float((Decimal(100 * wa) / Decimal(a) - Decimal(100 * wb) / Decimal(b)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)) if a and b else None)
    return {
        "group": key,
        "official_races": n_all,
        "primary_only_missing_races": len(missing),
        "missing_races_20260829": sum(r["code"].startswith("20260829") for r in missing),
        "missing_C1_wins": sum(r["winner_1c"] for r in missing),
        "official_K_C1_eligible_n": a,
        "official_K_C1_wins": wa,
        "same_primary_after_omissions_C1_eligible_n": b,
        "same_primary_after_omissions_C1_wins": wb,
        "primary_full_C1_win_pct": full_rate,
        "primary_without_missing_C1_win_pct": kept_rate,
        "full_minus_without_missing_percentage_points": delta,
        "small_cohort_caution": min(a, b) < 100,
        "postrace_only_not_T12": True,
    }


def summarize(observations: list[dict], omitted_codes: set[str]) -> dict:
    keyed = {}
    for r in observations:
        code = r["code"]
        if code in keyed:
            raise ValueError("duplicate_official_race_code:" + code)
        if r["omitted"] != (code in omitted_codes):
            raise ValueError("primary_missing_code_flag_conflict:" + code)
        if r["winner_1c"] and not r["eligible"]:
            raise ValueError("ineligible_winner:" + code)
        keyed[code] = r
    if not omitted_codes.issubset(keyed):
        raise ValueError("missing_cohort_not_in_official_races")
    by_venue = collections.defaultdict(list)
    by_band = collections.defaultdict(list)
    by_venue_band = collections.defaultdict(list)
    for r in keyed.values():
        by_venue[r["venue"]].append(r)
        by_band[r["band"]].append(r)
        by_venue_band[(r["venue"], r["band"])].append(r)
    return {
        "national": cohort_summary(list(keyed.values()), "all"),
        "by_postrace_wind_band": [cohort_summary(by_band[b], b) for b in BANDS],
        "by_venue": [cohort_summary(by_venue[v], v) for v in sorted(by_venue)],
        "by_venue_postrace_wind_band": [
            cohort_summary(by_venue_band[(v, b)], v + "_" + b)
            for v in sorted(by_venue) for b in BANDS
        ],
    }


def run(comparison: Path, missing_profile: Path, secondary_manifest: Path,
        official_k_dir: Path, baseline_csv: Path) -> dict:
    reconciliation = json.loads(comparison.read_text(encoding="utf-8"))
    profile = json.loads(missing_profile.read_text(encoding="utf-8"))
    frozen = validate_evidence(json.loads(secondary_manifest.read_text(encoding="utf-8")))
    if (reconciliation.get("schema") != "BOAT_EDGE_OFFICIAL_K_FROZEN_92_DAY_PRIMARY_COMPARISON_V1"
            or reconciliation.get("study_period") != "2026-08-01/2026-10-31"
            or reconciliation.get("days_attempted") != 92
            or reconciliation.get("failed_days") != 0
            or reconciliation.get("secondary_extra_days") != 0
            or reconciliation.get("field_discrepancy_count") != 1
            or reconciliation.get("total_common_races_field_checked") != 14109
            or profile.get("schema") != "BOAT_EDGE_K_PRIMARY_ONLY_140_POSTRACE_PROFILE_V1"
            or profile.get("frozen_period") != "2026-08-01/2026-10-31"
            or profile.get("wind_factor_or_model_training_authorized") is not False):
        raise ValueError("research_source_snapshot_or_status_not_frozen")
    rdays = reconciliation["results"]
    if len(rdays) != 92 or len({r["day"] for r in rdays}) != 92:
        raise ValueError("nonunique_primary_receipts")
    index = {r["day"]: r for r in rdays}
    omissions = set(reconciliation.get("official_only_race_codes", []))
    omitted_records = {r["race_code"]: r for r in profile["records"]}
    if (len(omissions) != 140 or len(omitted_records) != 140
            or set(omitted_records) != omissions or profile["missing_races"] != 140):
        raise ValueError("omission_cohort_mismatch")
    baseline = frozen_baseline(baseline_csv)
    observations, manifest = [], []
    for src in frozen:
        day = src["day"].replace("-", "")
        datum = index.get(day)
        if (datum is None or datum["secondary_git_blob_sha"] != src["sha"]
                or datum["secondary_races"] != src["rows"]
                or datum["status"] not in {"reconciled", "primary_extra", "field_mismatch"}):
            raise ValueError("untrusted_primary_secondary_day_receipt:" + day)
        path = official_k_dir / ("k" + day[2:] + ".lzh")
        if path.is_symlink() or not path.is_file():
            raise FileNotFoundError("unavailable_official_K:" + day)
        raw = path.read_bytes()
        sha = hashlib.sha256(raw).hexdigest()
        if sha != datum["official_K_sha256"]:
            raise ValueError("official_K_archive_sha_mismatch:" + day)
        decoded = unpack_lha(raw, day=day)
        if hashlib.sha256(decoded).hexdigest() != datum["decoded_sha256"]:
            raise ValueError("official_K_decoded_sha_mismatch:" + day)
        text = decoded.decode("cp932")
        header_count = sum(bool(RACE.match(line)) for line in text.splitlines())
        races = parse_k(text, day=day, expected_races=header_count, allow_unsettled=True)
        daily_omitted = {code for code in omissions if code.startswith(day)}
        if (len(races) != datum["official_K_races"] or
                set(races) - daily_omitted != set(races) - set(datum["primary_only_race_codes"])
                or set(datum["primary_only_race_codes"]) != daily_omitted or
                len(races) - len(daily_omitted) != src["rows"]):
            raise ValueError("primary_daily_race_universe_disagreement:" + day)
        for code, k in races.items():
            row = observation(code, k, code in omissions)
            if row["omitted"]:
                evidence = omitted_records[code]
                if (evidence["official_result_wind_m"] != row["wind_m"]
                        or evidence["actual_first_course_boat"] != row["first_boat"]
                        or evidence["actual_first_course_status"] != row["status_c1"]
                        or evidence["official_K_unsettled"] != row["unsettled"]):
                    raise ValueError("previous_140_profile_conflicts_with_primary:" + code)
            observations.append(row)
        manifest.append({"date": src["day"], "official_K_SHA256": sha,
                         "official_races": len(races),
                         "primary_only_races": len(daily_omitted),
                         "secondary_git_blob_sha": src["sha"]})
    if (len(observations) != 14249 or len({r["code"] for r in observations}) != 14249
            or sum(r["omitted"] for r in observations) != 140):
        raise ValueError("full_period_primary_size_inconsistent")
    results = summarize(observations, omissions)
    nat = results["national"]
    if (nat["official_K_C1_eligible_n"] != 14090
            or nat["official_K_C1_wins"] != 7811
            or nat["same_primary_after_omissions_C1_eligible_n"] != 13956
            or nat["same_primary_after_omissions_C1_wins"] != 7735
            or len(results["by_venue_postrace_wind_band"]) != 72):
        raise ValueError("official_C1_frozen_period_unexpected_denominators")
    for venue in results["by_venue"]:
        code = venue["group"]
        ratio = (venue["official_K_C1_wins"] * 1000 //
                 venue["official_K_C1_eligible_n"]) / 10
        if ratio != float(baseline[code]["c1_win_pct"]):
            raise ValueError("official_rate_cannot_be_reproduced:" + code)
    shifts = sorted(
        (v for v in results["by_venue_postrace_wind_band"]
         if v["full_minus_without_missing_percentage_points"] is not None),
        key=lambda v: (-abs(v["full_minus_without_missing_percentage_points"]),
                       v["group"]),
    )
    return {
        "schema": "BOAT_EDGE_OFFICIAL_K_WIND_MISSINGNESS_SENSITIVITY_V1",
        "classification": "postrace_primary_subset_missingness_bias_not_T12",
        "period": "2026-08-01/2026-10-31",
        "official_K_receipt_days": len(manifest),
        "primary_races": len(observations),
        "secondary_present_primary_races": len(observations) - len(omissions),
        "omitted_secondary_races": len(omissions),
        "omitted_20260829": sum(r["omitted"] and r["code"].startswith("20260829")
                               for r in observations),
        "c1_denominator_exclusions": sorted(EXCLUDED_C1_STATUSES),
        "note": "Same official-K records; subset removes ONLY 140 omitted race codes, not 139 additional secondary analysis exclusions.",
        "official_24_venue_one_decimal_reproduced": True,
        "by_wind_count": 3, "venue_wind_strata": 72,
        "top_absolute_venue_band_shifts": shifts[:12],
        **results,
        "official_denominator_documented_and_certified": False,
        "causal_wind_effect_identified": False,
        "pre_cutoff_weather_verified": False,
        "forecast_backtest_improvement_proven": False,
        "production_model_change_authorized": False,
        "daily_SHA_receipts": manifest,
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--official-comparison", required=True, type=Path)
    ap.add_argument("--missing-profile", required=True, type=Path)
    ap.add_argument("--secondary-frozen-evidence", required=True, type=Path)
    ap.add_argument("--official-k-dir", required=True, type=Path)
    ap.add_argument("--frozen-official-baseline", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    args = ap.parse_args()
    result = run(args.official_comparison, args.missing_profile,
                 args.secondary_frozen_evidence, args.official_k_dir,
                 args.frozen_official_baseline)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
                        encoding="utf-8")
    print(json.dumps({
        "official_days": result["official_K_receipt_days"],
        "official_races": result["primary_races"],
        "omitted": result["omitted_secondary_races"],
        "strata": result["venue_wind_strata"],
        "national_shift_pp": result["national"]["full_minus_without_missing_percentage_points"],
        "model_change_authorized": False,
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Reproduce (not declare) frozen official 24-venue C1 percentages from K archives.

Research-only postrace primary data. Matching 24 reported percentages is an
empirical agreement, NOT proof of the statistical authority's denominator rule.
No model imports, training, T-12, production writes, or main changes.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
from collections import Counter
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

if __package__:
    from .research_official_k_one_day_compare import RACE, parse_k, unpack_lha
    from .research_official_k_receipt import _is_lzh
else:
    from research_official_k_one_day_compare import RACE, parse_k, unpack_lha
    from research_official_k_receipt import _is_lzh

START, END = dt.date(2026, 8, 1), dt.date(2026, 10, 31)
EXCLUDED_C1_STATUSES = frozenset({"F", "S0", "S1", "S2"})
ALLOWED_C1_STATUSES = frozenset({f"{i:02d}" for i in range(1, 7)}) | frozenset(
    {"F", "S0", "S1", "S2", "K0", "K1", "K2", "L0", "L1", "L2"})
EXPECTED_UNSETTLED = frozenset({"202608072401", "202609140606"})
EXPECTED_PRIMARY_RACES = 14249


def frozen_baseline(path: Path) -> dict:
    with path.open(encoding="utf-8-sig", newline="") as fp:
        rows = list(csv.DictReader(fp))
    if len(rows) != 24 or {r["venue_code"] for r in rows} != {
            f"{i:02d}" for i in range(1, 25)}:
        raise ValueError("frozen_24_venue_baseline_invalid")
    for r in rows:
        if r["start_date"] != str(START) or r["end_date"] != str(END):
            raise ValueError("frozen_official_rate_window_mismatch")
        value = Decimal(r["c1_win_pct"])
        if value < 0 or value > 100 or value.as_tuple().exponent < -1:
            raise ValueError("frozen_official_rate_precision_invalid")
    return {r["venue_code"]: r for r in rows}


def audit(raw_dir: Path, official_baseline: Path) -> dict:
    baseline = frozen_baseline(official_baseline)
    results, sha_manifest = {}, []
    by_venue = {v: Counter() for v in sorted(baseline)}
    unsettled = set()
    for offset in range((END - START).days + 1):
        day = START + dt.timedelta(days=offset)
        yyyymmdd = day.strftime("%Y%m%d")
        p = raw_dir / ("k" + day.strftime("%y%m%d") + ".lzh")
        if p.is_symlink() or not p.is_file():
            raise FileNotFoundError("official_K_missing_or_symlink:" + yyyymmdd)
        raw = p.read_bytes()
        if len(raw) > 20_000_000 or not _is_lzh(raw):
            raise ValueError("invalid_daily_K_archive:" + yyyymmdd)
        decoded = unpack_lha(raw, day=yyyymmdd)
        text = decoded.decode("cp932")
        header_n = sum(bool(RACE.match(line)) for line in text.splitlines())
        if not 1 <= header_n <= 288:
            raise ValueError("bad_primary_day_count:" + yyyymmdd)
        entries = parse_k(text, day=yyyymmdd, expected_races=header_n, allow_unsettled=True)
        if any(not k.startswith(yyyymmdd) or k in results for k in entries):
            raise ValueError("duplicate_or_wrong_day_primary_race:" + yyyymmdd)
        for code, race in entries.items():
            if race["venue"] not in by_venue:
                raise ValueError("unlisted_primary_venue:" + code)
            racers = race["entries"]
            first = [x for x in racers if x["course"] == 1]
            if len(first) != 1:
                raise ValueError("missing_or_ambiguous_primary_1C:" + code)
            first_status = first[0]["status"]
            if first_status not in ALLOWED_C1_STATUSES:
                raise ValueError("unrecognized_primary_1C_status:" + code + ":" + first_status)
            winners = [x for x in racers if x["status"] == "01"]
            if len(winners) == 0:
                if not race["unsettled"]:
                    raise ValueError("winner_absent_without_unsettled_mark:" + code)
                unsettled.add(code)
            if len(winners) > 1:
                raise ValueError("multiple_winners:" + code)
            c = by_venue[race["venue"]]
            c["official_K_races"] += 1
            c["first_course_entry_count"] += 1
            c["status_" + first_status] += 1
            c["unsettled_races"] += int(not winners)
            if winners and winners[0]["boat"] == first[0]["boat"]:
                if first_status in EXCLUDED_C1_STATUSES:
                    raise ValueError("winner_also_excluded:" + code)
                c["first_course_wins"] += 1
            results[code] = race["venue"]
        sha_manifest.append({
            "date": day.isoformat(),
            "archive_sha256": hashlib.sha256(raw).hexdigest(),
            "decoded_sha256": hashlib.sha256(decoded).hexdigest(),
            "official_races": len(entries),
            "classification": "primary_postrace_not_T12",
        })
    if len(results) != EXPECTED_PRIMARY_RACES:
        raise ValueError("unexpected_primary_92_day_race_count:" + str(len(results)))
    if unsettled != EXPECTED_UNSETTLED:
        raise ValueError("unexpected_unsettled_primary_races:" + repr(sorted(unsettled)))
    venues = []
    for code, c in sorted(by_venue.items()):
        total = c["first_course_entry_count"]
        excluded = {status: c["status_" + status]
                    for status in sorted(EXCLUDED_C1_STATUSES)}
        denominator = total - sum(excluded.values())
        wins = c["first_course_wins"]
        if not 0 < denominator <= total or wins > denominator:
            raise ValueError("invalid_primary_c1_denominator:" + code)
        exact = Decimal(100 * wins) / Decimal(denominator)
        trunc_tenths = (1000 * wins) // denominator
        reproduction = Decimal(trunc_tenths) / Decimal(10)
        rounded = exact.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
        baseline_rate = Decimal(baseline[code]["c1_win_pct"])
        venues.append({
            "venue": code, "name": baseline[code]["venue_name"],
            "official_K_races": total, "primary_C1_wins": wins,
            "primary_C1_status_exclusions": excluded,
            "experimental_eligible_C1_denominator": denominator,
            "computed_raw_C1_rate_pct": str(exact.quantize(Decimal("0.0001"))),
            "computed_truncated_one_decimal_pct": str(reproduction),
            "rounded_half_up_one_decimal_pct": str(rounded),
            "frozen_official_display_rate_pct": str(baseline_rate),
            "display_truncated_match": reproduction == baseline_rate,
            "display_half_up_match": rounded == baseline_rate,
        })
    matched = sum(v["display_truncated_match"] for v in venues)
    return {
        "schema": "BOAT_EDGE_C1_RATE_PRIMARY_24_VENUE_REPRODUCTION_V1",
        "classification": "research_postrace_empirical_reproduction_not_official_formula_certification",
        "date_start": str(START), "date_end": str(END),
        "official_K_raw_days_checked": len(sha_manifest),
        "official_K_primary_races_count": len(results),
        "official_K_unsettled_race_codes": sorted(unsettled),
        "denominator_candidate": "count each official K race once for actual C1; exclude C1 status F,S0,S1,S2; allow other listed statuses",
        "display_candidate": "truncate C1_wins * 100 / eligible_n to one decimal",
        "venue_display_matches": matched,
        "venue_total": 24,
        "all_24_displays_reproduced": matched == 24,
        "half_up_display_matches": sum(v["display_half_up_match"] for v in venues),
        "official_denominator_rule_documented_and_certified": False,
        "forecast_improvement_proven": False,
        "production_adoption_authorized": False,
        "venues": venues,
        "manifest": sha_manifest,
        "limitations": [
            "The 24 published one-decimal percentages may be compatible with multiple denominator policies.",
            "An exact one-decimal reproduction is observational evidence, not a sourced official rule.",
            "Official K is postrace; not a source of T-12 wind/ST input.",
            "Prior secondary CSV omits 140 official races, including two unsettled cases.",
            "No four-mode prospective Top-N/Brier/LogLoss improvement has been demonstrated.",
        ],
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--official-k-dir", required=True, type=Path)
    ap.add_argument("--frozen-official-baseline", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    a = ap.parse_args()
    report = audit(a.official_k_dir, a.frozen_official_baseline)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "official_K_days": report["official_K_raw_days_checked"],
        "official_K_races": report["official_K_primary_races_count"],
        "reproduced_venues": report["venue_display_matches"],
        "unsettled": len(report["official_K_unsettled_race_codes"]),
        "official_formula_certified": False,
    }, ensure_ascii=False))
    if report["venue_display_matches"] != 24:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

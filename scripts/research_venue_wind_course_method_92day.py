#!/usr/bin/env python3
"""Research-only, read-only 92-day wind x actual-course x winning-method audit.

Outputs postrace observations. NEVER import these fields into a T-12 prediction.
Requires immutable Git-blob comparison against the pre-existing 92-day manifest.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import sys
from collections import Counter, defaultdict
from datetime import date, timedelta
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from venue_environment_observational import parse_result, wilson_95  # noqa: E402

MANIFEST = ROOT / "docs/research/venue_wind_202608_202610_24venues_research_only.json"
START, END = date(2026, 8, 1), date(2026, 10, 31)
BASE = "https://raw.githubusercontent.com/BoatraceCSV/boatracecsv.github.io/main/data/results/realtime/"
METHODS = ("逃げ", "差し", "まくり", "まくり差し", "抜き", "恵まれ")
BANDS = ("0-2m", "3-4m", "5m+")
EVENTS = ("2C_差し", "3C_まくり", "4C_まくり", "4C_まくり差し")


def git_blob_sha(raw: bytes) -> str:
    header = ("blob %s\0" % len(raw)).encode("ascii")
    return hashlib.sha1(header + raw).hexdigest()


def expected_by_day(manifest: dict) -> dict[str, dict]:
    if manifest.get("period") != "2026-08-01 to 2026-10-31":
        raise ValueError("manifest period mismatch")
    entries = manifest.get("source_hashes_per_day", [])
    lookup = {}
    for e in entries:
        key = e["month"] + "-" + e["file"][:2]
        if key in lookup:
            raise ValueError("duplicate manifest day " + key)
        lookup[key] = e
    days = {str(START + timedelta(days=i)) for i in range((END - START).days + 1)}
    if set(lookup) != days:
        raise ValueError("missing or extra manifest day")
    return lookup


def load_rows(fetch, expected: dict) -> tuple[list[dict], list[dict]]:
    rows, receipts = [], []
    for n in range((END - START).days + 1):
        day = START + timedelta(days=n)
        day_str = str(day)
        url = BASE + f"{day:%Y/%m/%d}.csv"
        raw = fetch(url)
        sha = git_blob_sha(raw)
        if sha != expected[day_str]["sha"]:
            raise ValueError("Git blob mismatch for " + day_str)
        content = raw.decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(content, newline=""))
        mandatory = {"レースコード", "1着_艇番", "決まり手", "風速(m)", "風向",
                     "波の高さ(cm)", "1コース_スタートタイミング", "1コース_F"}
        mandatory.update(f"{i}コース_艇番" for i in range(1, 7))
        mandatory.update(f"{i}コース_スタートタイミング" for i in range(1, 7))
        mandatory.update(f"{i}コース_F" for i in range(1, 7))
        if not reader.fieldnames or not mandatory.issubset(reader.fieldnames):
            raise ValueError("source schema missing fields on " + day_str)
        daily = list(reader)
        if len(daily) != expected[day_str]["rows"]:
            raise ValueError("row count mismatch for " + day_str)
        for r in daily:
            if not r["レースコード"].startswith(day.strftime("%Y%m%d")):
                raise ValueError("race date mismatch for " + day_str)
        receipts.append({"date": day_str, "rows": len(daily), "git_blob_sha": sha,
                         "url": url, "temporal_class": "postrace_only"})
        rows.extend(daily)
    return rows, receipts


def make_counter():
    return {"n": 0, "c1": 0, "escape": 0, "methods": Counter(),
            "winning_courses": Counter(), "cross": Counter(), "wind_dirs": Counter(),
            "waves_n": 0, "waves_sum": 0.0, "waves_missing": 0,
            "st1_n": 0, "st1_sum": 0.0, "st1_missing_or_f": 0, "f1_n": 0}


def finalize(x: dict, min_n: int) -> dict:
    n = x["n"]
    def event(name):
        k = x["cross"].get(name, 0)
        return {"count": k, "rate_of_all_races_pct": round(100 * k / n, 3) if n else None,
                "wilson95_pct": wilson_95(k, n)}
    return {
        "n": n, "course1_wins": x["c1"], "escape_method_count": x["escape"],
        "course1_win_pct": round(100*x["c1"]/n, 3) if n else None,
        "course1_wilson95_pct": wilson_95(x["c1"], n),
        "adequate_exploratory_n_100": n >= min_n,
        "methods": dict(sorted(x["methods"].items())),
        "winning_courses": {str(i): x["winning_courses"].get(i, 0) for i in range(1, 7)},
        "course_method_counts": dict(sorted(x["cross"].items())),
        "events": {e: event(e) for e in EVENTS},
        "wave_mean_cm": round(x["waves_sum"]/x["waves_n"], 3) if x["waves_n"] else None,
        "wave_n": x["waves_n"], "wave_missing": x["waves_missing"],
        "st1_mean_nonf_seconds": round(x["st1_sum"]/x["st1_n"], 4) if x["st1_n"] else None,
        "st1_nonf_n": x["st1_n"], "st1_missing_or_f": x["st1_missing_or_f"],
        "st1_f_n": x["f1_n"],
    }


def aggregate(rows: list[dict], min_n: int = 100) -> dict:
    # Same acceptance as the existing study: parse_result is the frozen baseline gate.
    # Refuse duplicate codes rather than silently counting one of the candidates.
    by_code, duplicates = {}, set()
    for raw in rows:
        code = (raw.get("レースコード") or "").strip()
        if code in by_code:
            duplicates.add(code)
        else:
            by_code[code] = raw
    groups = defaultdict(make_counter)
    rejected = Counter()
    for code, r in by_code.items():
        if code in duplicates:
            rejected["duplicate_race_codes_removed_all"] += 1
            continue
        try:
            parsed = parse_result(r)
        except ValueError as exc:
            rejected[str(exc)] += 1
            continue
        v, b, m = parsed["venue"], parsed["wind_band"], parsed["month"]
        course, method = parsed["winner_course"], parsed["method"]
        for key in (("national", b), ("venue", v, b), ("month", m, b),
                    ("venue_month", v, m, b)):
            a = groups[key]
            a["n"] += 1
            a["c1"] += (course == 1)
            a["escape"] += (method == "逃げ")
            a["methods"][method] += 1
            a["winning_courses"][course] += 1
            a["cross"][f"{course}C_{method}"] += 1
            a["wind_dirs"][parsed["wind_direction_raw"]] += 1
            wave_text = (r.get("波の高さ(cm)") or "").strip()
            try:
                wave = float(wave_text)
            except ValueError:
                wave = math.nan
            if math.isfinite(wave) and 0 <= wave <= 100 and wave_text:
                a["waves_n"] += 1
                a["waves_sum"] += wave
            else:
                a["waves_missing"] += 1
            st_text = (r.get("1コース_スタートタイミング") or "").strip()
            is_f = (r.get("1コース_F") or "").strip() == "F"
            a["f1_n"] += is_f
            try:
                st = float(st_text)
            except ValueError:
                st = math.nan
            if not is_f and math.isfinite(st) and 0 <= st <= 1:
                a["st1_n"] += 1
                a["st1_sum"] += st
            else:
                a["st1_missing_or_f"] += 1
    national = {b: finalize(groups[("national", b)], min_n) for b in BANDS}
    venue = {f"{i:02d}": {b: finalize(groups[("venue", f"{i:02d}", b)], min_n)
                           for b in BANDS} for i in range(1, 25)}
    months = {f"2026-{m:02d}": {b: finalize(groups[("month", f"2026{m:02d}", b)], min_n)
                                  for b in BANDS} for m in (8, 9, 10)}
    venue_month = {f"{i:02d}": {
        f"2026-{m:02d}": {
            b: finalize(groups[("venue_month", f"{i:02d}", f"2026{m:02d}", b)], min_n)
            for b in BANDS}
        for m in (8, 9, 10)} for i in range(1, 25)}
    return {
        "schema": "VENUE_ACTUAL_COURSE_METHOD_WIND_POSTRACE_V1",
        "status": "research_descriptive_only", "weather_is_postrace": True,
        "model_training_authorized": False, "formal_prediction_evidence": False,
        "record_count_input": len(rows),
        "record_count_valid": sum(national[b]["n"] for b in BANDS),
        "excluded": dict(sorted(rejected.items())),
        "national": national, "venues": venue, "monthly": months,
        "venue_monthly": venue_month,
        "notes": [
            "Actual starting course is not the same as boat or frame number.",
            "Method/course event percentages use all valid races in their wind band.",
            "These are correlations, not causally identified wind adjustments.",
            "Result wind, waves, actual ST and finish must never become T-12 features.",
            "No course/wind compensation on main or production is authorized.",
        ],
    }


def reconcile(study: dict, baseline: dict):
    if study["record_count_input"] != baseline["input_rows"]:
        raise ValueError("input count inconsistent with frozen 3-month baseline")
    if study["record_count_valid"] != baseline["eligible_unique_races"]:
        raise ValueError("valid count inconsistent with frozen 3-month baseline")
    if sum(study["excluded"].values()) != study["record_count_input"] - study["record_count_valid"]:
        raise ValueError("excluded count does not balance")
    for b in BANDS:
        if study["national"][b]["n"] != baseline["national"][b]["n"]:
            raise ValueError("national wind count disagreement " + b)
    for v in baseline["venues"]:
        for b in BANDS:
            if study["venues"][v["code"]][b]["n"] != v["wind_bands"][b]["n"]:
                raise ValueError("venue wind count disagreement " + v["code"] + " " + b)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--min-n", type=int, default=100)
    ap.add_argument("--c1-exception-output", type=Path, help="PR-only postrace 1C exception ledger")
    ap.add_argument("--frozen-day-csv-output", type=Path, help="Optional SHA-verified 2026-08-01 comparison input")
    ap.add_argument("--frozen-target-csv-dir", type=Path, help="Optional frozen 3-day secondary files for K exception checks")
    ap.add_argument("--frozen-exception-csv-dir", type=Path, help="SHA-verified raw CSV for all 34 exception races across 28 days")
    ap.add_argument("--frozen-all-csv-dir", type=Path, help="PR-only all 92 SHA-verified secondary daily CSVs for K primary audit")
    args = ap.parse_args()
    if args.min_n < 1:
        raise SystemExit("minimum n must be positive")
    baseline = json.loads(MANIFEST.read_text(encoding="utf-8"))
    expected = expected_by_day(baseline)
    frozen_day = {}
    def fetch(url):
        with urlopen(url, timeout=30) as response:
            data = response.read()
        if args.frozen_day_csv_output and url == BASE + "2026/08/01.csv":
            frozen_day["source"] = data
        if args.frozen_target_csv_dir:
            for day in ("2026/08/02", "2026/08/21", "2026/08/26"):
                if url == BASE + day + ".csv":
                    frozen_day[day.replace("/", "")] = data
        if args.frozen_exception_csv_dir or args.frozen_all_csv_dir:
            frozen_day[url[len(BASE):].replace("/", "").replace(".csv", "")] = data
        return data
    rows, receipts = load_rows(fetch, expected)
    if args.frozen_day_csv_output:
        if git_blob_sha(frozen_day.get("source", b"")) != expected["2026-08-01"]["sha"]:
            raise ValueError("frozen_20260801_day_sha_missing_or_mismatch")
        args.frozen_day_csv_output.parent.mkdir(parents=True, exist_ok=True)
        args.frozen_day_csv_output.write_bytes(frozen_day["source"])
    if args.frozen_target_csv_dir:
        args.frozen_target_csv_dir.mkdir(parents=True, exist_ok=True)
        for day in ("2026-08-02", "2026-08-21", "2026-08-26"):
            value = frozen_day.get(day.replace("-", ""))
            if value is None or git_blob_sha(value) != expected[day]["sha"]:
                raise ValueError("frozen_target_day_sha_missing_or_mismatch:" + day)
            (args.frozen_target_csv_dir / ("secondary_" + day.replace("-", "") + ".csv")).write_bytes(value)
    if args.frozen_all_csv_dir:
        for date, item in expected.items():
            key = date.replace("-", "")
            raw = frozen_day.get(key)
            if raw is None or git_blob_sha(raw) != item["sha"]:
                raise ValueError("all_day_source_hash_mismatch:" + date)
        args.frozen_all_csv_dir.mkdir(parents=True, exist_ok=True)
        for date in sorted(expected):
            key = date.replace("-", "")
            out = args.frozen_all_csv_dir / ("secondary_" + key + ".csv")
            if out.is_symlink():
                raise ValueError("refuse_symlink_export:" + str(out))
            if out.exists() and out.read_bytes() != frozen_day[key]:
                raise ValueError("refuse_modified_export:" + date)
            if not out.exists():
                out.write_bytes(frozen_day[key])
    output = aggregate(rows, args.min_n)
    reconcile(output, baseline)
    if args.frozen_exception_csv_dir and args.c1_exception_output is None:
        raise ValueError("exception_csv_export_requires_frozen_candidate_ledger")
    if args.c1_exception_output is not None:
        from scripts.research_official_c1_exception_ledger import from_verified_rows
        frozen = ROOT / "docs/research/venue_course_method_evidence_20261106/reconciled_92day_summary.json"
        evidence = json.loads(frozen.read_text(encoding="utf-8"))
        candidates = from_verified_rows(rows, receipts, evidence)
        args.c1_exception_output.parent.mkdir(parents=True, exist_ok=True)
        args.c1_exception_output.write_text(
            json.dumps(candidates, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8")
        if args.frozen_exception_csv_dir:
            days = sorted({x["race_code"][:8] for x in candidates["exceptions"]})
            if len(days) != 28:
                raise ValueError("expected_28_distinct_exception_days")
            for day in days:
                date = f"{day[:4]}-{day[4:6]}-{day[6:]}"
                value = frozen_day.get(day)
                if value is None or git_blob_sha(value) != expected[date]["sha"]:
                    raise ValueError("exception_day_git_sha_invalid:" + day)
            args.frozen_exception_csv_dir.mkdir(parents=True, exist_ok=True)
            for day in days:
                (args.frozen_exception_csv_dir / ("secondary_" + day + ".csv")).write_bytes(frozen_day[day])
    output["source_receipts"] = receipts
    output["method_note"] = "External Git blob equality verifies a historical file snapshot, not official racing results or first remote receipt."
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    summary = {"status": output["status"], "input": output["record_count_input"],
               "valid": output["record_count_valid"], "excluded": output["excluded"],
               "national": {b: {k: output["national"][b][k]
                                for k in ("n", "course1_win_pct", "events", "wave_mean_cm",
                                          "st1_mean_nonf_seconds")} for b in BANDS},
               "output": str(args.output)}
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()

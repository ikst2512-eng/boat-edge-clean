#!/usr/bin/env python3
"""Read-only retrospective study of finish-time weather and real courses.

Never use this output as race-day T-12 input: results/weather here are
post-race records. No network, forecast modification, or source mutation.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import math
import re
from collections import defaultdict
from pathlib import Path

VENUES = ("桐生", "戸田", "江戸川", "平和島", "多摩川", "浜名湖", "蒲郡", "常滑", "津", "三国", "びわこ", "住之江", "尼崎", "鳴門", "丸亀", "児島", "宮島", "徳山", "下関", "若松", "芦屋", "福岡", "唐津", "大村")
BINS = ("0-2", "3-4", "5+")
REQUIRED = ("レースコード", "風速(m)", "決まり手", "1着_艇番") + tuple(f"{n}コース_艇番" for n in range(1, 7)) + tuple(f"{n}着_艇番" for n in range(1, 7)) + tuple(f"{n}コース_F" for n in range(1, 7))


def wilson(k: int, n: int) -> tuple[str, str]:
    if n == 0:
        return "", ""
    z = 1.95996398454
    p = k / n
    den = 1 + z * z / n
    mid = (p + z * z / (2 * n)) / den
    radius = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return f"{100 * (mid - radius):.1f}", f"{100 * (mid + radius):.1f}"


def classify(row: dict, day: dt.date, seen: set[str]):
    """Return (venue index, bin, first-course win, escape) or a reason."""
    code = (row.get("レースコード") or "").strip()
    if not re.fullmatch(r"\d{12}", code) or not code.startswith(day.strftime("%Y%m%d")):
        return None, "invalid_code"
    venue = int(code[8:10])
    if venue not in range(1, 25) or int(code[10:12]) not in range(1, 13):
        return None, "invalid_code"
    if code in seen:
        return None, "duplicate"
    seen.add(code)
    raw_wind = (row.get("風速(m)") or "").strip()
    if re.fullmatch(r"\d+(?:\.\d+)?", raw_wind) is None:
        return None, "invalid_wind"
    wind = float(raw_wind)
    if not 0 <= wind <= 40:
        return None, "invalid_wind"

    def full_permutation(prefix: str):
        raw = [(row.get(f"{n}{prefix}") or "").strip() for n in range(1, 7)]
        if not all(re.fullmatch(r"[1-6]", v) for v in raw):
            return None
        nums = [int(v) for v in raw]
        return nums if sorted(nums) == [1, 2, 3, 4, 5, 6] else None

    course = full_permutation("コース_艇番")
    if course is None:
        return None, "incomplete_course"
    finish = full_permutation("着_艇番")
    if finish is None:
        return None, "incomplete_finish"
    if any((row.get(f"{n}コース_F") or "").strip() == "F" for n in range(1, 7)):
        return None, "flying"
    first_course_won = int(course[0] == finish[0])
    escape = int("".join((row.get("決まり手") or "").split()) == "逃げ")
    wind_bin = 0 if wind <= 2 else 1 if wind <= 4 else 2
    return (venue - 1, wind_bin, first_course_won, escape), None


def study(root: Path, start: dt.date, end: dt.date):
    if end < start:
        raise ValueError("end date precedes start date")
    if (end - start).days > 366:
        raise ValueError("study limited to 367 days per run")
    counts = [[[0, 0, 0] for _ in BINS] for _ in VENUES]
    errors = defaultdict(int)
    manifest = []
    seen = set()
    for offset in range((end - start).days + 1):
        day = start + dt.timedelta(days=offset)
        p = root / "data" / "results" / "realtime" / f"{day:%Y}" / f"{day:%m}" / f"{day:%d}.csv"
        if not p.is_file() or p.is_symlink():
            raise FileNotFoundError(f"source missing or symlink: {p}; incomplete period rejected")
        raw = p.read_bytes()
        if not raw:
            raise ValueError(f"empty source: {p}")
        text = raw.decode("utf-8-sig")
        source_rows = 0
        for row in csv.DictReader(text.splitlines()):
            source_rows += 1
            errors["input"] += 1
            if not all(k in row for k in REQUIRED):
                raise ValueError(f"missing required CSV columns at {p}")
            result, reason = classify(row, day, seen)
            if reason:
                errors[reason] += 1
                continue
            venue, bucket, first, escape = result
            counts[venue][bucket][0] += 1
            counts[venue][bucket][1] += first
            counts[venue][bucket][2] += escape
            errors["valid"] += 1
        manifest.append({"date": str(day), "rows": source_rows, "source_sha256": hashlib.sha256(raw).hexdigest(), "path": str(p)})
    return counts, dict(errors), manifest


def export(counts, path: Path):
    fields = ["venue_code", "venue_name", "wind_speed_ms", "n_six_finish_valid", "c1_win_count", "c1_win_pct", "escape_count", "escape_pct", "c1_wilson95_low_pct", "c1_wilson95_high_pct", "sample_warning", "temporal_class"]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(fields)
        for i, venue in enumerate(VENUES):
            for j, bucket in enumerate(BINS):
                n, wins, escapes = counts[i][j]
                lo, hi = wilson(wins, n)
                writer.writerow([f"{i+1:02d}", venue, bucket, n, wins, f"{100 * wins / n:.1f}" if n else "", escapes, f"{100 * escapes / n:.1f}" if n else "", lo, hi, "descriptive_n_ge_30" if n >= 30 else "small_sample" if n else "no_observations", "postrace_only_not_T12"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, type=Path, help="Local BoatraceCSV source repo root; never network")
    parser.add_argument("--start", required=True, type=dt.date.fromisoformat)
    parser.add_argument("--end", required=True, type=dt.date.fromisoformat)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    counts, rejected, manifest = study(args.root, args.start, args.end)
    export(counts, args.output)
    summary = {"temporal_class": "postrace_only_not_T12", "counts": rejected, "sources": manifest}
    args.output.with_suffix(".sources.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "days": len(manifest), "counts": rejected}, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()

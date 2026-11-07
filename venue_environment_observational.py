"""Research-only, post-race observational venue/wind audit.

Results weather is NOT a predeadline measurement. No model or forecast imports.
The input CSV's source provenance is not independently authenticated here.
"""
import argparse
import csv
import json
import math
import re
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

BANDS = ("0-2m", "3-4m", "5m+")
METHODS = frozenset({"逃げ", "差し", "まくり", "まくり差し", "抜き", "恵まれ"})
REQUIRED = {"レースコード", "1着_艇番", "決まり手", "風速(m)", "風向"} | {
    f"{i}コース_艇番" for i in range(1, 7)
}
VENUES = frozenset(f"{i:02d}" for i in range(1, 25))


def wind_band(speed):
    if speed <= 2:
        return "0-2m"
    if speed <= 4:
        return "3-4m"
    return "5m+"


def wilson_95(success, count):
    if count <= 0:
        return None
    z = 1.959963984540054
    p = success / count
    den = 1 + z*z/count
    mid = (p + z*z/(2*count))/den
    radius = z*math.sqrt(p*(1-p)/count + z*z/(4*count*count))/den
    return [round(100*(mid-radius), 2), round(100*(mid+radius), 2)]


def parse_result(row):
    code = (row.get("レースコード") or "").strip()
    if not re.fullmatch(r"20\d{10}", code) or code[8:10] not in VENUES:
        raise ValueError("invalid_race_code")
    try:
        datetime.strptime(code[:8], "%Y%m%d")
    except ValueError as exc:
        raise ValueError("invalid_race_date") from exc
    if not 1 <= int(code[10:12]) <= 12:
        raise ValueError("invalid_race_number")
    try:
        winner = int(row.get("1着_艇番", ""))
        courses = [int(row.get(f"{i}コース_艇番", "")) for i in range(1, 7)]
    except (TypeError, ValueError) as exc:
        raise ValueError("incomplete_finish_or_course") from exc
    if sorted(courses) != [1, 2, 3, 4, 5, 6] or winner not in courses:
        raise ValueError("incomplete_finish_or_course")
    try:
        speed = float(row.get("風速(m)", ""))
    except (TypeError, ValueError) as exc:
        raise ValueError("wind_missing_or_invalid") from exc
    if not math.isfinite(speed) or not 0 <= speed <= 30:
        raise ValueError("wind_missing_or_invalid")
    # Source expresses wind in integer m/s. Do not put 2.5m in '3-4m'.
    if not speed.is_integer():
        raise ValueError("wind_noninteger_out_of_band_definition")
    # Historical result data uses full-width spaces: 逃　げ / 差　し / 抜　き.
    method = "".join(str(row.get("決まり手") or "").split())
    if method not in METHODS:
        raise ValueError("winning_method_missing_or_invalid")
    direction = str(row.get("風向") or "").strip()
    if not direction and speed > 0:
        raise ValueError("wind_direction_missing")
    return {
        "code": code, "venue": code[8:10], "month": code[:6],
        "wind_band": wind_band(speed),
        "wind_direction_raw": direction if direction else "無風方向未記録",
        "method": method, "winner_boat": winner,
        "winner_course": courses.index(winner) + 1,
    }


def summarize(records, minimum):
    n = len(records)
    counts = Counter(r["method"] for r in records)
    first_course_wins = sum(r["winner_course"] == 1 for r in records)
    boat1_wins = sum(r["winner_boat"] == 1 for r in records)
    pct = lambda v: round(100*v/n, 2) if n else None
    return {
        "n": n, "sufficient_n": n >= minimum,
        "winner_boat1_pct": pct(boat1_wins),
        "winner_course1_pct": pct(first_course_wins),
        "winner_course1_ci95_pct": wilson_95(first_course_wins, n),
        "escape_method_pct": pct(counts["逃げ"]),
        "escape_method_ci95_pct": wilson_95(counts["逃げ"], n),
        "winner_course_pct": {
            str(c): pct(sum(r["winner_course"] == c for r in records))
            for c in range(1, 7)
        },
        "winning_method_pct": {m: pct(counts[m]) for m in sorted(METHODS)},
    }


def analyze_rows(rows, min_n=100):
    if min_n < 1:
        raise ValueError("min_n_must_be_positive")
    by_code = {}
    duplicates = set()
    exclusions = Counter()
    count = 0
    for row in rows:
        count += 1
        code = (row.get("レースコード") or "").strip()
        if code in by_code or code in duplicates:
            duplicates.add(code)
            by_code.pop(code, None)
            continue
        try:
            by_code[code] = parse_result(row)
        except ValueError as exc:
            by_code[code] = {"invalid": str(exc)}
    accepted = []
    for code, record in by_code.items():
        if code in duplicates:
            continue
        if "invalid" in record:
            exclusions[record["invalid"]] += 1
        else:
            accepted.append(record)
    if duplicates:
        exclusions["duplicate_race_codes_removed_all"] = len(duplicates)
    groups = defaultdict(list)
    months = defaultdict(list)
    directions = defaultdict(list)
    for row in accepted:
        groups[(row["venue"], row["wind_band"])].append(row)
        months[(row["venue"], row["month"], row["wind_band"])].append(row)
        directions[(row["venue"], row["wind_band"], row["wind_direction_raw"])].append(row)
    venues = {}
    for venue in sorted(VENUES):
        stats = {band: summarize(groups[(venue, band)], min_n) for band in BANDS}
        calm = stats["0-2m"]
        for band in BANDS[1:]:
            strong = stats[band]
            comparable = calm["sufficient_n"] and strong["sufficient_n"]
            strong["vs_0_2m_course1_win_delta_pt"] = (
                round(strong["winner_course1_pct"] - calm["winner_course1_pct"], 2)
                if comparable else None
            )
            strong["vs_0_2m_escape_delta_pt"] = (
                round(strong["escape_method_pct"] - calm["escape_method_pct"], 2)
                if comparable else None
            )
        venues[venue] = stats
    return {
        "schema": "VENUE_WIND_POST_RACE_DESCRIPTIVE_V1",
        "research_only": True, "formal_prediction_evidence": False,
        "weather_is_post_race": True, "model_training_authorized": False,
        "wind_direction_relative_to_course": "not_calculated_without_verified_venue_axis",
        "baseline_reference": "0-2m", "minimum_group_n": min_n,
        "input_rows": count, "accepted_unique_races": len(accepted),
        "excluded": dict(sorted(exclusions.items())),
        "venue_wind_band": venues,
        "venue_month_wind_band": [
            {"venue": v, "year_month": m, "wind_band": band,
             **summarize(records, min_n)}
            for (v, m, band), records in sorted(months.items())
        ],
        "venue_wind_direction_raw": [
            {"venue": v, "wind_band": band, "recorded_wind_direction": direction,
             **summarize(records, min_n)}
            for (v, band, direction), records in sorted(directions.items())
        ],
        "limits": [
            "Observational associations, not causal effects.",
            "Result-file wind differs from measured predeadline wind.",
            "Source receipts and origin are NOT independently verified.",
            "Missing or duplicate races are excluded, never replaced with zeros.",
            "Boat number and actual starting course are different variables.",
            "Wind heading is not converted to head/tail without venue axis evidence.",
            "Venue/month, race class, athlete quality and race selection confound effects.",
            "Sparse groups produce null comparisons; rates are not forecast probabilities.",
        ],
    }


def analyze_csv(path, min_n=100):
    with Path(path).open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        if not reader.fieldnames or not REQUIRED.issubset(reader.fieldnames):
            missing = sorted(REQUIRED - set(reader.fieldnames or ()))
            raise ValueError("result_schema_missing_columns:" + ",".join(missing))
        return analyze_rows(reader, min_n=min_n)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("results_csv", type=Path, help="post-race results CSV only")
    parser.add_argument("--out", type=Path, help="output research JSON; stdout when omitted")
    parser.add_argument("--min-n", type=int, default=100)
    args = parser.parse_args()
    payload = json.dumps(analyze_csv(args.results_csv, args.min_n),
                         ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.out:
        args.out.write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")


if __name__ == "__main__":
    main()

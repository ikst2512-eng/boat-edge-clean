#!/usr/bin/env python3
"""Research-only ledger of first-course F/unranked rows in frozen 92-day CSV.

Checks all 92 BoatraceCSV Git blob hashes before publishing any candidates.
A secondary-source missing finishing place is NOT an official K status.
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

START, END = dt.date(2026, 8, 1), dt.date(2026, 10, 31)
FOCUS = ("03", "06", "17", "23")
EXPECTED = {
    "03": {"raw": 545, "eligible": 536, "wins": 245, "f": 6, "nonf_unranked": 5},
    "06": {"raw": 635, "eligible": 632, "wins": 336, "f": 6, "nonf_unranked": 4},
    "17": {"raw": 469, "eligible": 461, "wins": 265, "f": 2, "nonf_unranked": 2},
    "23": {"raw": 516, "eligible": 512, "wins": 294, "f": 2, "nonf_unranked": 7},
}

def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()

def exception(row: dict, parsed: dict) -> dict | None:
    first = (row.get("1コース_艇番") or "").strip()
    ranks = [(row.get(f"{i}着_艇番") or "").strip() for i in range(1, 7)]
    if any(x and (x not in "123456" or len(x) != 1) for x in ranks):
        raise ValueError("invalid_ranked_boat:" + parsed["code"])
    nonempty = [x for x in ranks if x]
    if len(nonempty) != len(set(nonempty)):
        raise ValueError("duplicate_finish_boat:" + parsed["code"])
    f = (row.get("1コース_F") or "").strip() == "F"
    ranked = first in ranks
    if ranked and not f:
        return None
    return {
        "race_code": parsed["code"], "venue": parsed["venue"],
        "first_course_boat": first, "first_course_f_mark": f,
        "first_course_finish_rank": (ranks.index(first) + 1 if ranked else None),
        "first_course_st_raw": (row.get("1コース_スタートタイミング") or "").strip(),
        "reason": "first_course_F_mark" if f else "first_course_unranked_nonF",
        "official_K_status": "unverified", "official_K_receipt_sha256": None,
        "source_class": "BoatraceCSV_postrace_secondary_only",
    }

def scan_day(path: Path, source: dict) -> tuple[dict, list[dict]]:
    if path.is_symlink() or not path.is_file():
        raise FileNotFoundError("missing_or_symlink_day:" + str(path))
    raw = path.read_bytes()
    sha = git_blob_sha(raw)
    if sha != source["sha"]:
        raise ValueError(f"git_blob_sha_mismatch:{source['day']}:{sha}")
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {"レースコード", "1コース_艇番", "1コース_F",
                    "1コース_スタートタイミング", "決まり手", "風速(m)", "風向"}
        required |= {f"{i}着_艇番" for i in range(1, 7)}
        required |= {f"{i}コース_艇番" for i in range(1, 7)}
        if not required.issubset(reader.fieldnames or []):
            raise ValueError("missing_columns:" + str(path))
        rows = list(reader)
    if len(rows) != source["rows"]:
        raise ValueError("row_count_mismatch:" + source["day"])
    accepted, c, candidates, seen = 0, Counter(), [], set()
    for row in rows:
        key = (row.get("レースコード") or "").strip()
        if not key.startswith(source["day"].replace("-", "")) or key in seen:
            raise ValueError("date_or_duplicate_race_code:" + key)
        seen.add(key)
        if key[8:10] in FOCUS:
            c[key[8:10] + ":raw"] += 1
        try:
            parsed = parse_result(row)
        except ValueError:
            continue
        accepted += 1
        venue = parsed["venue"]
        if venue not in FOCUS:
            continue
        c[venue + ":eligible"] += 1
        c[venue + ":wins"] += int(parsed["winner_course"] == 1)
        x = exception(row, parsed)
        if x:
            c[venue + (":f" if x["first_course_f_mark"] else ":nonf_unranked")] += 1
            candidates.append(x)
    if accepted != source["accepted"]:
        raise ValueError("accepted_count_mismatch:" + source["day"])
    return dict(c), candidates

def run(root: Path, manifest: Path) -> dict:
    evidence = json.loads(manifest.read_text(encoding="utf-8"))
    if evidence.get("period") != "2026-08-01/2026-10-31":
        raise ValueError("unexpected_fixed_period")
    sources = evidence.get("sources", [])
    days = [(START + dt.timedelta(days=i)).isoformat()
            for i in range((END - START).days + 1)]
    if [s["day"] for s in sources] != days:
        raise ValueError("source_days_missing_duplicated_or_out_of_order")
    totals, candidates = Counter(), []
    for source in sources:
        day = dt.date.fromisoformat(source["day"])
        path = root / f"data/results/realtime/{day:%Y}/{day:%m}/{day:%d}.csv"
        counts, issues = scan_day(path, source)
        totals.update(counts)
        candidates.extend(issues)
    for venue, expected in EXPECTED.items():
        for key, count in expected.items():
            actual = totals[f"{venue}:{key}"]
            if actual != count:
                raise ValueError(f"focus_total_mismatch:{venue}:{key}:{actual}:{count}")
    if len(candidates) != 34:
        raise ValueError("unexpected_exception_count:" + str(len(candidates)))
    return {
        "schema": "FIRST_COURSE_EXCEPTION_CANDIDATES_V1",
        "classification": "secondary_postrace_research_only_not_official_K",
        "period": evidence["period"], "source_days_sha_verified": len(sources),
        "official_K_rows_reconciled": 0, "T12_eligible": False,
        "official_c1_denominator_established": False,
        "by_venue": {v: {k: totals[f"{v}:{k}"] for k in EXPECTED[v]} for v in FOCUS},
        "exceptions": sorted(candidates, key=lambda x: x["race_code"]),
    }

def from_verified_rows(rows: list[dict], receipts: list[dict], evidence: dict) -> dict:
    """Generate candidates only from the existing 92-day SHA-verified fetcher."""
    sources = evidence.get("sources", [])
    expected_days = [(START + dt.timedelta(days=i)).isoformat() for i in range(92)]
    if evidence.get("period") != "2026-08-01/2026-10-31" or [s["day"] for s in sources] != expected_days:
        raise ValueError("unexpected_frozen_source_period")
    if len(receipts) != 92 or len(rows) != sum(s["rows"] for s in sources):
        raise ValueError("verified_receipt_or_raw_count_mismatch")
    for receipt, source in zip(receipts, sources):
        if (receipt.get("date") != source["day"]
                or receipt.get("git_blob_sha") != source["sha"]
                or receipt.get("rows") != source["rows"]
                or receipt.get("temporal_class") != "postrace_only"):
            raise ValueError("receipt_mismatch:" + source["day"])
    counts, daily, accepted_daily = Counter(), Counter(), Counter()
    seen, candidates = set(), []
    for row in rows:
        key = (row.get("レースコード") or "").strip()
        day = key[:4] + "-" + key[4:6] + "-" + key[6:8]
        if key in seen or day not in expected_days:
            raise ValueError("duplicate_or_unexpected_race_code:" + key)
        seen.add(key)
        daily[day] += 1
        venue = key[8:10]
        if venue in FOCUS:
            counts[venue + ":raw"] += 1
        try:
            parsed = parse_result(row)
        except ValueError:
            continue
        accepted_daily[day] += 1
        if venue not in FOCUS:
            continue
        counts[venue + ":eligible"] += 1
        counts[venue + ":wins"] += int(parsed["winner_course"] == 1)
        x = exception(row, parsed)
        if x:
            counts[venue + (":f" if x["first_course_f_mark"] else ":nonf_unranked")] += 1
            candidates.append(x)
    for source in sources:
        if daily[source["day"]] != source["rows"] or accepted_daily[source["day"]] != source["accepted"]:
            raise ValueError("daily_rows_or_acceptance_mismatch:" + source["day"])
    for venue, expected in EXPECTED.items():
        for key, n in expected.items():
            if counts[venue + ":" + key] != n:
                raise ValueError("focus_count_mismatch:" + venue + ":" + key)
    if len(candidates) != 34:
        raise ValueError("unexpected_candidate_count:" + str(len(candidates)))
    return {
        "schema": "FIRST_COURSE_EXCEPTION_CANDIDATES_V1",
        "classification": "secondary_postrace_research_only_not_official_K",
        "period": evidence["period"], "source_days_sha_verified": 92,
        "official_K_rows_reconciled": 0, "T12_eligible": False,
        "official_c1_denominator_established": False,
        "by_venue": {v: {k: counts[v + ":" + k] for k in EXPECTED[v]} for v in FOCUS},
        "exceptions": sorted(candidates, key=lambda x: x["race_code"]),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--frozen-evidence", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    report = run(args.source_root, args.frozen_evidence)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"candidates": len(report["exceptions"]), "official_K_rows_reconciled": 0}))

if __name__ == "__main__":
    main()

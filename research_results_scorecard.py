"""Research-only retrospective scorecard against publicly published results.

This audit cannot certify pre-cutoff provenance or candidate prospective
accuracy. It scores *saved* baseline Top10 only; never regenerates candidate
predictions using post-race entry. Results are fetched solely for evaluation.
"""
import argparse
import csv
import io
import json
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from urllib.request import Request, urlopen

BASE = "https://boatracecsv.github.io/data/results/realtime/"
TOP = (1, 3, 5, 10)

def _actual(row):
    try:
        values = [int(row[f"{place}着_艇番"]) for place in range(1, 4)]
    except (ValueError, KeyError, TypeError):
        return None
    if len(set(values)) != 3 or any(x not in range(1, 7) for x in values):
        return None
    return "-".join(map(str, values))

def _results(day):
    day = date.fromisoformat(f"{day[:4]}-{day[4:6]}-{day[6:]}")
    url = BASE + day.strftime("%Y/%m/%d") + ".csv"
    with urlopen(Request(url, headers={"User-Agent":"BOAT-EDGE-CLEAN-RESEARCH-AUDIT/1.0"}),
                 timeout=20) as resp:
        if resp.status != 200:
            raise ValueError("results HTTP error")
        raw = resp.read(5_000_001)
        if len(raw) > 5_000_000:
            raise ValueError("results too large")
    rows = list(csv.DictReader(io.StringIO(raw.decode("utf-8-sig"))))
    seen = set()
    result = {}
    for row in rows:
        code = row.get("レースコード", "")
        if len(code) != 12 or not code.isascii() or not code.isdigit() or not code.startswith(day.strftime("%Y%m%d")):
            continue
        if code in seen:
            raise ValueError("duplicate result race_code")
        seen.add(code)
        result[code] = {"ticket": _actual(row), "method": row.get("決まり手"),
                        "entry": [row.get(f"{c}コース_艇番") for c in range(1,7)]}
    return result

def score(snapshots, results_by_day):
    totals = Counter()
    daily = defaultdict(Counter)
    methods = defaultdict(Counter)
    for record in snapshots:
        code = record["race_code"]
        totals["snapshots"] += 1
        row = results_by_day.get(code[:8], {}).get(code)
        if row is None:
            totals["missing_result"] += 1
            continue
        ticket = row["ticket"]
        if not ticket:
            totals["invalid_result"] += 1
            continue
        top = record["predictions"]
        if not isinstance(top, list) or len(top) != 10 or len(set(top)) != 10:
            totals["invalid_prediction"] += 1
            continue
        totals["scored_retrospective"] += 1
        daily[code[:8]]["n"] += 1
        method = row.get("method") or "unknown"
        methods[method]["n"] += 1
        for k in TOP:
            hit = int(ticket in top[:k])
            totals[f"top{k}_hits"] += hit
            daily[code[:8]][f"top{k}"] += hit
            methods[method][f"top{k}"] += hit
        entry = row.get("entry")
        if len(entry) == 6 and sorted(entry) == [str(i) for i in range(1, 7)]:
            totals["postrace_entry_available"] += 1
            if entry != [str(i) for i in range(1, 7)]:
                totals["postrace_entry_changed"] += 1
        else:
            totals["postrace_entry_missing"] += 1
    n = totals["scored_retrospective"]
    return {
        "counts": dict(totals),
        "top_rates": {str(k): totals[f"top{k}_hits"] / n if n else None for k in TOP},
        "by_day": {k: dict(v) for k,v in sorted(daily.items())},
        "by_winning_method": {k: dict(v) for k,v in sorted(methods.items())},
        "prospective_verified": 0,
        "candidate_scored": 0,
        "warning": "Retrospective baseline only: outcome data must not be used as candidate input. Git dates are not independent first-seen proof."
    }

def evaluate(directory):
    snapshots = []
    for path in sorted(Path(directory).glob("*.json")):
        record = json.loads(path.read_text(encoding="utf-8"))
        if record.get("race_code") != path.stem:
            raise ValueError("snapshot filename mismatch")
        snapshots.append(record)
    days = sorted({x["race_code"][:8] for x in snapshots})
    results = {}
    errors = {}
    for day in days:
        try:
            results[day] = _results(day)
        except (OSError, TimeoutError, ValueError, UnicodeError) as exc:
            errors[day] = type(exc).__name__
    report = score(snapshots, results)
    report["result_source_errors"] = errors
    report["days_requested"] = days
    return report

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("snapshot_directory")
    args = parser.parse_args()
    print(json.dumps(evaluate(args.snapshot_directory), ensure_ascii=False, indent=2))

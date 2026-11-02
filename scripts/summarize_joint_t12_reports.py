"""Summarize observed T-12 research reports; never infer missing successes."""
import argparse
import json
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

from scripts.joint_t12_failure_reason import classify


def has_verified_complete_pair(item):
    if item.get("both_complete_before_t12") is not True:
        return False
    if not all(item.get(key) is True for key in (
            "originals_hash_verified", "exhibition_complete", "odds_120_complete")):
        return False
    try:
        cutoff = datetime.fromisoformat(item["cutoff_jst"])
        before = datetime.fromisoformat(item["before_received_jst"])
        odds = datetime.fromisoformat(item["odds_received_jst"])
        if any(ts.utcoffset() != timedelta(hours=9) for ts in (cutoff, before, odds)):
            return False
        return before <= cutoff and odds <= cutoff
    except (KeyError, ValueError, TypeError):
        return False


def summarize(report_dir):
    root = Path(report_dir)
    files = sorted(root.glob("joint_*.json"))
    counts = Counter()
    races = set()
    attempts = set()
    success = 0
    malformed = 0
    details = []
    for path in files:
        try:
            item = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(item, dict):
                raise ValueError("not an object")
            attempt = item.get("attempt")
            race = item.get("race_code")
            if not isinstance(attempt, int) or isinstance(attempt, bool) or attempt < 1:
                raise ValueError("missing attempt")
            if not isinstance(race, str) or len(race) != 12 or not race.isdigit():
                raise ValueError("missing race")
            is_success = has_verified_complete_pair(item)
            category = "complete_pair" if is_success else item.get("failure_category")
            if not isinstance(category, str) or category not in (
                "complete_pair", "cutoff", "transport", "http_unresolved",
                "storage_or_io_unresolved", "audit_invalid", "unknown"):
                category = classify(item.get("status"), item.get("error") or item.get("error_type"))
            if not is_success and item.get("both_complete_before_t12") is True:
                category = "audit_invalid"
            elif not is_success and category == "complete_pair":
                category = "unknown"
            if (race, attempt) in attempts:
                raise ValueError("duplicate identity")
            attempts.add((race, attempt))
            races.add(race)
            counts[category] += 1
            success += int(is_success)
            details.append({"race_code": race, "attempt": attempt, "category": category})
        except (ValueError, TypeError, UnicodeError, OSError, json.JSONDecodeError):
            malformed += 1
    return {
        "evidence_scope": "local joint_*.json only; not all historical workflow runs",
        "report_files": len(files),
        "valid_attempt_reports": sum(counts.values()),
        "invalid_or_duplicate_reports": malformed,
        "distinct_races_in_reports": len(races),
        "complete_pair_attempts": success,
        "category_counts": dict(sorted(counts.items())),
        "details": details,
        "historical_success_rate": None,
        "forecast_usable": False,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--reports", default="reports")
    parser.add_argument("--output", default="reports/t12_summary.json")
    args = parser.parse_args()
    result = summarize(args.reports)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))

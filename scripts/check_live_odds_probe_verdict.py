"""Fail operational odds checks that produced no validated HTTP 200 evidence.

Executed only for admitted unattended schedule / scheduled-upstream runs.
The raw observation artifact is uploaded even if this check fails.
"""
import json
import sys
from pathlib import Path

from summarize_live_odds_history import consistent_attempts


def verdict(record):
    if not isinstance(record, dict) or record.get("source_status") != "ok":
        return "source_unavailable"
    samples = record.get("samples")
    if not isinstance(samples, list) or not samples:
        return "no_eligible_races"
    for sample in samples:
        if not isinstance(sample, dict):
            continue
        code = sample.get("race_code")
        attempts = sample.get("attempts")
        if (isinstance(code, str) and len(code) == 12 and code.isdigit()
                and consistent_attempts(attempts)
                and attempts[-1]["state"] == "valid_200"
                and attempts[-1]["http"] == 200):
            return "valid_200_observed"
    return "no_valid_200"


def main():
    record = json.loads(Path("live_odds_metrics.json").read_text(encoding="utf-8"))
    result = verdict(record)
    print("LIVE_ODDS_OPERATIONAL_VERDICT " + json.dumps(
        {"verdict": result, "source_status": record.get("source_status")},
        ensure_ascii=False), flush=True)
    summary = __import__("os").environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as out:
            out.write("\\n### Operational live odds verdict\\n\\n" + result + "\\n")
    if result != "valid_200_observed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()

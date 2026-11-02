"""Render source-backed T12 reaudit outcomes without inventing success rates."""
import argparse
import json
from pathlib import Path


def format_reaudit(data):
    if not isinstance(data, dict) or data.get("full_history_verified") is not False:
        raise ValueError("invalid scoped reaudit")
    rows = data.get("artifact_results")
    if not isinstance(rows, list):
        raise ValueError("missing artifact results")
    verified = 0
    unresolved = 0
    checked = 0
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("invalid artifact row")
        count = row.get("verified_complete_pairs")
        status = row.get("status")
        if type(count) is not int or count < 0:
            raise ValueError("invalid verified count")
        if status == "source_reaudit_complete":
            checked += 1
            verified += count
        elif status == "source_reaudit_unresolved" and count == 0:
            unresolved += 1
        else:
            raise ValueError("invalid audit status")
    if data.get("verified_complete_pair_attempts_in_inspected_artifacts") != verified:
        raise ValueError("verified totals mismatch")
    return ("## T−12 archived source re-audit (retained artifacts only)\n\n"
            "| Measure | Count |\n|---|---:|\n"
            f"| Archives independently examined | {checked} |\n"
            f"| Archives unresolved | {unresolved} |\n"
            f"| Independently verified complete attempt pairs | {verified} |\n\n"
            "**Historical T−12 success rate: not determined.** "
            "Expired or missing artifacts and unobserved runs are not treated as failures. "
            "Source verification is research-only and does not authorize live forecasts.\n")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("report")
    p.add_argument("summary")
    args = p.parse_args()
    report = json.loads(Path(args.report).read_text(encoding="utf-8"))
    with Path(args.summary).open("a", encoding="utf-8") as out:
        out.write(format_reaudit(report))

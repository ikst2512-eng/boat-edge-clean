"""Fail-closed historical race evidence preflight for optional manual Gemini research."""
import argparse
import json
import re
from pathlib import Path
from four_mode_frozen_diagnostic import compare_race


def preflight(code, comparator=compare_race):
    verdict = {"race_code": code, "status": "invalid_code", "formal": False,
               "production_change_allowed": False, "remote_first_seen_verified": False}
    if isinstance(code, str) and re.fullmatch(r"20[0-9]{10}", code):
        case = comparator(code)
        if isinstance(case, dict) and case.get("status") == "historical_comparison_only" and case.get("formal") is False and case.get("remote_first_seen_verified") is False:
            verdict["status"] = "historical_comparison_only"
            verdict["winning_ticket"] = case.get("winning_ticket")
        else:
            verdict["status"] = "unverified_or_missing_historical_case"
    return verdict


def main():
    p = argparse.ArgumentParser()
    p.add_argument("race_code")
    p.add_argument("--output", type=Path, default=Path("ai_frozen_race_preflight.json"))
    args = p.parse_args()
    report = preflight(args.race_code)
    args.output.write_text(json.dumps(report, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    print("Frozen race preflight:", report["status"])
    if report["status"] != "historical_comparison_only":
        p.error("Frozen race evidence unavailable: Gemini request must not run")


if __name__ == "__main__":
    main()

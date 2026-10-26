"""Research-only integration: collect existing baseline then freeze paired forecasts.

Not scheduled, not imported by production. Commit and push must be completed
before cutoff independently; this script does not certify external receipt.
"""
import argparse
import json
from datetime import datetime
from research_model import JST
from collect_research_daily import collect, validate_run_counts
from research_prospective_pair_capture import capture

def run(day):
    collected = collect(day)
    validate_run_counts(collected)
    frozen = capture(day, "research_snapshots", "research_prospective_pairs",
                     now=datetime.now(JST))
    return {"day": day, "baseline": collected, "paired": frozen,
            "requires_git_publication_before_cutoff": True,
            "prospective_verified": False}

if __name__ == "__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--day", default=datetime.now(JST).strftime("%Y%m%d"))
    args=parser.parse_args()
    print(json.dumps(run(args.day),ensure_ascii=False))

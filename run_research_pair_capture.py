"""Research-only same-run orchestration, not connected to a schedule.

Call on a research branch before all race cutoffs. The production daily
collector and formal Fresh pipeline are not changed. Never rewrites snapshots.
"""
import argparse
import json
from datetime import datetime
from research_model import JST
from research_prospective_pair_capture import capture

def run(day, snapshots="research_snapshots", output="research_prospective_pairs"):
    now = datetime.now(JST)
    summary = capture(day, snapshots, output, now=now)
    return {"day": day, "capture_at": now.isoformat(), **summary,
            "scheduled": False, "external_timestamp_proven": False,
            "note": "Commit and independently timestamp output before cutoff; local files alone are not evidence."}

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--day", default=datetime.now(JST).strftime("%Y%m%d"))
    parser.add_argument("--snapshots", default="research_snapshots")
    parser.add_argument("--output", default="research_prospective_pairs")
    args = parser.parse_args()
    print(json.dumps(run(args.day, args.snapshots, args.output), ensure_ascii=False))

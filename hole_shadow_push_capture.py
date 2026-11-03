"""Read-only shadow capture for newly added forecasts in a GitHub push.

The run log/artifact can be used for subsequent independent provenance review.
Never labels a Github run timestamp as proof of original predeadline publication.
"""
import argparse
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from hole_shadow_prospective_gate import freeze

PATTERN = re.compile(r"four_mode_forecasts/(20[0-9]{10})\.json\Z")


def added_forecast_codes(before, after, git_output=None):
    if not all(re.fullmatch(r"[0-9a-f]{40}", s) for s in (before, after)):
        raise ValueError("invalid_commit_refs")
    if before == "0" * 40:
        raise ValueError("first_push_requires_manual_review")
    if git_output is None:
        git_output = subprocess.check_output(
            ["git", "diff", "--name-only", "--diff-filter=A",
             before, after, "--", "four_mode_forecasts/"], text=True)
    codes = []
    for line in git_output.splitlines():
        match = PATTERN.fullmatch(line)
        if match:
            codes.append(match.group(1))
    return sorted(set(codes))


def capture(root, before, after, event_id, received_at=None, git_output=None):
    received_at = received_at or datetime.now(timezone.utc)
    if received_at.tzinfo is None or not str(event_id).isdigit():
        raise ValueError("invalid_run_metadata")
    codes = added_forecast_codes(before, after, git_output)
    records = [freeze(code, root, received_at) for code in codes]
    return {"schema": "HOLE_PUSH_SHADOW_RECEIPT_V1",
            "status": "research_capture_only",
            "event_run_id": str(event_id),
            "push_before_sha": before, "push_after_sha": after,
            "runner_received_at_utc": received_at.astimezone(timezone.utc).isoformat(),
            "new_forecast_files": len(codes), "frozen_count": sum(
                r.get("status") == "shadow_frozen_unverified" for r in records),
            "records": records, "formal": False, "prospective_verified": False,
            "production_forecast_changed": False,
            "warning": "This is runner-time provenance, not verified first remote receipt; bot pushes may not trigger this workflow."}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--before", required=True)
    parser.add_argument("--after", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--root", default=".")
    parser.add_argument("--output", default="hole_shadow_push_receipt.json")
    args = parser.parse_args()
    report = capture(Path(args.root), args.before, args.after, args.run_id)
    Path(args.output).write_text(json.dumps(report, ensure_ascii=False,
                                      sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"],
                      "new_forecast_files": report["new_forecast_files"],
                      "frozen_count": report["frozen_count"]}, sort_keys=True))

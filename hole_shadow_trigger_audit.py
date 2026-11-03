"""Audit Git history for newly-added forecast archives without asserting trigger success.

Designed for CI verification of observability; a later successful GitHub workflow
run does not prove that an earlier collection push triggered a capture.
"""
import argparse
import json
import re
import subprocess
from datetime import datetime, timezone

VALID = re.compile(r"four_mode_forecasts/(20[0-9]{10})\.json\Z")
SHA = re.compile(r"[0-9a-f]{40}\Z")


def inspect_range(before, after, runner=None):
    if not SHA.fullmatch(before) or not SHA.fullmatch(after) or before == "0" * 40:
        raise ValueError("invalid_commit_range")
    run = runner or subprocess.check_output
    output = run(["git", "diff", "--name-status", "--diff-filter=A", before, after,
                  "--", "four_mode_forecasts/"], text=True)
    codes = sorted({m.group(1) for line in output.splitlines()
                    if (m := VALID.fullmatch(line.removeprefix("A\t"))) is not None})
    return {"status": "git_addition_audit_only", "base": before, "head": after,
            "new_forecast_count": len(codes), "new_forecast_codes": codes,
            "capture_workflow_triggered": None,
            "independent_predeadline_proof": False,
            "formal": False,
            "warning": "Git differences do not verify workflow dispatch or first external receipt."}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--before", required=True)
    p.add_argument("--after", required=True)
    a = p.parse_args()
    print(json.dumps(inspect_range(a.before, a.after),
                     ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()

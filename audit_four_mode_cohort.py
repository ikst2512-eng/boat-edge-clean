"""Read-only four-mode local Git chronology cohort. Never formalizes picks."""
import argparse
import json
import subprocess
from collections import Counter
from pathlib import Path
from audit_four_mode_first_add import inspect

ROOT = Path(__file__).resolve().parent

def run(root=ROOT):
    files = subprocess.check_output(
        ["git", "ls-files", "--", "four_mode_forecasts/*.json"],
        cwd=root, text=True).splitlines()
    paths = sorted(x for x in files if x.startswith("four_mode_forecasts/")
                   and x.endswith(".json") and x != "four_mode_forecasts/capture_status.json")
    reasons = Counter()
    samples = {}
    passed = 0
    for path in paths:
        try:
            inspect(path, root=root)
            passed += 1
        except (ValueError, KeyError, TypeError, OSError, subprocess.CalledProcessError,
                json.JSONDecodeError) as exc:
            reason = str(exc) if isinstance(exc, ValueError) else type(exc).__name__
            reasons[reason] += 1
            samples.setdefault(reason, path)
    return {"schema": "CLEAN_FOUR_MODE_LOCAL_AUDIT_COHORT_V1",
            "files_checked": len(paths), "local_chronology_passed": passed,
            "rejected": len(paths)-passed, "rejection_reasons": dict(sorted(reasons.items())),
            "rejection_samples": samples, "remote_first_seen_verified": 0,
            "formal_performance_eligible": 0}

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--strict", action="store_true")
    args = p.parse_args()
    result = run()
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    if args.strict and result["rejected"]:
        raise SystemExit(1)

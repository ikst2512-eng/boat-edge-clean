"""Capture research-only hole shadow tickets immediately after verified main publication.

Runs in the existing collection job: no reliance on bot-triggered push workflows.
Does not claim independent first receipt or future predictive performance.
"""
import argparse
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from hole_shadow_prospective_gate import freeze

SHA = re.compile(r"[a-f0-9]{40}\Z")
PATH = re.compile(r"four_mode_forecasts/(20[0-9]{10})\.json\Z")


def capture_published(root, evidence_path, now=None, git=None):
    root = Path(root)
    path = Path(evidence_path)
    if path.is_symlink() or not path.is_file():
        return {"status": "no_publication_evidence", "formal": False, "records": []}
    evidence = json.loads(path.read_text(encoding="utf-8"))
    if evidence.get("outcome") != "pushed_to_main":
        return {"status": "not_published", "formal": False, "records": []}
    commit = evidence.get("commit_sha")
    if not isinstance(commit, str) or not SHA.fullmatch(commit):
        raise ValueError("invalid_publication_commit")
    if type(evidence.get("added_forecasts")) is not int or not 0 < evidence["added_forecasts"] <= 500:
        raise ValueError("invalid_added_count")
    git = git or (lambda args: subprocess.check_output(["git", *args], text=True).strip())
    head = git(["rev-parse", "HEAD"])
    if head != commit:
        raise ValueError("publication_head_mismatch")
    added = git(["diff-tree", "--no-commit-id", "--name-only", "--diff-filter=A",
                 "-r", commit, "--", "four_mode_forecasts/"]).splitlines()
    if len(added) != evidence["added_forecasts"] or not added:
        raise ValueError("publication_addition_mismatch")
    if any(PATH.fullmatch(name) is None for name in added):
        raise ValueError("invalid_added_forecast_path")
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError("naive_capture_time")
    records = []
    for name in added:
        code = PATH.fullmatch(name).group(1)
        try:
            item = freeze(code, root, now)
            if not isinstance(item, dict) or item.get("race_code") != code:
                raise ValueError("invalid_shadow_race_identity")
        except (ValueError, TypeError, KeyError, UnicodeError, OSError,
                subprocess.CalledProcessError) as exc:
            # A single broken race must not erase already valid same-job
            # shadows. Record the failure and retain a nonzero exit verdict.
            item = {"race_code": code, "status": "validation_error",
                    "error_type": type(exc).__name__}
        records.append(item)
    return {"schema": "HOLE_SHADOW_PUBLISHED_SAME_JOB_V1",
            "status": "research_only_after_confirmed_push",
            "publication_commit_sha": commit, "capture_run_at_utc": now.isoformat(),
            "published_new_count": len(added),
            "frozen_count": sum(r.get("status") == "shadow_frozen_unverified" for r in records),
            "validation_error_count": sum(r.get("status") == "validation_error" for r in records),
            "records": records, "formal": False, "production_forecast_changed": False,
            "independent_first_receipt_verified": False,
            "warning": "Same-job post-push snapshot is not independent proof of predeadline publication."}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--evidence", default="four-mode-evidence/publication.json")
    parser.add_argument("--output", default="four-mode-evidence/hole-shadow.json")
    args = parser.parse_args()
    report = capture_published(args.root, args.evidence)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "frozen_count": report.get("frozen_count", 0),
                      "validation_error_count": report.get("validation_error_count", 0)},
                     ensure_ascii=False, sort_keys=True))
    if report.get("validation_error_count", 0):
        raise SystemExit(2)

"""Diagnostic-only local first-add checks for post-fix prospective records.

The legacy cohort stays rejected. This never certifies remote first-seen or
promotes any research candidate to formal scoring.
"""
import json
from pathlib import Path
from audit_clean_first_add import ROOT, PATTERN, audit_records

POST_FIX_START = "20261105"


def post_fix_paths(root=ROOT):
    directory = Path(root) / "prospective_predictions"
    return sorted(
        "prospective_predictions/" + entry.name
        for entry in directory.glob("*.json")
        if PATTERN.fullmatch("prospective_predictions/" + entry.name)
        and entry.name[:8] >= POST_FIX_START
    )


def inspect_post_fix(root=ROOT, auditor=audit_records):
    paths = post_fix_paths(root)
    if not paths:
        return {
            "schema": "CLEAN_POST_FIX_LOCAL_EVIDENCE_V1",
            "post_fix_start": POST_FIX_START,
            "status": "pending_no_new_capture",
            "candidate_count": 0,
            "local_audit_passed": 0,
            "rejected": 0,
            "remote_first_seen_verified": False,
            "formal": False,
        }
    report = auditor(paths, root)
    return {
        **report,
        "schema": "CLEAN_POST_FIX_LOCAL_EVIDENCE_V1",
        "post_fix_start": POST_FIX_START,
        "candidate_count": len(paths),
        "status": (
            "local_first_add_passed"
            if report["local_audit_passed"] == len(paths)
            and report["rejected"] == 0
            else "post_fix_evidence_rejected"
        ),
        "remote_first_seen_verified": False,
        "formal": False,
    }


if __name__ == "__main__":
    output = inspect_post_fix()
    print(json.dumps(output, ensure_ascii=False))
    if output["status"] != "local_first_add_passed":
        raise SystemExit("Post-fix candidate evidence not yet locally certified")

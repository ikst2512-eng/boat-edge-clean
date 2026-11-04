"""Diagnostic-only local first-add checks for post-fix prospective records.

The legacy cohort stays rejected. This never certifies remote first-seen or
promotes any research candidate to formal scoring.
"""
import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from audit_clean_first_add import ROOT, PATTERN, audit_records, inspect

POST_FIX_START = "20261105"


def post_fix_paths(root=ROOT):
    directory = Path(root) / "prospective_predictions"
    return sorted(
        "prospective_predictions/" + entry.name
        for entry in directory.glob("*.json")
        if PATTERN.fullmatch("prospective_predictions/" + entry.name)
        and entry.name[:8] >= POST_FIX_START
    )


def inspect_post_fix_record(path, root=ROOT):
    """Require traceable input provenance on every post-fix local candidate."""
    result = inspect(path, root)
    candidate = json.loads((Path(root) / path).read_text(encoding="utf-8"))
    if candidate.get("validated") is not False:
        raise ValueError("post-fix research classification invalid")
    tickets = candidate.get("predictions")
    if (not isinstance(tickets, list) or len(tickets) != 10
            or not all(isinstance(t, str) and re.fullmatch(r"[1-6]-[1-6]-[1-6]", t)
                       and len(set(t.split("-"))) == 3 for t in tickets)
            or len(set(tickets)) != 10):
        raise ValueError("post-fix trifecta tickets invalid")
    kind = candidate.get("input_source_kind")
    if kind not in ("public_pre_race_csv", "nonofficial_openapi_v1"):
        raise ValueError("post-fix source kind missing or invalid")
    title = candidate.get("source_title_sha256")
    cards = candidate.get("source_cards_sha256")
    combined = candidate.get("input_sha256")
    digest = re.compile(r"^[0-9a-f]{64}$")
    if any(not isinstance(v, str) or not digest.fullmatch(v)
           for v in (title, cards, combined)):
        raise ValueError("post-fix source digest mismatch")
    calculated = hashlib.sha256((title + ":" + cards).encode()).hexdigest()
    if combined != calculated or (kind == "nonofficial_openapi_v1" and title != cards):
        raise ValueError("post-fix source digest mismatch")
    code = candidate.get("race_code")
    deadline_value = candidate.get("source_deadline_jst")
    if not (isinstance(code, str) and re.fullmatch(r"20[0-9]{10}", code)
            and 1 <= int(code[8:10]) <= 24
            and 1 <= int(code[10:12]) <= 12
            and isinstance(deadline_value, str)):
        raise ValueError("post-fix race identity invalid")
    try:
        deadline = datetime.fromisoformat(deadline_value)
    except ValueError as exc:
        raise ValueError("post-fix race identity invalid") from exc
    if deadline.strftime("%Y%m%d") != code[:8]:
        raise ValueError("post-fix race identity invalid")
    return {**result, "input_source_kind": kind,
            "source_title_sha256": title, "source_cards_sha256": cards,
            "input_sha256": combined,
            "raw_remote_receipt_verified": False}


def inspect_post_fix(root=ROOT, auditor=None):
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
    report = (audit_records(paths, root, inspector=inspect_post_fix_record)
              if auditor is None else auditor(paths, root))
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


def with_execution_receipt(report, root=ROOT, environ=None):
    """Attach audit-run correlation; never certify remote GitHub receipt."""
    env = os.environ if environ is None else environ
    head = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    if len(head) != 40 or any(ch not in "0123456789abcdef" for ch in head):
        raise ValueError("invalid checkout commit for post-fix audit")
    return {**report, "audit_run_id": env.get("GITHUB_RUN_ID") or None,
            "audit_event_name": env.get("GITHUB_EVENT_NAME") or None,
            "audit_checkout_sha": head,
            "remote_first_seen_verified": False, "formal": False}


def diagnostic_summary(report):
    """Bounded Action-log explanation; full evidence stays in JSON artifact."""
    return json.dumps({
        "status": report["status"],
        "candidate_count": report["candidate_count"],
        "rejection_reasons": report.get("rejection_reasons", {}),
        "by_day": report.get("by_day", {}),
    }, ensure_ascii=False, sort_keys=True)


if __name__ == "__main__":
    output = with_execution_receipt(inspect_post_fix())
    print(json.dumps(output, ensure_ascii=False))
    print("POST_FIX_DIAGNOSTIC " + diagnostic_summary(output), file=sys.stderr)
    if output["status"] != "local_first_add_passed":
        raise SystemExit("Post-fix candidate evidence not yet locally certified")

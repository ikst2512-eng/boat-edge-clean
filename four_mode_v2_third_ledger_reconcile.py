"""Fail-closed race-ID reconciliation between real capture artifacts and durable ledger.

Read ONLY existing independent stage reports; never recompute or reconstruct
candidate tickets from outcomes. Capture report is a bounded window, not a
complete lifetime inventory; the ledger may contain older entries.
"""
import argparse
import json
from pathlib import Path

def reconcile(capture, ledger):
    if (type(capture) is not dict or type(ledger) is not dict
            or capture.get("schema") != "V2_THIRD_RATE_FROZEN_NIGHTLY_ARTIFACT_AUDIT_V1"
            or ledger.get("schema") != "V2_THIRD_RATE_DURABLE_LEDGER_SCORE_V1"):
        raise ValueError("invalid_audit_schema")
    out = {
        "schema": "V2_THIRD_RATE_CAPTURE_LEDGER_RECONCILIATION_V1",
        "formal": False, "remote_first_seen_independently_verified": False,
        "production_promotion_allowed": False,
        "status": "unverified",
        "capture_frozen": capture.get("frozen"),
        "ledger_frozen": ledger.get("frozen"),
        "capture_codes": [], "missing_from_ledger": [],
        "additional_ledger_codes": [],
        "warning": "A bounded run inventory and Git history are not independent remote-first-seen proof.",
    }
    left = capture.get("race_codes_frozen")
    right = ledger.get("race_codes_frozen")
    if (type(left) is not list or type(right) is not list
            or any(type(x) is not str or len(x) != 12 or not x.isdigit()
                   for x in left + right)
            or len(set(left)) != len(left) or len(set(right)) != len(right)
            or type(capture.get("frozen")) is not int or type(ledger.get("frozen")) is not int
            or capture["frozen"] != len(left) or ledger["frozen"] != len(right)):
        raise ValueError("invalid_frozen_race_rosters")
    out["capture_codes"] = sorted(left)
    out["missing_from_ledger"] = sorted(set(left) - set(right))
    out["additional_ledger_codes"] = sorted(set(right) - set(left))
    # Matching IDs are not sufficient when either upstream producer has an
    # unknown/contradictory result status. Only an explicitly scored bounded
    # capture and a valid durable rollup can establish a matched roster.
    capture_scored = capture.get("status") == "frozen_artifacts_scored_limited_cohort"
    ledger_scored = ledger.get("status") == "durable_frozen_evidence_scored"
    if (not capture_scored
            or capture.get("cohort_completeness_verified") is not True
            or capture.get("missing_or_failed_artifacts")
            or capture.get("bad_validation_runs")):
        out["status"] = "incomplete_capture_inventory"
    elif (not ledger_scored or ledger.get("invalid_files")):
        out["status"] = "invalid_or_unavailable_ledger"
    elif out["missing_from_ledger"]:
        out["status"] = "frozen_predictions_missing_from_ledger"
    elif left:
        out["status"] = "bounded_frozen_roster_matched"
    else:
        out["status"] = "no_frozen_predictions_to_compare"
    return out


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--capture", required=True, type=Path)
    parser.add_argument("--ledger", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    report = reconcile(json.loads(args.capture.read_text(encoding="utf-8")),
                       json.loads(args.ledger.read_text(encoding="utf-8")))
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n",
                           encoding="utf-8")
    print("V2_THIRD_RATE_LEDGER_RECONCILIATION=" + json.dumps(report, sort_keys=True))
    if report["status"] in ("frozen_predictions_missing_from_ledger",
                            "invalid_or_unavailable_ledger"):
        raise SystemExit(2)

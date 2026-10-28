#!/usr/bin/env python3
"""Offline check that archived evidence remains internally restorable and tamper evident."""
import argparse
import hashlib
import json
from pathlib import Path


def verify(comparison, payouts):
    if comparison.get("schema") != "CLEAN_LEGACY_RESULT_COMPARISON_V1":
        raise ValueError("unexpected comparison schema")
    if payouts.get("schema") != "CLEAN_LEGACY_PAYOUT_EVIDENCE_V1":
        raise ValueError("unexpected payout schema")
    for key in ("legacy_tree_sha", "clean_tree_sha"):
        if comparison.get(key) != payouts.get(key):
            raise ValueError("tree reference mismatch")
    matches = {}
    for row in comparison["records"]:
        if row["status"] == "FINISH_ORDER_MATCH":
            code = row["race_code"]
            if code in matches:
                raise ValueError("duplicate matched race")
            matches[code] = row
    seen = set()
    for row in payouts["records"]:
        code = row["race_code"]
        if code in seen or code not in matches:
            raise ValueError("orphan or duplicate payout")
        seen.add(code)
        parent = matches[code]
        if row["legacy_result_sha256"] != parent["legacy_sha256"]:
            raise ValueError("payout hash disagrees with source")
        if row["legacy_result_path"] != parent["legacy_path"]:
            raise ValueError("payout original path disagrees")
        if row["payout_yen_per_100"] != parent["legacy_payout_yen_per_100"]:
            raise ValueError("payout value disagrees")
    if len(seen) != payouts["payout_record_count"]:
        raise ValueError("payout count mismatch")
    return {"matched_results": len(matches), "linked_payouts": len(seen),
            "referential_integrity_passed": True,
            "raw_original_bytes_restored": False,
            "official_payout_verified": False,
            "delete_authorized": False}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--comparison", required=True)
    p.add_argument("--payouts", required=True)
    p.add_argument("--output", required=True)
    args = p.parse_args()
    comparison = json.loads(Path(args.comparison).read_text())
    payouts = json.loads(Path(args.payouts).read_text())
    result = verify(comparison, payouts)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))


if __name__ == "__main__":
    main()

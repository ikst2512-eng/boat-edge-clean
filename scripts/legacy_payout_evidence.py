#!/usr/bin/env python3
"""Export isolated, provenance-linked LEGACY payout evidence; never changes CLEAN results."""
import argparse
import json
import re
from pathlib import Path

CODE = re.compile(r"^[0-9]{12}$")
HASH = re.compile(r"^[0-9a-f]{64}$")


def build_ledger(report):
    if report.get("schema") != "CLEAN_LEGACY_RESULT_COMPARISON_V1":
        raise ValueError("unsupported comparison report")
    rows = []
    seen = set()
    for record in report["records"]:
        if record.get("status") != "FINISH_ORDER_MATCH":
            continue
        code = record.get("race_code")
        payout = record.get("legacy_payout_yen_per_100")
        digest = record.get("legacy_sha256")
        path = record.get("legacy_path")
        if not isinstance(code, str) or not CODE.fullmatch(code) or code in seen:
            raise ValueError("invalid or duplicate race")
        seen.add(code)
        if not isinstance(digest, str) or not HASH.fullmatch(digest):
            raise ValueError("missing original SHA256")
        expected = f"data/site_results/{code[:8]}-{code[8:10]}-{code[10:]}.json"
        if path != expected:
            raise ValueError("unexpected legacy original path")
        if type(payout) is not int or payout <= 0:
            # Unknown payout must stay unknown; no back-filling with guessed values.
            continue
        rows.append({"race_code": code, "payout_yen_per_100": payout,
                     "legacy_result_path": path, "legacy_result_sha256": digest,
                     "origin": "legacy_site_result_unverified_external_source",
                     "verified_against_official_source": False})
    return {"schema": "CLEAN_LEGACY_PAYOUT_EVIDENCE_V1",
            "legacy_tree_sha": report["legacy_tree_sha"],
            "clean_tree_sha": report["clean_tree_sha"],
            "compared_result_count": report["compared"],
            "payout_record_count": len(rows),
            "scope": "research_evidence_only_not_live_results_or_confirmed_ROI",
            "delete_authorized": False, "records": rows}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--comparison", required=True)
    parser.add_argument("--output", default="legacy_payout_evidence.json")
    args = parser.parse_args()
    payload = json.loads(Path(args.comparison).read_text(encoding="utf-8"))
    report = build_ledger(payload)
    p = Path(args.output)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"payout_records": report["payout_record_count"],
                      "compared": report["compared_result_count"]}))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Non-destructive byte-level legacy-vs-CLEAN result comparison.

Produces a report with explicit unknowns; does not imply forecast equivalence,
payout parity, predeadline proof, or safe deletion.
"""
import argparse
import base64
import hashlib
import json
import os
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

LEGACY = "ikst2512-eng/boat-edge"
CLEAN = "ikst2512-eng/boat-edge-clean"


def github_bytes(repo, blob_sha):
    url = f"https://api.github.com/repos/{repo}/git/blobs/{blob_sha}"
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "clean-result-audit"}
    if os.getenv("GH_TOKEN"):
        headers["Authorization"] = "Bearer " + os.environ["GH_TOKEN"]
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=30) as response:
        blob = json.load(response)
    if blob.get("encoding") != "base64" or blob.get("sha") != blob_sha:
        raise ValueError("GitHub blob identity/encoding mismatch")
    return base64.b64decode(blob["content"], validate=False)


def compare_record(code, legacy_bytes, clean_bytes):
    legacy = json.loads(legacy_bytes)
    clean = json.loads(clean_bytes)
    old_key = f"{code[:8]}-{code[8:10]}-{code[10:]}"
    if legacy.get("race_key") != old_key or clean.get("race_code") != code:
        raise ValueError(f"race identity mismatch: {code}")
    left, right = legacy.get("finish_order"), clean.get("finish_order")
    valid = lambda x: isinstance(x, list) and len(x) == 3 and all(
        type(n) is int and n in range(1, 7) for n in x) and len(set(x)) == 3
    if not valid(left) or not valid(right):
        state = "INVALID_OR_MISSING_FINISH_ORDER"
    else:
        state = "FINISH_ORDER_MATCH" if left == right else "FINISH_ORDER_CONFLICT"
    return {
        "race_code": code, "status": state,
        "legacy_sha256": hashlib.sha256(legacy_bytes).hexdigest(),
        "clean_sha256": hashlib.sha256(clean_bytes).hexdigest(),
        "byte_identical": legacy_bytes == clean_bytes,
        "legacy_finish_order": left, "clean_finish_order": right,
        "legacy_payout_yen_per_100": legacy.get("trifecta_payout_yen_per_100"),
        "clean_payout_yen_per_100": clean.get("trifecta_payout_yen_per_100"),
        "payout_comparable": isinstance(legacy.get("trifecta_payout_yen_per_100"), int)
          and isinstance(clean.get("trifecta_payout_yen_per_100"), int),
        "source_equivalence_verified": False,
        "prediction_equivalence_verified": False,
        "restore_test_passed": False,
        "delete_authorized": False,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--crosswalk", required=True, help="Output from legacy_race_crosswalk.py")
    parser.add_argument("--output", default="legacy_result_comparison.json")
    parser.add_argument("--limit", type=int, default=0, help="0 means all")
    args = parser.parse_args()
    index = json.loads(Path(args.crosswalk).read_text(encoding="utf-8"))
    if index.get("schema") != "CLEAN_LEGACY_RACE_CROSSWALK_V2":
        raise SystemExit("Unexpected crosswalk schema")
    records = []
    all_races = index["matched_races"]
    selected = all_races[:args.limit] if args.limit > 0 else all_races
    for item in selected:
        code = item["race_code"]
        legacy_path = f"data/site_results/{code[:8]}-{code[8:10]}-{code[10:]}.json"
        clean_path = f"confirmed_results/{code}.json"
        paths = {v["path"] for v in item["legacy"]}
        clean_paths = {v["path"] for v in item["clean"]}
        if legacy_path not in paths or clean_path not in clean_paths:
            records.append({"race_code": code, "status": "RESULT_PAIR_MISSING",
                            "delete_authorized": False})
            continue
        try:
            old_sha = next(v["git_blob_sha1"] for v in item["legacy"] if v["path"] == legacy_path)
            new_sha = next(v["git_blob_sha1"] for v in item["clean"] if v["path"] == clean_path)
            old = github_bytes(LEGACY, old_sha)
            new = github_bytes(CLEAN, new_sha)
            comparison = compare_record(code, old, new)
            comparison["legacy_git_blob_sha1"] = old_sha
            comparison["clean_git_blob_sha1"] = new_sha
            comparison["legacy_path"] = legacy_path
            comparison["clean_path"] = clean_path
            records.append(comparison)
        except (ValueError, OSError, json.JSONDecodeError) as exc:
            records.append({"race_code": code, "status": "FETCH_OR_VALIDATION_ERROR",
                            "error": str(exc), "delete_authorized": False})
    summary = {}
    for item in records:
        summary[item["status"]] = summary.get(item["status"], 0) + 1
    report = {"schema": "CLEAN_LEGACY_RESULT_COMPARISON_V1",
              "generated_at_utc": datetime.now(timezone.utc).isoformat(),
              "legacy_tree_sha": index["legacy_tree_sha"],
              "clean_tree_sha": index["clean_tree_sha"],
              "scope": "result_finish_order_only; no forecast or provenance equivalence",
              "compared": len(records), "summary": summary,
              "delete_authorized": False, "records": records}
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"compared": len(records), "summary": summary}, ensure_ascii=False))


if __name__ == "__main__":
    main()

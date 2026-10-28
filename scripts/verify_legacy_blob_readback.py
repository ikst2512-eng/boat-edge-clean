#!/usr/bin/env python3
"""Read back immutable legacy source blobs and verify byte SHA-256 against audit.

This checks upstream Git object retrievability, NOT independent backup restoration.
"""
import argparse
import hashlib
import json
from pathlib import Path
from scripts.legacy_result_compare import github_bytes, LEGACY


def verify_blob_readback(comparison, fetcher=github_bytes):
    if comparison.get("schema") != "CLEAN_LEGACY_RESULT_COMPARISON_V1":
        raise ValueError("unexpected comparison")
    checked = []
    seen = set()
    for row in comparison["records"]:
        if row.get("status") != "FINISH_ORDER_MATCH":
            continue
        code, blob, digest = (row.get("race_code"), row.get("legacy_git_blob_sha1"),
                              row.get("legacy_sha256"))
        if not code or code in seen or not blob or not digest:
            raise ValueError("missing or duplicate immutable identity")
        seen.add(code)
        raw = fetcher(LEGACY, blob)
        actual = hashlib.sha256(raw).hexdigest()
        if actual != digest:
            raise ValueError(f"byte SHA-256 mismatch: {code}")
        data = json.loads(raw)
        if data.get("race_key") != f"{code[:8]}-{code[8:10]}-{code[10:]}":
            raise ValueError(f"race identity mismatch: {code}")
        if data.get("finish_order") != row.get("legacy_finish_order"):
            raise ValueError(f"content mismatch: {code}")
        checked.append({"race_code": code, "git_blob_sha1": blob,
                        "sha256": digest, "verified": True})
    if len(checked) != comparison.get("summary", {}).get("FINISH_ORDER_MATCH"):
        raise ValueError("record count mismatch")
    return {"schema": "CLEAN_LEGACY_BLOB_READBACK_V1",
            "verified_legacy_blobs": len(checked),
            "all_sha256_valid": True,
            "independent_backup_restored": False,
            "delete_authorized": False,
            "records": checked}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--comparison", required=True)
    p.add_argument("--output", required=True)
    args = p.parse_args()
    comparison = json.loads(Path(args.comparison).read_text(encoding="utf-8"))
    report = verify_blob_readback(comparison)
    target = Path(args.output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"verified_legacy_blobs": report["verified_legacy_blobs"],
                      "all_sha256_valid": report["all_sha256_valid"],
                      "independent_backup_restored": False}))


if __name__ == "__main__":
    main()

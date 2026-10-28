#!/usr/bin/env python3
"""Create and restore an isolated tar archive of matched legacy result originals.

The archive is an ephemeral GitHub Actions artifact (90-day retention), not an
independent durable offsite backup. Does not cover Fresh or prediction evidence.
"""
import argparse
import hashlib
import io
import json
import tarfile
from pathlib import Path
from scripts.legacy_result_compare import github_bytes, LEGACY


def archive_and_verify(comparison, output, fetcher=github_bytes):
    if comparison.get("schema") != "CLEAN_LEGACY_RESULT_COMPARISON_V1":
        raise ValueError("invalid comparison schema")
    rows = [r for r in comparison["records"] if r.get("status") == "FINISH_ORDER_MATCH"]
    if len(rows) != comparison.get("summary", {}).get("FINISH_ORDER_MATCH"):
        raise ValueError("count mismatch")
    if not rows:
        raise ValueError("no originals")
    entries = {}
    for row in rows:
        code = row.get("race_code")
        if not isinstance(code, str) or len(code) != 12 or not code.isdigit() or code in entries:
            raise ValueError("invalid or duplicated race code")
        sha = row["legacy_sha256"]
        raw = fetcher(LEGACY, row["legacy_git_blob_sha1"])
        if len(raw) > 20000 or hashlib.sha256(raw).hexdigest() != sha:
            raise ValueError("source original invalid")
        doc = json.loads(raw)
        if doc.get("race_key") != f"{code[:8]}-{code[8:10]}-{code[10:]}":
            raise ValueError("race identity mismatch")
        entries[code] = (raw, sha)
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(path, "w:gz") as tar:
        for code, (raw, _) in sorted(entries.items()):
            info = tarfile.TarInfo(f"results/{code}.json")
            info.size = len(raw)
            info.mtime = 0
            tar.addfile(info, io.BytesIO(raw))
    # Test independent extraction from the produced archive, not from GitHub.
    with tarfile.open(path, "r:gz") as tar:
        members = tar.getmembers()
        if len(members) != len(entries):
            raise ValueError("archive entry count mismatch")
        observed = set()
        for member in members:
            if not member.isfile() or member.name.count("/") != 1:
                raise ValueError("unexpected archive entry")
            code = member.name.removeprefix("results/").removesuffix(".json")
            if member.name != f"results/{code}.json" or code not in entries or code in observed:
                raise ValueError("unknown/duplicate archive entry")
            observed.add(code)
            data = tar.extractfile(member).read()
            if hashlib.sha256(data).hexdigest() != entries[code][1]:
                raise ValueError("restored hash mismatch")
        if observed != set(entries):
            raise ValueError("incomplete restore")
    return {"schema": "CLEAN_LEGACY_RESULT_ARCHIVE_RESTORE_V1",
            "original_count": len(entries), "restored_count": len(observed),
            "sha256_restore_passed": True,
            "archive_path": str(path),
            "durable_offsite_backup_verified": False,
            "fresh_prediction_evidence_preserved": False,
            "delete_authorized": False}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--comparison", required=True)
    p.add_argument("--archive", required=True)
    p.add_argument("--report", required=True)
    a = p.parse_args()
    report = archive_and_verify(json.loads(Path(a.comparison).read_text()), a.archive)
    Path(a.report).write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report))


if __name__ == "__main__":
    main()

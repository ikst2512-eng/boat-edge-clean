"""Research-only validation of V13 Actions artifacts. Never certifies formal Fresh."""
import argparse
import collections
import hashlib
import json
import re
import sys
import zipfile


def audit(path, expected_run_id=None, expected_sha=None):
    issues = []
    if expected_run_id is None:
        issues.append("MISSING_EXPECTED_RUN_ID")
    if expected_sha is None:
        issues.append("MISSING_EXPECTED_GIT_SHA")
    with zipfile.ZipFile(path) as archive:
        entries = archive.namelist()
        names = set(entries)
        if len(entries) != len(names):
            issues.append("DUPLICATE_ZIP_MEMBER")

        def read_json(name):
            if name not in names:
                issues.append("MISSING_" + name.upper().replace(".", "_"))
                return None
            try:
                value = json.loads(archive.read(name))
                if not isinstance(value, dict):
                    raise ValueError("expected object")
                return value
            except (ValueError, UnicodeDecodeError):
                issues.append("INVALID_JSON_" + name)
                return None

        report = read_json("report.json")
        integrity = read_json("integrity.json")
        classification = read_json("page_classification.json")
        provenance = read_json("run_provenance.json")
        captures = report.get("captures", []) if report else []
        if not isinstance(captures, list) or not captures:
            issues.append("EMPTY_OR_INVALID_CAPTURES")
            captures = []
        expected_keys = []
        for record in captures:
            try:
                key = (record["venue_code"], record["race_number_requested"])
                if (not isinstance(key[0], str) or not isinstance(key[1], int)
                        or isinstance(key[1], bool)):
                    raise ValueError("invalid capture key")
                expected_keys.append(key)
                name = "snapshots/{}/{}/{}.html".format(
                    report["date_jst"], record["venue_code"], record["sha256"])
                if name not in names:
                    issues.append("MISSING_HTML")
                    continue
                raw = archive.read(name)
                if (hashlib.sha256(raw).hexdigest() != record["sha256"]
                        or len(raw) != record["bytes"]):
                    issues.append("HTML_INTEGRITY_MISMATCH")
            except (KeyError, TypeError, ValueError, AttributeError):
                issues.append("INVALID_CAPTURE_RECORD")
        if len(expected_keys) != len(set(expected_keys)):
            issues.append("DUPLICATE_CAPTURE")
        if report and (report.get("errors") or report.get("formal_eligible") is not False
                       or report.get("results_seen") is not False):
            issues.append("UNSAFE_OR_FAILED_CAPTURE")
        if integrity and (integrity.get("status") != "CAPTURE_INTEGRITY_PASS_RESEARCH_ONLY"
                          or integrity.get("verified_count") != len(captures)
                          or integrity.get("formal_eligible") is not False):
            issues.append("INTEGRITY_NOT_CERTIFIED")
        counts = {}
        if classification:
            rows = classification.get("classifications")
            if not isinstance(rows, list):
                rows = []
                issues.append("INVALID_CLASSIFICATIONS")
            keys = [(row.get("venue_code"), row.get("race_number")) for row in rows
                    if isinstance(row, dict)]
            try:
                counts = dict(collections.Counter(row.get("status") for row in rows
                                                  if isinstance(row, dict)))
            except TypeError:
                issues.append("INVALID_CLASSIFICATION_STATUS")
                counts = {}
            if (len(keys) != len(rows)
                    or collections.Counter(keys) != collections.Counter(expected_keys)):
                issues.append("CLASSIFICATION_KEYS_MISMATCH")
            if classification.get("counts") != counts:
                issues.append("CLASSIFICATION_COUNTS_MISMATCH")
            if (classification.get("schema") != "V13_RESEARCH_ONLY"
                    or classification.get("capture_integrity") != "CAPTURE_INTEGRITY_PASS_RESEARCH_ONLY"
                    or any(not isinstance(row, dict) or row.get("formal_eligible") is not False
                           for row in rows)):
                issues.append("INVALID_CLASSIFICATION")
        if provenance:
            if provenance.get("schema") != "V13_RESEARCH_RUN_PROVENANCE":
                issues.append("INVALID_PROVENANCE_SCHEMA")
            if not re.fullmatch(r"[a-f0-9]{40}", str(provenance.get("git_sha", ""))):
                issues.append("INVALID_GIT_SHA")
            if not str(provenance.get("run_id", "")).isdigit():
                issues.append("INVALID_RUN_ID")
            if expected_run_id is not None and str(provenance.get("run_id")) != str(expected_run_id):
                issues.append("RUN_ID_MISMATCH")
            if expected_sha is not None and provenance.get("git_sha") != expected_sha:
                issues.append("GIT_SHA_MISMATCH")
        for label, item in (("classification", classification), ("provenance", provenance)):
            if item and (item.get("formal_eligible") is not False
                         or item.get("results_seen") is not False
                         or item.get("scoring") != "NOT_RUN"
                         or item.get("unlock") != "LOCKED"):
                issues.append("UNSAFE_" + label.upper())
    return {
        "verdict": "PASS_RESEARCH_ONLY" if not issues else "NOT_CERTIFIED",
        "issues": sorted(set(issues)),
        "capture_count": len(captures),
        "classification_counts": counts,
        "run_id": provenance.get("run_id") if provenance else None,
        "git_sha": provenance.get("git_sha") if provenance else None,
        "formal_eligible": False,
        "unlock": "LOCKED",
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("artifact_zip")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--git-sha", required=True)
    args = parser.parse_args()
    result = audit(args.artifact_zip, args.run_id, args.git_sha)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(0 if result["verdict"] == "PASS_RESEARCH_ONLY" else 2)

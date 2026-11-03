"""Independently verify GitHub-persisted T12 originals at an exact immutable commit.

The uploaded report never establishes completeness by itself. Read each GitHub
blob back, verify its Git SHA, and replay all official three-source checks.
"""
import base64
import binascii
import hashlib
import json
import re
import tempfile
from pathlib import Path

from scripts.audit_three_official_t12_originals import audit_three_originals
from scripts.run_external_three_t12 import github_api, SOURCE_NAMES, RACE, ID

COMMIT_SHA = re.compile(r"[0-9a-f]{40}\Z")


def inspect_stored_files(files, race, obs_id, *, auditor=audit_three_originals):
    """Fail closed on partial or inaccurate Git evidence; no forecast permission."""
    if not RACE.fullmatch(race) or not ID.fullmatch(obs_id):
        raise ValueError("invalid saved race or observation")
    prefix = f"external_three_t12/{race[:8]}/{race}/{obs_id}"
    report_key = f"{prefix}/reports/three_originals.json"
    expected = {report_key}
    for part, names in SOURCE_NAMES.items():
        expected.update(f"{prefix}/{part}/{filename}" for filename in names)
    if set(files) - expected:
        raise ValueError("unrecognized stored evidence member")
    if report_key not in files:
        raise ValueError("missing stored observation report")
    report = json.loads(files[report_key])
    if (not isinstance(report, dict) or report.get("race_code") != race
            or report.get("full_t12_source_certified") is not False
            or report.get("forecast_usable") is not False):
        raise ValueError("stored report identity or certificate mismatch")
    result = {
        "race_code": race,
        "observation_id": obs_id,
        "declared_status": report.get("status"),
        "original_files_found": len(files) - 1,
        "research_complete": False,
        "full_t12_source_certified": False,
        "forecast_usable": False,
    }
    if report.get("status") not in (
            "research_components_complete_by_t12", "research_components_incomplete"):
        if len(files) != 1:
            raise ValueError("incomplete observation contains unsupported originals")
        result["status"] = "observation_not_ready"
        return result
    if set(files) != expected:
        raise ValueError("missing one or more saved original sources or manifests")
    # Independently check all three original/manifest pairs *before*
    # invoking the semantic three-source auditor. This prevents a future
    # auditor mock, shortcut or refactor from silently skipping byte integrity.
    for part, names in SOURCE_NAMES.items():
        original = files[f"{prefix}/{part}/{names[0]}"]
        manifest_raw = files[f"{prefix}/{part}/{names[1]}"]
        if not isinstance(original, bytes) or not isinstance(manifest_raw, bytes):
            raise ValueError("non-byte original or manifest")
        manifest = json.loads(manifest_raw)
        if (not isinstance(manifest, dict)
                or manifest.get("race_code") != race
                or manifest.get("sha256") != hashlib.sha256(original).hexdigest()
                or type(manifest.get("bytes")) is not int
                or manifest["bytes"] != len(original)):
            raise ValueError("stored original manifest SHA256, size or identity mismatch")
    with tempfile.TemporaryDirectory() as tmp:
        dirs = {}
        for part, names in SOURCE_NAMES.items():
            folder = Path(tmp) / part
            folder.mkdir()
            dirs[part] = folder
            for filename in names:
                raw = files[f"{prefix}/{part}/{filename}"]
                if not isinstance(raw, bytes) or len(raw) > 2_000_000:
                    raise ValueError("invalid stored original bytes")
                (folder / filename).write_bytes(raw)
        independently = auditor(dirs["card"], dirs["before"], dirs["odds"])
    declared = report.get("audit")
    if (not isinstance(declared, dict) or independently.get("race_code") != race
            or declared.get("component_checks") != independently.get("component_checks")
            or declared.get("missing_components") != independently.get("missing_components")
            or any(declared.get(k) != independently.get(k) for k in (
                "cutoff_jst", "racelist_received_jst", "beforeinfo_received_jst",
                "odds_received_jst", "latest_original_received_jst",
                "t12_receipt_margin_seconds"))):
        raise ValueError("stored originals disagree with declared audit")
    complete = independently.get("all_research_components_observed_by_t12")
    status = "research_components_complete_by_t12" if complete else "research_components_incomplete"
    if (type(complete) is not bool or report.get("status") != status
            or declared.get("all_research_components_observed_by_t12") is not complete):
        raise ValueError("declared research completion does not match originals")
    result.update({
        "status": "independent_originals_reaudited",
        "research_complete": complete,
        "missing_components": independently["missing_components"],
        "cutoff_jst": independently["cutoff_jst"],
        "latest_original_received_jst": independently["latest_original_received_jst"],
        "t12_receipt_margin_seconds": independently["t12_receipt_margin_seconds"],
    })
    return result


def read_exact_commit_blob(repo, token, commit_sha, path, *, api=github_api):
    from urllib.parse import quote
    endpoint = "contents/" + quote(path, safe="/") + "?ref=" + commit_sha
    value = api(repo, token, "GET", endpoint)
    if (not isinstance(value, dict) or value.get("type") != "file"
            or value.get("encoding") != "base64"
            or not isinstance(value.get("content"), str)):
        raise ValueError("GitHub did not return a file blob")
    try:
        raw = base64.b64decode("".join(value["content"].split()), validate=True)
    except (ValueError, binascii.Error) as exc:
        raise ValueError("invalid GitHub blob encoding") from exc
    git_sha = hashlib.sha1(f"blob {len(raw)}\0".encode() + raw).hexdigest()
    if value.get("sha") != git_sha:
        raise ValueError("stored GitHub blob SHA mismatch")
    return raw


def reaudit_published(repo, token, commit_sha, race, obs_id, *, reader=read_exact_commit_blob,
                      auditor=audit_three_originals):
    if not isinstance(commit_sha, str) or not COMMIT_SHA.fullmatch(commit_sha):
        raise ValueError("invalid immutable Git commit SHA")
    if not RACE.fullmatch(race) or not ID.fullmatch(obs_id):
        raise ValueError("invalid stored research identity")
    prefix = f"external_three_t12/{race[:8]}/{race}/{obs_id}"
    report_key = f"{prefix}/reports/three_originals.json"
    report_raw = reader(repo, token, commit_sha, report_key)
    report = json.loads(report_raw)
    files = {report_key: report_raw}
    if report.get("status") in (
            "research_components_complete_by_t12", "research_components_incomplete"):
        for part, names in SOURCE_NAMES.items():
            for name in names:
                key = f"{prefix}/{part}/{name}"
                files[key] = reader(repo, token, commit_sha, key)
    result = inspect_stored_files(files, race, obs_id, auditor=auditor)
    result["evidence_commit"] = commit_sha
    return result

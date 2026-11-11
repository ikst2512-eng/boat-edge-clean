"""Prospective, write-once research evidence: official raw originals + shadow.

This cannot certify a formal T-12 forecast, a GitHub-independent first-seen,
final entry, a calibrated model or a purchase. Historical data is NEVER filled.
"""
import argparse
import base64
import hashlib
import json
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen

JST = timezone(timedelta(hours=9))
REPO = "ikst2512-eng/boat-edge-clean"
BRANCH = "entry-course-evidence-ledger"
SOURCE_FILES = {"racelist": "racelist.html", "beforeinfo": "beforeinfo.json", "odds": "original.html"}
RACE = re.compile(r"20\d{6}(?:0[1-9]|1\d|2[0-4])(?:0[1-9]|1[0-2])\Z")
PATH_ROOT = "official_source_forecast_bundles"


def timestamp(value):
    if type(value) is not str:
        raise ValueError("timestamp_missing")
    try:
        value = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("timestamp_malformed") from exc
    if value.utcoffset() != timedelta(hours=9):
        raise ValueError("timestamp_not_jst")
    return value


def serialized(obj):
    return (json.dumps(obj, ensure_ascii=False, sort_keys=True,
                       separators=(",", ":")) + "\n").encode("utf-8")


def blob_sha(body):
    return hashlib.sha1(b"blob " + str(len(body)).encode() + b"\0" + body).hexdigest()


def build_bundle(row, source_dirs):
    """Build a bounded immutable bundle from an independently reaudited row.

    source_dirs is a dict of existing, local, verified official receipt folders.
    No external HTTP is performed here and no source timestamp is synthesized.
    """
    race = row.get("race_code")
    manifest = row.get("official_input_manifest")
    shadow = row.get("official_research_shadow")
    if (type(race) is not str or not RACE.fullmatch(race)
            or row.get("official_original_status") != "three_originals_reaudited_research_only"
            or row.get("formal_t12_certified") is not False
            or not isinstance(manifest, dict) or not isinstance(shadow, dict)):
        raise ValueError("not_independently_reaudited_three_originals")
    cutoff = timestamp(manifest.get("cutoff_jst"))
    generated = timestamp(shadow.get("generated_at_jst"))
    if (manifest.get("race_code") != race or shadow.get("race_code") != race
            or manifest.get("schema") != "OFFICIAL_REAUDITED_INPUT_MANIFEST_V1"
            or shadow.get("schema") != "OFFICIAL_SIX_LANE_RESEARCH_SHADOW_V1"
            or shadow.get("status") != "research_shadow_generated_pre_t12"
            or manifest.get("official_source_fields_reconstructed") is not True
            or shadow.get("generated") is not True
            or shadow.get("model_consumed_official_exhibition_fields") is not True
            or shadow.get("official_input_sha256") != manifest.get("input_sha256")
            or shadow.get("t12_cutoff_jst") != manifest.get("cutoff_jst")
            or len(manifest.get("six_boat_inputs", [])) != 6
            or set(manifest.get("official_sources", {})) != set(SOURCE_FILES)
            or set(source_dirs) != set(SOURCE_FILES)
            or not (manifest.get("formal_t12_certified") is False
                    and manifest.get("final_race_entry_verified") is False
                    and manifest.get("independent_remote_first_seen_verified") is False
                    and shadow.get("formal_t12_certified") is False
                    and shadow.get("independent_remote_first_seen_verified") is False
                    and shadow.get("purchase_approved") is False
                    and shadow.get("research_only") is True)):
        raise ValueError("not_a_research_only_official_shadow")
    # Recompute the exact original-input digest in the privileged job rather
    # than trusting the transfer artifact's self-declared SHA alone.
    base_fields = {key: manifest[key] for key in
                   ("race_code", "cutoff_jst", "official_sources", "six_boat_inputs")}
    digest = hashlib.sha256(json.dumps(
        base_fields, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")).hexdigest()
    if digest != manifest["input_sha256"]:
        raise ValueError("official_input_manifest_sha_mismatch")
    boats = manifest["six_boat_inputs"]
    if ({b.get("lane") for b in boats if isinstance(b, dict)} != set(range(1, 7))
            or {b.get("exhibition_course") for b in boats if isinstance(b, dict)} != set(range(1, 7))
            or len({str(b.get("registration")) for b in boats if isinstance(b, dict)}) != 6):
        raise ValueError("six_lanes_or_registration_mismatch")
    originals = {}
    received = []
    for kind, filename in SOURCE_FILES.items():
        folder = Path(source_dirs[kind])
        path = folder / filename
        if (folder.is_symlink() or path.is_symlink() or not path.is_file()):
            raise ValueError("original_file_missing_or_symlink")
        raw = path.read_bytes()
        meta = manifest["official_sources"][kind]
        when = timestamp(meta.get("received_at_jst"))
        if (not raw or len(raw) > 150_000
                or len(raw) != meta.get("bytes")
                or hashlib.sha256(raw).hexdigest() != meta.get("sha256")
                or when > generated or when >= cutoff):
            raise ValueError("original_bytes_hash_or_receipt_not_verified")
        received.append(when)
        originals[kind] = {"filename": filename,
                           "bytes": len(raw), "sha256": meta["sha256"],
                           "received_at_jst": when.isoformat(),
                           "base64": base64.b64encode(raw).decode("ascii")}
    if (max(received) != timestamp(shadow["latest_official_source_received_jst"])
            or not max(received) <= generated < cutoff):
        raise ValueError("source_generation_cutoff_chronology_invalid")
    content = {"schema": "OFFICIAL_RESEARCH_SOURCE_AND_SHADOW_BUNDLE_V1",
               "race_code": race,
               "research_only": True, "formal": False,
               "purchase_approved": False,
               "model_accuracy_verified": False,
               "final_race_entry_verified": False,
               "independent_remote_first_seen_verified": False,
               "cutoff_jst": cutoff.isoformat(),
               "official_input_manifest": manifest,
               "official_research_shadow": shadow,
               "official_raw_originals": originals}
    return f"{PATH_ROOT}/{race[:8]}/{race}.json", serialized(content), cutoff


def verify_independent_source_and_shadow_replay(row, source_dirs, *,
                                                 auditor=None,
                                                 manifest_builder=None,
                                                 shadow_builder=None):
    """Privileged job independently reconstructs evidence from transferred bytes.

    The capture report is only a claim until the source's original manifests,
    race/deadline, six racer identities, 120 odds and generated 4-mode ticket
    rankings are reverified against the actual received bytes.
    """
    from scripts.audit_three_official_t12_originals import audit_three_originals
    from scripts.audit_official_forecast_consumption import (
        verified_official_input_manifest, generate_official_research_shadow
    )
    if set(source_dirs) != set(SOURCE_FILES):
        raise ValueError("privileged_source_directory_set_mismatch")
    folders = [source_dirs[k] for k in SOURCE_FILES]
    official = (auditor or audit_three_originals)(*folders)
    if (not isinstance(official, dict)
            or official.get("race_code") != row.get("race_code")
            or official.get("all_research_components_observed_by_t12") is not True
            or official.get("three_originals_hash_verified") is not True
            or official.get("missing_components") != []
            or official.get("final_race_entry_verified") is not False):
        raise ValueError("privileged_official_three_source_reaudit_failed")
    independent_manifest = (manifest_builder or verified_official_input_manifest)(
        folders, official
    )
    if independent_manifest != row.get("official_input_manifest"):
        raise ValueError("privileged_original_manifest_replay_mismatch")
    shadow = row.get("official_research_shadow")
    if not isinstance(shadow, dict) or type(shadow.get("generated_at_jst")) is not str:
        raise ValueError("privileged_shadow_missing_generation")
    independently_calculated_shadow = (shadow_builder or generate_official_research_shadow)(
        independent_manifest, shadow["generated_at_jst"]
    )
    if independently_calculated_shadow != shadow or shadow.get("generated") is not True:
        raise ValueError("privileged_shadow_predictions_replay_mismatch")
    return True


def api_request(method, path, token, data=None):
    """GitHub Contents API only; returns (status, json)."""
    if type(token) is not str or not token:
        raise ValueError("github_token_missing")
    url = f"https://api.github.com/repos/{REPO}/contents/{quote(path, safe='/')}"
    if method == "GET":
        url += "?ref=" + quote(BRANCH)
    headers = {"Accept": "application/vnd.github+json",
               "Authorization": "Bearer " + token,
               "X-GitHub-Api-Version": "2022-11-28",
               "User-Agent": "boat-edge-research-append-only"}
    body = serialized(data) if data is not None else None
    try:
        with urlopen(Request(url, data=body, headers=headers, method=method), timeout=15) as response:
            return response.status, json.loads(response.read(800_000))
    except HTTPError as exc:
        if exc.code in (404, 409, 422):
            return exc.code, {}
        raise


def readback(path, token, *, getter=api_request):
    code, data = getter("GET", path, token)
    if code == 404:
        return None
    if code != 200 or not isinstance(data, dict) or data.get("encoding") != "base64":
        raise RuntimeError("remote_readback_unverified")
    try:
        body = base64.b64decode(data["content"], validate=False)
    except (ValueError, KeyError) as exc:
        raise RuntimeError("remote_readback_invalid_base64") from exc
    if blob_sha(body) != data.get("sha"):
        raise RuntimeError("remote_readback_blob_sha_mismatch")
    return body


def store_once(path, body, cutoff, token, *, getter=api_request, putter=api_request, clock=lambda: datetime.now(JST)):
    """Never update existing Git path. No retry/overwriting on 409/422."""
    if not path.startswith(PATH_ROOT + "/"):
        raise ValueError("wrong_research_evidence_namespace")
    if clock() + timedelta(seconds=35) >= cutoff:
        return {"status": "cutoff_near_or_passed_no_write", "path": path, "stored": False}
    existing = readback(path, token, getter=getter)
    if existing is not None:
        if existing != body:
            raise RuntimeError("immutable_path_content_conflict")
        return {"status": "preexisting_identical_reused", "path": path,
                "stored": True, "newly_stored": False, "sha256": hashlib.sha256(body).hexdigest()}
    if clock() + timedelta(seconds=20) >= cutoff:
        return {"status": "cutoff_near_or_passed_no_write", "path": path, "stored": False}
    code, result = putter("PUT", path, token, {
        "branch": BRANCH,
        "message": "research: append prospective official raw and shadow " + path.rsplit("/", 1)[-1],
        "content": base64.b64encode(body).decode("ascii"),
    })
    observed = clock()
    if code != 201 or observed >= cutoff:
        # A response after cutoff cannot establish a valid cutoff-before-first-add.
        raise RuntimeError("git_create_unverified_or_too_late_http_" + str(code))
    if (not isinstance(result, dict)
            or result.get("content", {}).get("sha") != blob_sha(body)
            or not re.fullmatch(r"[a-f0-9]{40}", str(result.get("commit", {}).get("sha", "")))):
        raise RuntimeError("github_put_response_mismatch")
    remote_bytes = readback(path, token, getter=getter)
    readback_received = clock()
    if remote_bytes != body:
        raise RuntimeError("github_initial_readback_content_mismatch")
    return {"status": "new_research_bundle_first_add_put_and_get_matched",
            "path": path, "stored": True, "newly_stored": True,
            "git_commit_sha": result["commit"]["sha"],
            "git_blob_sha1": blob_sha(body),
            "put_response_observed_at_jst": observed.isoformat(),
            "readback_response_observed_at_jst": readback_received.isoformat(),
            "sha256": hashlib.sha256(body).hexdigest(),
            "formal_t12_certified": False,
            "independent_remote_first_seen_verified": False}



def receipt_snapshot(outcomes, *, status, event, run_id, run_attempt,
                     observed_at_jst, error_type=None, error_code=None):
    """An Action-local receipt, not independent GitHub remote first-seen proof.

    Report only identifiers, hashes, observed times and safe classification.
    Never serialize auth tokens or the raw source bytes into the receipt.
    """
    if status not in ("checked", "failed"):
        raise ValueError("invalid_git_store_audit_status")
    if not isinstance(outcomes, list):
        raise ValueError("invalid_git_store_audit_outcomes")
    timestamp(observed_at_jst)
    stored = sum(x.get("newly_stored") is True for x in outcomes)
    return {
        "schema": "OFFICIAL_RESEARCH_GIT_WRITE_RECEIPT_V1",
        "status": status,
        "repository": REPO, "ledger_branch": BRANCH,
        "action_event": event, "action_run_id": run_id,
        "action_run_attempt": run_attempt,
        "observed_at_jst": observed_at_jst,
        "newly_stored": stored,
        "outcomes": outcomes,
        "error_type": error_type, "error_code": error_code,
        "research_only": True, "formal_t12_certified": False,
        "production_forecast": False,
        "independent_remote_first_seen_verified": False,
        "purchase_approved": False,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch-dir", type=Path, default=Path("official_joint_evidence"))
    parser.add_argument("--receipt-output", type=Path,
                        default=Path("official-source-git-receipt/receipt.json"))
    args = parser.parse_args()
    outcomes = []
    status = "failed"
    error_type = error_code = None
    try:
        from scripts.audit_official_forecast_consumption import read_json, locate_sources
        if (os.environ.get("GITHUB_REPOSITORY") != REPO
                or os.environ.get("GITHUB_REF") != "refs/heads/main"
                or os.environ.get("GITHUB_EVENT_NAME") not in ("schedule", "workflow_dispatch")):
            raise ValueError("guarded_non_main_or_non_scheduled_event")
        token = os.environ.get("GH_TOKEN")
        if not token:
            raise ValueError("github_writer_token_unavailable")
        report = read_json(args.batch_dir / "forecast_temporal_link_report.json")
        if (report.get("status") != "read_only_research_audited"
                or report.get("formal_t12_certified") != 0
                or report.get("official_consumed_forecasts") != 0):
            raise ValueError("source_audit_unverified")
        for row in report.get("rows", []):
            if row.get("official_original_status") != "three_originals_reaudited_research_only":
                continue
            shadow = row.get("official_research_shadow")
            if not isinstance(shadow, dict) or shadow.get("generated") is not True:
                outcomes.append({"race_code": row.get("race_code"), "status": "shadow_not_generated"})
                continue
            folders = locate_sources(args.batch_dir, row["race_code"])
            source_dirs = dict(zip(SOURCE_FILES, folders))
            path, body, cutoff = build_bundle(row, source_dirs)
            # Reparse all three original sources and rederive the exact research
            # forecast before ANY Git PUT; never trust the handoff summary.
            verify_independent_source_and_shadow_replay(row, source_dirs)
            try:
                stored = store_once(path, body, cutoff, token)
            except Exception as exc:
                # A failed request can be ambiguous (e.g. 409 or a lost 201).
                # Preserve the exact race/path/expected SHA without inventing
                # a first-add success, and leave the remote original untouched.
                outcomes.append({
                    "race_code": row["race_code"],
                    "path": path,
                    "expected_sha256": hashlib.sha256(body).hexdigest(),
                    "cutoff_jst": cutoff.isoformat(),
                    "status": "unverified_writer_failure",
                    "error_type": type(exc).__name__,
                    "stored": False, "newly_stored": False,
                })
                raise
            outcomes.append({"race_code": row["race_code"],
                             "cutoff_jst": cutoff.isoformat(), **stored})
        status = "checked"
    except Exception as exc:
        error_type = type(exc).__name__
        # Safe finite error codes ONLY; never leak HTTP headers/auth payloads.
        if isinstance(exc, (ValueError, RuntimeError)):
            text = str(exc)
            if re.fullmatch(r"[a-zA-Z0-9_:-]{1,120}", text):
                error_code = text
        raise
    finally:
        receipt = receipt_snapshot(
            outcomes, status=status,
            event=os.environ.get("GITHUB_EVENT_NAME", "unavailable"),
            run_id=os.environ.get("GITHUB_RUN_ID", "unavailable"),
            run_attempt=os.environ.get("GITHUB_RUN_ATTEMPT", "unavailable"),
            observed_at_jst=datetime.now(JST).isoformat(),
            error_type=error_type, error_code=error_code,
        )
        args.receipt_output.parent.mkdir(parents=True, exist_ok=True)
        # Local Action Artifact only; this does NOT add/modify a Git original.
        args.receipt_output.write_bytes(serialized(receipt))
        print("OFFICIAL_RESEARCH_GIT_STORE " +
              json.dumps(receipt, ensure_ascii=False, sort_keys=True))



if __name__ == "__main__":
    main()

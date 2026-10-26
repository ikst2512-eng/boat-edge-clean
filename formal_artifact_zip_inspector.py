"""Inspect downloaded GitHub Actions artifact ZIP bytes without trusting its metadata.

Offline structural integrity only. Never grants model authenticity, cutoff proof,
or Formal Fresh approval. The ZIP must be downloaded independently from GitHub.
"""
import hashlib
import io
import json
import re
import zipfile
from formal_candidate_validator import InvalidCandidate, _timestamp
from formal_v5_transport_adapter import inspect_v5_transport


def inspect_downloaded_artifact(zip_bytes, expected_race_code, expected_candidate_sha256):
    if not isinstance(zip_bytes, bytes) or not 0 < len(zip_bytes) <= 2_000_000:
        raise InvalidCandidate("artifact zip missing or oversized")
    if not isinstance(expected_race_code, str) or not expected_race_code.isascii() or not expected_race_code.isdigit() or len(expected_race_code) != 12:
        raise InvalidCandidate("race code invalid")
    if not isinstance(expected_candidate_sha256, str) or not re.fullmatch(r"[0-9a-f]{64}", expected_candidate_sha256):
        raise InvalidCandidate("digest invalid")
    try:
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
            infos = z.infolist()
            names = [i.filename for i in infos]
            required = {f"prospective_candidates/{expected_race_code}.json", "prospective_receipt.json"}
            if set(names) != required or len(infos) != 2:
                raise InvalidCandidate("unexpected artifact members")
            if any(i.is_dir() or i.file_size > 100000 or i.flag_bits & 1 or
                   i.compress_type not in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED) or
                   ((i.external_attr >> 16) & 0o170000) == 0o120000 or
                   (i.file_size and (i.compress_size == 0 or i.file_size > 100 * i.compress_size))
                   for i in infos):
                raise InvalidCandidate("unsafe artifact members")
            candidate_bytes = z.read(f"prospective_candidates/{expected_race_code}.json")
            receipt_bytes = z.read("prospective_receipt.json")
    except (zipfile.BadZipFile, OSError, RuntimeError, ValueError, KeyError) as exc:
        raise InvalidCandidate("invalid artifact zip") from exc
    digest = hashlib.sha256(candidate_bytes).hexdigest()
    if digest != expected_candidate_sha256:
        raise InvalidCandidate("downloaded candidate digest mismatch")
    inspected = inspect_v5_transport(candidate_bytes)
    candidate = json.loads(candidate_bytes)
    def unique_pairs(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise InvalidCandidate("duplicate receipt JSON key")
            result[key] = value
        return result
    try:
        receipt = json.loads(receipt_bytes.decode("utf-8"), object_pairs_hook=unique_pairs,
                             parse_constant=lambda _: (_ for _ in ()).throw(InvalidCandidate("nonfinite receipt JSON")))
    except (ValueError, UnicodeError) as exc:
        raise InvalidCandidate("receipt JSON invalid") from exc
    if (not isinstance(receipt, dict) or receipt.get("candidate_sha256") != digest or
        receipt.get("race_code") != expected_race_code or
        receipt.get("schema") != "fresh-prospective-receipt-v1" or
        receipt.get("status") != "candidate_only_not_formal_or_public" or
        receipt.get("deadline_at") != candidate.get("deadline_at") or
        receipt.get("source_snapshot_sha256") != candidate.get("source_snapshot_sha256") or
        receipt.get("independent_github_arrival_verified") is not False or
        type(receipt.get("workflow_run_id")) is not int or receipt["workflow_run_id"] <= 0 or
        type(receipt.get("workflow_attempt")) is not int or receipt["workflow_attempt"] <= 0):
        raise InvalidCandidate("receipt does not bind downloaded candidate")
    source_digest = candidate.get("source_snapshot_sha256")
    if not isinstance(source_digest, str) or not re.fullmatch(r"[0-9a-f]{64}", source_digest):
        raise InvalidCandidate("source snapshot digest invalid")
    generated = _timestamp(candidate.get("generated_at"))
    deadline = _timestamp(candidate.get("deadline_at"))
    recorded = _timestamp(receipt.get("runner_recorded_at"))
    if not generated <= recorded or (deadline - recorded).total_seconds() < 12 * 60:
        raise InvalidCandidate("runner receipt not safely before cutoff")
    if inspected["race_key"].replace("-", "") != expected_race_code:
        raise InvalidCandidate("candidate race mismatch")
    return {"downloaded_bytes_consistent": True, "candidate_sha256": digest,
            "race_code": expected_race_code,
            "workflow_run_id": receipt["workflow_run_id"],
            "workflow_attempt": receipt["workflow_attempt"],
            "generated_at": candidate["generated_at"],
            "deadline_at": candidate["deadline_at"],
            "independent_upload_time_verified": False, "formal_approved": False}

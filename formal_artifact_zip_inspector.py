"""Inspect downloaded GitHub Actions artifact ZIP bytes without trusting its metadata.

Offline structural integrity only. Never grants model authenticity, cutoff proof,
or Formal Fresh approval. The ZIP must be downloaded independently from GitHub.
"""
import hashlib
import io
import json
import re
import zipfile
from formal_candidate_validator import InvalidCandidate
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
    try:
        receipt = json.loads(receipt_bytes)
    except (ValueError, UnicodeError) as exc:
        raise InvalidCandidate("receipt JSON invalid") from exc
    if not isinstance(receipt, dict) or receipt.get("candidate_sha256") != digest or receipt.get("race_code") != expected_race_code:
        raise InvalidCandidate("receipt does not bind downloaded candidate")
    if inspected["race_key"].replace("-", "") != expected_race_code:
        raise InvalidCandidate("candidate race mismatch")
    return {"downloaded_bytes_consistent": True, "candidate_sha256": digest,
            "independent_upload_time_verified": False, "formal_approved": False}

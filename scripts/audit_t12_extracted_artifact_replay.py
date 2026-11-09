"""Fail-closed original-source replay of GitHub Actions v4 extracted artifacts.

GitHub's authenticated artifact metadata digest is compared against a pinned
historical digest; this digest is NOT recomputed from a re-packed ZIP. The
official download-artifact action extracts the artifact. The original source
bytes are then independently re-audited from manifests by scheduled_pair_zip.
"""
import hashlib
import io
import json
import re
import zipfile
from pathlib import Path
from urllib.request import Request, urlopen

from scripts.audit_t12_scheduled_pair_zip import replay as raw_source_replay

REPO = re.compile(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+\Z")
HEX = re.compile(r"[a-f0-9]{64}\Z")


def artifact_metadata(repo, token, artifact_id):
    if (not isinstance(repo, str) or not REPO.fullmatch(repo)
            or not isinstance(token, str) or not token
            or type(artifact_id) is not int or artifact_id <= 0):
        raise ValueError("invalid GitHub metadata credentials")
    endpoint = (
        f"https://api.github.com/repos/{repo}/actions/artifacts/{artifact_id}"
    )
    req = Request(endpoint, headers={
        "Authorization": "Bearer " + token,
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "boat-edge-t12-extracted-archive-audit",
    })
    with urlopen(req, timeout=20) as response:
        if response.status != 200:
            raise ValueError("GitHub Actions metadata HTTP is not 200")
        return json.load(response)


def replay_original_zip_file(path, *, run_id, artifact_id, digest, metadata,
                             auditor=raw_source_replay):
    """Rehash the *original* remote Actions ZIP when its actual bytes are provided.

    Unlike replay_extracted, this checks the exact archive bytes and CRC, not a
    reconstructed ZIP. This is an optional independent read-only sidecar;
    successful ZIP provenance does not attest the model or first forecast push.
    """
    if (type(run_id) is not int or run_id <= 0
            or type(artifact_id) is not int or artifact_id <= 0
            or not isinstance(digest, str) or HEX.fullmatch(digest) is None
            or not isinstance(metadata, dict)
            or metadata.get("id") != artifact_id
            or metadata.get("name") != f"independent-late-preview-{run_id}"
            or metadata.get("expired") is not False
            or metadata.get("digest") != "sha256:" + digest
            or (metadata.get("workflow_run") or {}).get("id") != run_id
            or type(metadata.get("size_in_bytes")) is not int
            or not 0 < metadata["size_in_bytes"] <= 20_000_000):
        raise ValueError("invalid original GitHub artifact identity or metadata")
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise ValueError("actual original ZIP file is missing or unsafe")
    size = path.stat().st_size
    if size != metadata["size_in_bytes"] or not 0 < size <= 20_000_000:
        raise ValueError("actual original ZIP byte size mismatches GitHub")
    raw = path.read_bytes()
    actual = hashlib.sha256(raw).hexdigest()
    if actual != digest:
        raise ValueError("actual original ZIP hash mismatches GitHub metadata")
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            entries = archive.infolist()
            if not entries or len(entries) > 2000:
                raise ValueError("invalid original ZIP member count")
            names = set()
            total = 0
            for member in entries:
                name = member.filename
                parts = name.replace("\\", "/").split("/")
                unix_kind = (member.external_attr >> 16) & 0o170000
                if (not name or name.startswith("/") or "\\" in name
                        or any(x in (".", "..", "") for x in parts if x)
                        or ".." in parts or unix_kind == 0o120000
                        or name in names
                        or member.file_size > 2_000_000):
                    raise ValueError("unsafe original ZIP member")
                names.add(name)
                total += member.file_size
                if total > 20_000_000:
                    raise ValueError("oversized original ZIP extracted bytes")
            if archive.testzip() is not None:
                raise ValueError("original ZIP CRC mismatch")
    except (zipfile.BadZipFile, OSError, RuntimeError) as exc:
        raise ValueError("original GitHub ZIP unreadable") from exc
    source = auditor(raw, run_id, digest)
    if (not isinstance(source, dict) or source.get("run_id") != run_id
            or source.get("artifact_sha256") != digest
            or source.get("full_t12_source_certified") is not False
            or source.get("formal") is not False):
        raise ValueError("original ZIP source audit not fail-closed")
    return {
        "schema": "T12_ORIGINAL_ACTIONS_ZIP_DIRECT_REHASH_V1",
        "run_id": run_id,
        "artifact_id": artifact_id,
        "original_zip_sha256_verified": True,
        "original_zip_sha256": actual,
        "original_zip_byte_size": size,
        "original_zip_members_crc_verified": len(entries),
        "official_source_originals_replayed": True,
        "original_source_replay": source,
        "independent_source_server_publication_timing_verified_by_this_check": False,
        "first_forecast_git_remote_receipt_verified": False,
        "model_original_input_consumption_verified": False,
        "full_t12_source_certified": False,
        "accuracy_scoring_allowed": False,
        "formal_accuracy_denominator": None,
        "new_formal_certifications": 0,
        "formal": False,
        "t12_eligible": False,
    }


def replay_extracted(root, *, run_id, artifact_id, digest, metadata,
                     auditor=raw_source_replay):
    if (type(run_id) is not int or run_id <= 0
            or type(artifact_id) is not int or artifact_id <= 0
            or not isinstance(digest, str) or not HEX.fullmatch(digest)):
        raise ValueError("invalid expected artifact identity")
    if (not isinstance(metadata, dict)
            or metadata.get("id") != artifact_id
            or metadata.get("name") != f"independent-late-preview-{run_id}"
            or metadata.get("expired") is not False
            or metadata.get("digest") != f"sha256:{digest}"
            or (metadata.get("workflow_run") or {}).get("id") != run_id
            or type(metadata.get("size_in_bytes")) is not int
            or not 0 < metadata["size_in_bytes"] <= 20_000_000):
        raise ValueError("Actions artifact metadata mismatch or unavailable")
    root = Path(root)
    if root.is_symlink() or not root.is_dir():
        raise ValueError("downloaded artifact directory is missing or symlink")
    files = []
    total = 0
    for entry in root.rglob("*"):
        if entry.is_symlink():
            raise ValueError("unsafe extracted artifact symlink")
        if entry.is_dir():
            continue
        if not entry.is_file():
            raise ValueError("unsafe extracted artifact member")
        relative = entry.relative_to(root).as_posix()
        if relative.startswith("/") or ".." in Path(relative).parts:
            raise ValueError("unsafe extracted archive path")
        if entry.stat().st_size > 2_000_000:
            raise ValueError("oversized original archive member")
        total += entry.stat().st_size
        files.append((relative, entry))
    if (not files or len(files) > 2000 or total > 20_000_000
            or len(set(name for name, _ in files)) != len(files)):
        raise ValueError("invalid extracted artifact content count")
    # A repacked ZIP has a DIFFERENT SHA from the original GitHub ZIP.
    # Never label its hash as the GitHub ZIP digest or as a first receipt.
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as output:
        for name, entry in sorted(files):
            output.writestr(name, entry.read_bytes())
    repacked = buffer.getvalue()
    repackage_sha = hashlib.sha256(repacked).hexdigest()
    result = auditor(repacked, run_id, repackage_sha)
    if (not isinstance(result, dict) or result.get("run_id") != run_id
            or result.get("artifact_sha256") != repackage_sha
            or result.get("full_t12_source_certified") is not False
            or result.get("formal") is not False):
        raise ValueError("independent extracted-source replay not fail-closed")
    result["original_actions_artifact_sha256"] = digest
    result["github_original_zip_digest_verified_by_local_hash"] = False
    result["github_artifact_digest_metadata_matches"] = True
    result["extracted_original_source_bytes_replayed"] = True
    result["repacked_zip_sha256_for_internal_replay"] = repackage_sha
    # Preserve the existing bounded historical reconciliation API, but make
    # the limited nature of this field explicit in adjacent report metadata.
    result["artifact_sha256"] = digest
    result["archive_readback_scope"] = (
        "download-artifact_v4_extracted_files; individually verified "
        "boatrace.jp source manifests; GitHub ZIP digest from authenticated "
        "API metadata, NOT rehashed original ZIP bytes"
    )
    return result

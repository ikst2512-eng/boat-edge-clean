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

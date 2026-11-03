"""Write-once raw HTTP acquisition evidence for optional four-mode capture artifacts.

Receipts preserve source bytes and a local receive timestamp; never prove remote
first-seen or certify upstream provenance independently.
"""
import hashlib
import json
import os
from datetime import timedelta
from pathlib import Path
from urllib.parse import urlsplit

ALLOWED_HOSTS = {"boatracecsv.github.io", "race.boatcast.jp", "boatraceopenapi.github.io"}
MAX_BYTES = 4_000_000


def preserve(url, raw, received_at):
    destination = os.getenv("FOUR_MODE_RAW_RECEIPT_DIR")
    if not destination:
        return None
    parsed = urlsplit(url)
    if (parsed.scheme != "https" or parsed.hostname not in ALLOWED_HOSTS
            or parsed.username is not None or parsed.password is not None
            or parsed.port not in (None, 443) or parsed.fragment):
        raise ValueError("raw_receipt_untrusted_source")
    if (type(raw) is not bytes or len(raw) > MAX_BYTES
            or received_at.utcoffset() != timedelta(hours=9)):
        raise ValueError("raw_receipt_invalid_bytes_or_clock")
    directory = Path(destination)
    directory.mkdir(parents=True, exist_ok=True)
    if directory.is_symlink():
        raise ValueError("raw_receipt_symlink_directory")
    digest = hashlib.sha256(raw).hexdigest()
    identifier = hashlib.sha256(url.encode("utf-8") + b"\0" + raw).hexdigest()
    raw_path = directory / (identifier + ".bin")
    manifest_path = directory / (identifier + ".json")
    manifest = {"schema": "FOUR_MODE_LOCAL_RAW_HTTP_RECEIPT_V1",
                "url": url, "received_at_jst": received_at.isoformat(),
                "sha256": digest, "byte_count": len(raw),
                "independent_remote_receipt_verified": False}
    if raw_path.exists():
        if raw_path.is_symlink() or raw_path.read_bytes() != raw:
            raise ValueError("raw_receipt_collision_or_change")
    else:
        with raw_path.open("xb") as output:
            output.write(raw)
    if manifest_path.exists():
        existing = json.loads(manifest_path.read_text(encoding="utf-8"))
        if (existing.get("url") != url or existing.get("sha256") != digest
                or existing.get("byte_count") != len(raw)):
            raise ValueError("raw_receipt_manifest_collision")
    else:
        with manifest_path.open("x", encoding="utf-8") as output:
            json.dump(manifest, output, ensure_ascii=False, sort_keys=True)
            output.write("\n")
    return manifest

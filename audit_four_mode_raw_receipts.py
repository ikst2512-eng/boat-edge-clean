"""Verify exact-byte integrity of local raw HTTP receipt artifacts.

This is artifact integrity, not independent proof of upstream or predeadline access.
"""
import hashlib
import json
import re
from datetime import datetime, timedelta
from pathlib import Path

from four_mode_raw_receipt import ALLOWED_HOSTS
from urllib.parse import urlsplit


def audit(directory):
    directory = Path(directory)
    if directory.is_symlink() or not directory.is_dir():
        return {"status": "unavailable", "verified": 0, "formal": False}
    manifests = sorted(directory.glob("*.json"))
    binaries = list(directory.glob("*.bin"))
    if not manifests:
        return {"status": "no_receipts", "verified": 0, "formal": False}
    valid = 0
    ids = set()
    for manifest_path in manifests:
        identifier = manifest_path.stem
        raw_path = directory / (identifier + ".bin")
        if (not re.fullmatch(r"[a-f0-9]{64}", identifier)
                or manifest_path.is_symlink() or raw_path.is_symlink()
                or not raw_path.is_file() or manifest_path.stat().st_size > 4096
                or raw_path.stat().st_size > 4_000_000):
            return {"status": "invalid_receipt", "verified": 0, "formal": False}
        try:
            m = json.loads(manifest_path.read_text(encoding="utf-8"))
            raw = raw_path.read_bytes()
            url = m["url"]
            parsed = urlsplit(url)
            stamp = datetime.fromisoformat(m["received_at_jst"])
            expected_id = hashlib.sha256(url.encode("utf-8") + bytes([0]) + raw).hexdigest()
            if (m.get("schema") != "FOUR_MODE_LOCAL_RAW_HTTP_RECEIPT_V1"
                    or m.get("independent_remote_receipt_verified") is not False
                    or parsed.scheme != "https" or parsed.hostname not in ALLOWED_HOSTS
                    or parsed.username is not None or parsed.password is not None
                    or stamp.utcoffset() != timedelta(hours=9)
                    or m.get("byte_count") != len(raw)
                    or m.get("sha256") != hashlib.sha256(raw).hexdigest()
                    or identifier != expected_id):
                raise ValueError("receipt_mismatch")
        except (KeyError, TypeError, ValueError, OSError, UnicodeError):
            return {"status": "invalid_receipt", "verified": 0, "formal": False}
        ids.add(identifier)
        valid += 1
    if len(binaries) != len(manifests) or any(p.stem not in ids or p.is_symlink() for p in binaries):
        return {"status": "orphan_source_bytes", "verified": 0, "formal": False}
    return {"status": "local_integrity_verified", "verified": valid,
            "formal": False, "remote_first_seen_verified": False}


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("directory", type=Path)
    args = p.parse_args()
    print(json.dumps(audit(args.directory), sort_keys=True))

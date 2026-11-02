"""Publish immutable source receipts only after both files are complete."""
import json
import os
import shutil
import tempfile
from pathlib import Path


def publish_receipt(dest, filename, raw, report):
    dest = Path(dest)
    if dest.exists():
        raise FileExistsError("immutable observation already exists")
    dest.parent.mkdir(parents=True, exist_ok=True)
    lock = dest.with_name(dest.name + ".publish.lock")
    fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    os.close(fd)
    staging = None
    try:
        if dest.exists():
            raise FileExistsError("immutable observation already exists")
        staging = Path(tempfile.mkdtemp(prefix=".receipt-", dir=dest.parent))
        (staging / filename).write_bytes(raw)
        (staging / "manifest.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        # A rename inside the same filesystem publishes only complete pairs.
        # Never silently replace a completed observation.
        if dest.exists():
            raise FileExistsError("immutable observation already exists")
        os.rename(staging, dest)
    finally:
        if staging is not None and staging.exists():
            shutil.rmtree(staging)
        lock.unlink()

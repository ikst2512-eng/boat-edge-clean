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
    staging = Path(tempfile.mkdtemp(prefix=".receipt-", dir=dest.parent))
    try:
        (staging / filename).write_bytes(raw)
        (staging / "manifest.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        # A rename inside the same filesystem publishes only complete pairs.
        # Never silently replace a completed observation.
        if dest.exists():
            raise FileExistsError("immutable observation already exists")
        os.rename(staging, dest)
    finally:
        if staging.exists():
            shutil.rmtree(staging)

"""Isolated official PRE-RACE HTML receipt. Never fetch results or infer entries.

Not connected to production scheduling or Fresh. Callers must supply a verified
official deadline; a receipt is evidence of bytes retrieved, not parsed values.
"""
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from pathlib import Path
import json
import os
import tempfile
from urllib.request import Request, build_opener, HTTPRedirectHandler
import re

JST = timezone(timedelta(hours=9))
MAX_BYTES = 1_500_000
MIN_MARGIN = timedelta(minutes=2)


class _RejectRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError("official source redirected")


def capture_beforeinfo(race_key, deadline, *, now=None, opener=None):
    """Return a source receipt and raw bytes only for safely predeadline races.

    Does not parse HTML, save snapshots, unlock results, or call any result URL.
    """
    match = re.fullmatch(r"(20\d{6})-(0[1-9]|1\d|2[0-4])-(0?[1-9]|1[0-2])", race_key or "")
    if not match:
        raise ValueError("invalid race key")
    hd, jcd, rno = match.groups()
    try:
        race_day = datetime.strptime(hd, "%Y%m%d").date()
    except ValueError as exc:
        raise ValueError("invalid race date") from exc
    if not isinstance(deadline, datetime) or deadline.tzinfo is None:
        raise ValueError("verified timezone-aware deadline required")
    cutoff = deadline.astimezone(JST)
    if cutoff.date() != race_day:
        raise ValueError("deadline date/race date mismatch")
    started = (now or datetime.now(timezone.utc)).astimezone(JST)
    if started >= cutoff - MIN_MARGIN:
        raise ValueError("not safely before deadline")
    url = f"https://www.boatrace.jp/owpc/pc/race/beforeinfo?hd={hd}&jcd={jcd}&rno={int(rno)}"
    req = Request(url, headers={"User-Agent": "BOAT-EDGE-CLEAN/1.0", "Accept": "text/html"})
    transport = opener if opener is not None else build_opener(_RejectRedirect()).open
    with transport(req, timeout=12) as response:
        final_url = response.geturl() if hasattr(response, "geturl") else req.full_url
        if final_url != url:
            raise ValueError("official source redirected")
        content_type = response.headers.get("Content-Type", "").lower()
        if response.status != 200 or "html" not in content_type:
            raise ValueError("official HTML response not verified")
        raw = response.read(MAX_BYTES + 1)
    completed = datetime.now(timezone.utc).astimezone(JST) if now is None else started
    if len(raw) > MAX_BYTES or not raw or completed >= cutoff - MIN_MARGIN:
        raise ValueError("oversized, empty or late response")
    receipt = {
        "race_key": race_key,
        "source": url,
        "fetched_at": completed.isoformat(),
        "sha256": sha256(raw).hexdigest(),
        "bytes": len(raw),
        "status": "raw_html_only",
        "verified_preview": False,
        "actual_entry_verified": False,
        "results_seen": False,
        "unlock": False,
        "scoring": False,
    }
    return receipt, raw


def save_raw_receipt(receipt, raw, directory):
    """Atomically save research-only evidence outside public race data paths.

    No production race JSON is generated. Files are immutable for a race/digest;
    overwrite is refused even if only one member of a pair exists.
    """
    if receipt.get("status") != "raw_html_only" or receipt.get("sha256") != sha256(raw).hexdigest() or receipt.get("bytes") != len(raw):
        raise ValueError("raw receipt integrity mismatch")
    key = receipt.get("race_key", "")
    if not re.fullmatch(r"(20\d{6})-(0[1-9]|1\d|2[0-4])-(0?[1-9]|1[0-2])", key):
        raise ValueError("invalid receipt race key")
    if any(receipt.get(flag) is not False for flag in ("verified_preview", "actual_entry_verified", "results_seen", "unlock", "scoring")):
        raise ValueError("untrusted receipt flags")
    root = Path(directory)
    root.mkdir(parents=True, exist_ok=True)
    stem = key + "-" + receipt["sha256"]
    pairs = [(root / (stem + ".html"), raw), (root / (stem + ".json"), (json.dumps(receipt, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8"))]
    # Per-receipt exclusive lock prevents concurrent writers from deleting one
    # another's published files during rollback. Readers must require both files.
    lock_path = root / (stem + ".lock")
    lock_fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    pending = []
    created = []
    try:
        if any(path.exists() for path, _ in pairs):
            raise FileExistsError("receipt already exists; immutable evidence")
        for path, data in pairs:
            with tempfile.NamedTemporaryFile(dir=root, prefix=".pending-", delete=False) as fp:
                pending.append(Path(fp.name))
                fp.write(data)
                fp.flush()
                os.fsync(fp.fileno())
        for (path, _), temp in zip(pairs, pending):
            os.link(temp, path)
            created.append(path)
        # Commit marker published last: only receipts with this marker are readable.
        marker = root / (stem + ".complete")
        with tempfile.NamedTemporaryFile(dir=root, prefix=".pending-", delete=False) as fp:
            pending.append(Path(fp.name))
            fp.write(receipt["sha256"].encode("ascii") + bytes([10]))
            fp.flush()
            os.fsync(fp.fileno())
        os.link(pending[-1], marker)
        created.append(marker)
        return [str(path) for path, _ in pairs]
    except BaseException:
        for path in reversed(created):
            path.unlink(missing_ok=True)
        raise
    finally:
        for temp in pending:
            temp.unlink(missing_ok=True)
        os.close(lock_fd)
        lock_path.unlink(missing_ok=True)


def read_raw_receipt(directory, race_key, digest, *, deadline):
    """Read only a completed immutable raw receipt; never promote to verified data."""
    if not re.fullmatch(r"20\d{6}-(?:0[1-9]|1\d|2[0-4])-(?:0?[1-9]|1[0-2])", race_key or ""):
        raise ValueError("invalid race key")
    if not isinstance(digest, str) or not re.fullmatch(r"[a-f0-9]{64}", digest):
        raise ValueError("invalid digest")
    root = Path(directory)
    stem = race_key + "-" + digest
    marker = root / (stem + ".complete")
    if marker.read_bytes() != digest.encode("ascii") + bytes([10]):
        raise ValueError("invalid receipt completion marker")
    raw = (root / (stem + ".html")).read_bytes()
    json_bytes = (root / (stem + ".json")).read_bytes()
    if not raw or len(raw) > MAX_BYTES or len(json_bytes) > 8192:
        raise ValueError("invalid receipt size")
    receipt = json.loads(json_bytes)
    if not isinstance(receipt, dict) or receipt.get("race_key") != race_key or receipt.get("sha256") != digest or receipt.get("bytes") != len(raw):
        raise ValueError("receipt mismatch")
    if sha256(raw).hexdigest() != digest or receipt.get("status") != "raw_html_only":
        raise ValueError("raw receipt integrity mismatch")
    hd,jcd,rno = race_key.split("-")
    expected = f"https://www.boatrace.jp/owpc/pc/race/beforeinfo?hd={hd}&jcd={jcd}&rno={int(rno)}"
    if receipt.get("source") != expected:
        raise ValueError("receipt race source mismatch")
    # A receipt must not purport to have been captured on another race day.
    try:
        captured = datetime.fromisoformat(receipt["fetched_at"])
        race_day = datetime.strptime(hd, "%Y%m%d").date()
    except (KeyError, ValueError, TypeError) as exc:
        raise ValueError("invalid receipt capture timestamp") from exc
    if captured.tzinfo is None or captured.astimezone(JST).date() != race_day:
        raise ValueError("receipt capture date mismatch")
    if not isinstance(deadline, datetime) or deadline.tzinfo is None:
        raise ValueError("verified timezone-aware deadline required")
    cutoff = deadline.astimezone(JST)
    if cutoff.date() != race_day or captured.astimezone(JST) >= cutoff - MIN_MARGIN:
        raise ValueError("receipt was not captured in safe predeadline window")
    if any(receipt.get(flag) is not False for flag in ("verified_preview", "actual_entry_verified", "results_seen", "unlock", "scoring")):
        raise ValueError("unsafe receipt flags")
    return receipt, raw

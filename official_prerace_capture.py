"""Isolated official PRE-RACE HTML receipt. Never fetch results or infer entries.

Not connected to production scheduling or Fresh. Callers must supply a verified
official deadline; a receipt is evidence of bytes retrieved, not parsed values.
"""
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from urllib.request import Request, urlopen
import re

JST = timezone(timedelta(hours=9))
MAX_BYTES = 1_500_000
MIN_MARGIN = timedelta(minutes=2)


def capture_beforeinfo(race_key, deadline, *, now=None, opener=urlopen):
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
    with opener(req, timeout=12) as response:
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

"""Bounded public CSV source adapter for as-of historical course features.

Only older race days are loaded; timestamps and SHA256 hashes are retained.
No prediction result is fetched, and this does not certify BOAT RACE official data.
"""
from datetime import datetime, date, timedelta
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
import csv
import hashlib
import io
import re

BASE = "https://boatracecsv.github.io/data/"
MAX_DAYS = 31
MAX_BYTES = 2_000_000


def _time(text):
    try:
        result = datetime.fromisoformat(text)
        return result if result.utcoffset() is not None else None
    except (ValueError, TypeError):
        return None


def _fetch(url):
    if not url.startswith(BASE):
        raise ValueError("untrusted_history_source")
    with urlopen(Request(url, headers={"User-Agent": "BOAT-EDGE-CLEAN-RESEARCH/1.0"}), timeout=8) as response:
        if response.status != 200:
            raise ValueError("history_source_unavailable")
        raw = response.read(MAX_BYTES + 1)
        if len(raw) > MAX_BYTES:
            raise ValueError("history_source_too_large")
        return raw


def _rows(raw):
    if not isinstance(raw, bytes) or len(raw) > MAX_BYTES:
        raise ValueError("invalid_history_csv")
    return list(csv.DictReader(io.StringIO(raw.decode("utf-8-sig"))))


def load_asof_history(target_day, cutoff_at, *, lookback_days=14, fetch=None, clock=None):
    """Fetch up to 31 *older* calendar days, paired by 12-digit race code.

    Requires trustworthy local receipt time strictly before target cutoff.
    Calls with missing historical archives report failures; they do not create
    synthetic results or silently substitute target-day race outcomes.
    """
    if not isinstance(target_day, str) or not re.fullmatch(r"20\d{6}", target_day):
        raise ValueError("invalid_target_day")
    day = datetime.strptime(target_day, "%Y%m%d").date()
    cutoff = _time(cutoff_at)
    if cutoff is None or not isinstance(lookback_days, int) or not 1 <= lookback_days <= MAX_DAYS:
        raise ValueError("invalid_cutoff_or_lookback")
    fetcher = fetch or _fetch
    now = clock or (lambda: datetime.now(cutoff.tzinfo))
    if now() >= cutoff:
        raise ValueError("historical_source_not_acquired_before_cutoff")
    history = []
    failures = []
    for delta in range(1, lookback_days + 1):
        older = day - timedelta(days=delta)
        path = older.strftime("%Y/%m/%d.csv")
        chunks = {}
        for key, folder in (("card", "programs/race_cards/"), ("result", "results/realtime/")):
            url = BASE + folder + path
            try:
                raw = fetcher(url)
                received = now()
                if received.utcoffset() is None or received >= cutoff:
                    raise ValueError("historical_source_not_acquired_before_cutoff")
                chunks[key] = (_rows(raw), hashlib.sha256(raw).hexdigest(), received)
            except (OSError, UnicodeError, ValueError, HTTPError, URLError) as exc:
                if str(exc) == "historical_source_not_acquired_before_cutoff":
                    raise
                failures.append({"day": older.isoformat(), "kind": key, "reason": type(exc).__name__})
        if len(chunks) != 2:
            continue
        card_rows, card_sha, card_at = chunks["card"]
        result_rows, result_sha, result_at = chunks["result"]
        cards = {}
        for row in card_rows:
            code = row.get("レースコード")
            if code and re.fullmatch(r"20\d{10}", code) and code[:8] == older.strftime("%Y%m%d"):
                # Duplicate card keys are ambiguous, never silently choose one.
                cards.setdefault(code, []).append(row)
        seen = set()
        for row in result_rows:
            code = row.get("レースコード")
            if not code or not re.fullmatch(r"20\d{10}", code) or code[:8] != older.strftime("%Y%m%d"):
                continue
            if code in seen:
                failures.append({"day": older.isoformat(), "kind": "result", "reason": "duplicate_race_code"})
                # avoid using any duplicate result by filtering at end
            seen.add(code)
        duplicates = set()
        counts = {}
        for row in result_rows:
            code = row.get("レースコード")
            if code in seen:
                counts[code] = counts.get(code, 0) + 1
        duplicates = {code for code, n in counts.items() if n != 1}
        for row in result_rows:
            code = row.get("レースコード")
            if code not in seen or code in duplicates or len(cards.get(code, [])) != 1:
                continue
            history.append({"race_card": cards[code][0], "result": row,
                            "card_receipt_at": card_at.isoformat(),
                            "result_receipt_at": result_at.isoformat(),
                            "card_sha256": card_sha, "result_sha256": result_sha})
    return {"source": "BoatraceCSV third-party historical CSV",
            "history": history, "failed_sources": failures,
            "target_day": target_day, "cutoff_at": cutoff.isoformat(),
            "lookback_days": lookback_days, "research_only": True}

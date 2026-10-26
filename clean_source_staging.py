"""Isolated pre-publication validation for prospective CLEAN race-card imports.

This validator does not fetch upstream data, publish data, or authorize scoring.
Only callers providing independently sourced records can use its results.
"""
from datetime import datetime
from urllib.parse import urlparse
import math
import re

RACE_KEY = re.compile(r"^(20\d{6})-(0[1-9]|1\d|2[0-4])-(0[1-9]|1[0-2])$")
ALLOWED_HOSTS = {"www.boatrace.jp", "boatrace.jp"}
REQUIRED = {"race_key", "source_url", "fetched_at", "racers"}


def validate_staged_race(record):
    if not isinstance(record, dict) or not REQUIRED.issubset(record):
        raise ValueError("missing required race provenance")
    match = RACE_KEY.fullmatch(record["race_key"]) if isinstance(record["race_key"], str) else None
    if not match:
        raise ValueError("invalid race key")
    datetime.strptime(match.group(1), "%Y%m%d")
    url = urlparse(record["source_url"]) if isinstance(record["source_url"], str) else None
    if not url or url.scheme != "https" or url.hostname not in ALLOWED_HOSTS or url.username or url.password:
        raise ValueError("unapproved official source")
    if not url.path.startswith("/owpc/pc/race/"):
        raise ValueError("source is not an official race endpoint")
    from urllib.parse import parse_qs
    params = parse_qs(url.query)
    if any(len(params.get(k, [])) != 1 for k in ("hd", "jcd", "rno")):
        raise ValueError("source race identity absent")
    if (params["hd"][0], params["jcd"][0].zfill(2), params["rno"][0].zfill(2)) != match.groups():
        raise ValueError("cross-race source mismatch")
    try:
        dt = datetime.fromisoformat(record["fetched_at"])
    except (TypeError, ValueError):
        raise ValueError("invalid retrieval time") from None
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise ValueError("timezone-aware retrieval required")
    racers = record["racers"]
    if not isinstance(racers, list) or len(racers) != 6:
        raise ValueError("exactly six racers required")
    lanes = []
    for racer in racers:
        if not isinstance(racer, dict) or type(racer.get("lane")) is not int:
            raise ValueError("lane missing")
        lanes.append(racer["lane"])
        if not isinstance(racer.get("name"), str) or not racer["name"].strip():
            raise ValueError("racer name missing")
    if sorted(lanes) != [1, 2, 3, 4, 5, 6]:
        raise ValueError("lanes missing or duplicated")
    if record.get("results_seen") is not False or record.get("unlock") is not False or record.get("scoring") is not False:
        raise ValueError("pre-result guard not closed")
    return {"race_key": record["race_key"], "source_url": record["source_url"], "fetched_at": dt.isoformat(), "lanes": sorted(lanes), "status": "staged_unpublished"}


if __name__ == "__main__":
    raise SystemExit("Library-only validator: no standalone publishing action")

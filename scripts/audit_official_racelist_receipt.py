"""Independent inspection of archived official racelist bytes (research only)."""
import hashlib
import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlencode

def audit_racelist(directory, race_code, cutoff_jst):
    directory = Path(directory)
    raw = (directory / "racelist.html").read_bytes()
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    if not isinstance(race_code, str) or not re.fullmatch(r"20[0-9]{10}", race_code):
        raise ValueError("invalid requested race")
    day, venue, number = race_code[:8], int(race_code[8:10]), int(race_code[10:])
    if venue not in range(1, 25) or number not in range(1, 13):
        raise ValueError("invalid requested race")
    expected = "https://www.boatrace.jp/owpc/pc/race/racelist?" + urlencode(
        {"hd": day, "jcd": f"{venue:02d}", "rno": str(number)})
    if manifest.get("race_code") != race_code or manifest.get("official_url") != expected:
        raise ValueError("source identity mismatch")
    if manifest.get("status") != "official_racelist_html_observed_research_only":
        raise ValueError("unverified source status")
    if hashlib.sha256(raw).hexdigest() != manifest.get("sha256") or len(raw) != manifest.get("bytes"):
        raise ValueError("source bytes mismatch")
    if not 0 < len(raw) <= 1_500_000:
        raise ValueError("source size invalid")
    if not raw.lstrip()[:256].lower().startswith((b"<!doctype html", b"<html")):
        raise ValueError("non-HTML original")
    started = datetime.fromisoformat(manifest["request_started_at_jst"])
    received = datetime.fromisoformat(manifest["received_at_jst"])
    cutoff = datetime.fromisoformat(cutoff_jst)
    if any(t.utcoffset() != timedelta(hours=9) for t in (started, received, cutoff)):
        raise ValueError("non-JST timestamps")
    if received < started or received.strftime("%Y%m%d") != day or cutoff.strftime("%Y%m%d") != day:
        raise ValueError("invalid chronology or day")
    return {
        "race_code": race_code, "original_hash_verified": True,
        "racelist_received_jst": received.isoformat(),
        "received_by_t12": received <= cutoff,
        "six_racers_verified": False, "entry_verified": False,
        "full_t12_source_certified": False,
        "t12_eligible": False, "forecast_usable": False,
    }

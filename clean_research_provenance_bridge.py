"""Research-only bridge guard for two independently captured race sources.

Never converts unverified source material into verified exhibition/actual entry.
"""
from datetime import datetime, timedelta, timezone
import re

JST = timezone(timedelta(hours=9))
KEY = re.compile(r"20[0-9]{6}-(?:0[1-9]|1[0-9]|2[0-4])-(?:0[1-9]|1[0-2])")
DIGEST = re.compile(r"[a-f0-9]{64}")

def compare_capture_identity(racelist, beforeinfo, *, deadline):
    if not isinstance(racelist, dict) or not isinstance(beforeinfo, dict):
        raise ValueError("missing provenance")
    race_key = racelist.get("race_key")
    if not isinstance(race_key, str) or not KEY.fullmatch(race_key):
        raise ValueError("invalid race identity")
    if beforeinfo.get("race_key") != race_key:
        raise ValueError("cross-race contamination")
    if racelist.get("status") != "html_candidates_unverified":
        raise ValueError("racelist candidates unavailable")
    if beforeinfo.get("status") != "research_unverified":
        raise ValueError("beforeinfo research unavailable")
    if beforeinfo.get("verified_preview") is not False or beforeinfo.get("actual_entry_verified") is not False:
        raise ValueError("unsafe promotion flags")
    if not isinstance(beforeinfo.get("raw_sha256"), str) or not DIGEST.fullmatch(beforeinfo["raw_sha256"]):
        raise ValueError("missing hash provenance")
    rows = beforeinfo.get("start_exhibition")
    if not isinstance(rows, list) or len(rows) != 6:
        raise ValueError("incomplete exhibition")
    if sorted(x.get("boat_number") for x in rows if isinstance(x, dict)) != list(range(1,7)):
        raise ValueError("duplicate or missing boat number")
    try:
        captured = datetime.fromisoformat(beforeinfo["captured_at"])
    except (KeyError, ValueError, TypeError) as e:
        raise ValueError("invalid capture timestamp") from e
    if captured.tzinfo is None or not isinstance(deadline, datetime) or deadline.tzinfo is None:
        raise ValueError("timezone required")
    day = datetime.strptime(race_key[:8], "%Y%m%d").date()
    if captured.astimezone(JST).date() != day or deadline.astimezone(JST).date() != day:
        raise ValueError("race day mismatch")
    if captured.astimezone(JST) >= deadline.astimezone(JST) - timedelta(minutes=2):
        raise ValueError("capture outside safe two-minute predeadline margin")
    return {"race_key": race_key, "status": "bridged_unverified",
            "official_preview_values_equal": False,
            "actual_entry_verified": False, "verified_preview": False,
            "source_sha256": beforeinfo["raw_sha256"]}

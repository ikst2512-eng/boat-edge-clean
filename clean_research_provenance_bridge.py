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
    try:
        race_day = datetime.strptime(race_key[:8], "%Y%m%d").date()
    except ValueError as exc:
        raise ValueError("invalid calendar date") from exc
    if beforeinfo.get("race_key") != race_key:
        raise ValueError("cross-race contamination")
    if racelist.get("status") != "html_candidates_unverified":
        raise ValueError("racelist candidates unavailable")
    racers = racelist.get("racers")
    if not isinstance(racers, list) or len(racers) != 6:
        raise ValueError("incomplete racelist")
    if any(not isinstance(x, dict) or type(x.get("lane")) is not int
           or not isinstance(x.get("registration"), str)
           or not re.fullmatch(r"[0-9]{4}", x["registration"])
           for x in racers):
        raise ValueError("invalid racelist racer")
    if sorted(x["lane"] for x in racers) != list(range(1, 7)):
        raise ValueError("duplicate or missing racelist lane")
    if len({x["registration"] for x in racers}) != 6:
        raise ValueError("duplicate racer registration")
    if racelist.get("official_provenance_verified") is not False:
        raise ValueError("unsafe racelist provenance promotion")
    if beforeinfo.get("status") != "research_unverified":
        raise ValueError("beforeinfo research unavailable")
    if beforeinfo.get("verified_preview") is not False or beforeinfo.get("actual_entry_verified") is not False:
        raise ValueError("unsafe promotion flags")
    if not isinstance(beforeinfo.get("raw_sha256"), str) or not DIGEST.fullmatch(beforeinfo["raw_sha256"]):
        raise ValueError("missing hash provenance")
    rows = beforeinfo.get("start_exhibition")
    if not isinstance(rows, list) or len(rows) != 6:
        raise ValueError("incomplete exhibition")
    if any(not isinstance(x, dict) or type(x.get("boat_number")) is not int for x in rows):
        raise ValueError("invalid exhibition record")
    if sorted(x["boat_number"] for x in rows) != list(range(1,7)):
        raise ValueError("duplicate or missing boat number")
    try:
        captured = datetime.fromisoformat(beforeinfo["captured_at"])
    except (KeyError, ValueError, TypeError) as e:
        raise ValueError("invalid capture timestamp") from e
    if captured.tzinfo is None or not isinstance(deadline, datetime) or deadline.tzinfo is None:
        raise ValueError("timezone required")
    if captured.astimezone(JST).date() != race_day or deadline.astimezone(JST).date() != race_day:
        raise ValueError("race day mismatch")
    if captured.utcoffset() != timedelta(hours=9) or deadline.utcoffset() != timedelta(hours=9):
        raise ValueError("JST +09:00 provenance required")
    if captured.astimezone(JST) >= deadline.astimezone(JST) - timedelta(minutes=2):
        raise ValueError("capture outside safe two-minute predeadline margin")
    return {"race_key": race_key, "status": "bridged_unverified",
            "official_preview_values_equal": False,
            "actual_entry_verified": False, "verified_preview": False,
            "source_sha256": beforeinfo["raw_sha256"]}

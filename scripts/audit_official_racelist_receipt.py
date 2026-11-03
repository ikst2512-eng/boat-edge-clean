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
    if not raw.lstrip()[:256].lower().startswith((b"<!doctype html", b"<html", b"<?xml")):
        raise ValueError("non-HTML original")
    started = datetime.fromisoformat(manifest["request_started_at_jst"])
    received = datetime.fromisoformat(manifest["received_at_jst"])
    cutoff = datetime.fromisoformat(cutoff_jst)
    if any(t.utcoffset() != timedelta(hours=9) for t in (started, received, cutoff)):
        raise ValueError("non-JST timestamps")
    if received < started or received.strftime("%Y%m%d") != day or cutoff.strftime("%Y%m%d") != day:
        raise ValueError("invalid chronology or day")
    from scripts.diagnose_official_racelist_html import diagnose_racelist_html
    html_diagnostics = diagnose_racelist_html(raw)
    from scripts.inspect_official_racelist_registrations import inspect_six_registrations
    racer_check = inspect_six_registrations(raw)
    return {
        "race_code": race_code, "original_hash_verified": True,
        "html_diagnostics": html_diagnostics,
        "registrations_by_lane": racer_check["registrations_by_lane"],
        "racelist_received_jst": received.isoformat(),
        "received_before_supplied_cutoff": received <= cutoff,
        "cutoff_source_verified": False,
        "six_racers_verified": racer_check["six_racers_verified"], "entry_verified": False,
        "full_t12_source_certified": False,
        "t12_eligible": False, "forecast_usable": False,
    }


def audit_racelist_with_official_deadline(racelist_dir, beforeinfo_dir, race_code):
    """Derive the T12 cutoff from independently archived official beforeinfo."""
    from scripts.inspect_official_beforeinfo_json import inspect
    beforeinfo_dir = Path(beforeinfo_dir)
    original = (beforeinfo_dir / "beforeinfo.json").read_bytes()
    metadata = json.loads((beforeinfo_dir / "manifest.json").read_text(encoding="utf-8"))
    if hashlib.sha256(original).hexdigest() != metadata.get("sha256") or len(original) != metadata.get("bytes"):
        raise ValueError("beforeinfo source integrity mismatch")
    if metadata.get("race_code") != race_code or metadata.get("status") != "official_json_observed_not_t12_certified":
        raise ValueError("beforeinfo race identity/status mismatch")
    day, venue, number = race_code[:8], race_code[8:10], str(int(race_code[10:]))
    expected = "https://www.boatrace.jp/owsp/sp/spdata?type=beforeinfo&" + urlencode(
        {"hd": day, "jcd": venue, "rno": number})
    if metadata.get("url") != expected:
        raise ValueError("beforeinfo official URL mismatch")
    before_started = datetime.fromisoformat(metadata["request_started_at_jst"])
    before_received = datetime.fromisoformat(metadata["received_at_jst"])
    if (before_started.utcoffset() != timedelta(hours=9)
            or before_received.utcoffset() != timedelta(hours=9)
            or before_received < before_started
            or before_started.strftime("%Y%m%d") != day
            or before_received.strftime("%Y%m%d") != day):
        raise ValueError("invalid beforeinfo chronology")
    source = json.loads(original).get("maindata")
    if not isinstance(source, dict) or str(source.get("hd")) != day or str(source.get("jcd")).zfill(2) != venue or str(source.get("rno")) != number:
        raise ValueError("beforeinfo original race identity mismatch")
    deadline_text = inspect({"maindata": source})["deadline_display"]
    if not isinstance(deadline_text, str) or not re.fullmatch(r"(?:[01][0-9]|2[0-3]):[0-5][0-9]", deadline_text):
        raise ValueError("invalid official deadline")
    cutoff = datetime.fromisoformat(
        f"{day[:4]}-{day[4:6]}-{day[6:8]}T{deadline_text}:00+09:00") - timedelta(minutes=12)
    result = audit_racelist(racelist_dir, race_code, cutoff.isoformat())
    inspection = inspect({"maindata": source})
    exhibition_map = inspection["exhibition_course_to_boat"]
    result["beforeinfo_received_by_t12"] = before_received <= cutoff
    result["exhibition_entry_received_by_t12"] = (before_received <= cutoff and bool(exhibition_map))
    result["exhibition_course_to_boat"] = exhibition_map
    result["racecard_and_exhibition_entry_observed_by_t12"] = bool(
        result["received_before_supplied_cutoff"] and before_received <= cutoff
        and result["six_racers_verified"] and len(exhibition_map) == 6)
    result["received_by_t12"] = result["received_before_supplied_cutoff"]
    result["cutoff_source_verified"] = True
    result["cutoff_provenance"] = "verified_original_beforeinfo"
    result["official_deadline_jst"] = (cutoff + timedelta(minutes=12)).isoformat()
    result["beforeinfo_received_jst"] = before_received.isoformat()
    # Exhibition course mapping is not final entry. No forecast permission is granted.
    return result

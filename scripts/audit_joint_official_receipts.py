"""Audit a pair of independently archived official sources, never approve forecasts."""
import hashlib
import json
from datetime import datetime, timedelta
from pathlib import Path
from scripts.inspect_official_beforeinfo_json import inspect
from scripts.inspect_official_odds_receipt import inspect_odds_receipt
from server import parse_official_odds_table


def audit_pair(before_dir, odds_dir):
    before_dir, odds_dir = Path(before_dir), Path(odds_dir)
    def load(directory, filename):
        raw = (directory / filename).read_bytes()
        manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
        if hashlib.sha256(raw).hexdigest() != manifest.get("sha256") or len(raw) != manifest.get("bytes"):
            raise ValueError("original source mismatch")
        start = datetime.fromisoformat(manifest["request_started_at_jst"])
        received = datetime.fromisoformat(manifest["received_at_jst"])
        if start.utcoffset() != timedelta(hours=9) or received.utcoffset() != timedelta(hours=9) or received < start:
            raise ValueError("invalid receipt chronology")
        return raw, manifest, received
    original_before, a, a_received = load(before_dir, "beforeinfo.json")
    original_odds, b, b_received = load(odds_dir, "original.html")
    if a.get("status") != "official_json_observed_not_t12_certified" or b.get("status") != "official_odds_observed_research_only":
        raise ValueError("not successful original source observations")
    race = a["race_code"]
    if race != b.get("race_code") or len(race) != 12 or not race.isdigit():
        raise ValueError("race identity mismatch")
    source = json.loads(original_before)["maindata"]
    if str(source.get("hd")) != race[:8] or str(source.get("jcd")).zfill(2) != race[8:10] or str(source.get("rno")) != str(int(race[10:])):
        raise ValueError("original beforeinfo race identity mismatch")
    check = inspect(json.loads(original_before))
    deadline = datetime.fromisoformat(race[:4] + "-" + race[4:6] + "-" + race[6:8] + "T" + check["deadline_display"] + ":00+09:00")
    if b.get("deadline_at_jst") != deadline.isoformat():
        raise ValueError("odds deadline differs from official beforeinfo")
    cutoff = deadline - timedelta(minutes=12)
    odds = parse_official_odds_table(original_odds.decode("utf-8", "replace"))
    odds_check = inspect_odds_receipt(odds, race_code=race, received_at_jst=b_received.isoformat(), deadline_jst=deadline.isoformat())
    exhibition_complete = bool(check["six_unique_boats"] and check["exhibition_time_nonempty_six"] and check["tilt_observed_boats"] == 6 and check["start_exhibition_six_valid_rows"])
    # Diagnostics come from original-source reinspection; gate stays unchanged.
    component_checks = {
        "six_unique_boats": bool(check["six_unique_boats"]),
        "exhibition_time_six": bool(check["exhibition_time_nonempty_six"]),
        "tilt_six": check["tilt_observed_boats"] == 6,
        "start_exhibition_six": bool(check["start_exhibition_six_valid_rows"]),
        "beforeinfo_received_by_t12": a_received <= cutoff,
        "official_odds_120": bool(odds_check["valid_120_combinations"]),
        "odds_received_by_t12": bool(odds_check["complete_odds_observed_before_t12"]),
    }
    missing_components = [name for name, passed in component_checks.items() if not passed]
    joint = exhibition_complete and a_received <= cutoff and odds_check["complete_odds_observed_before_t12"]
    return {"race_code": race, "cutoff_jst": cutoff.isoformat(), "before_received_jst": a_received.isoformat(),
            "odds_received_jst": b_received.isoformat(), "originals_hash_verified": True,
            "exhibition_complete": exhibition_complete, "odds_120_complete": odds_check["valid_120_combinations"],
            "both_complete_before_t12": bool(joint), "component_checks": component_checks,
            "missing_components": missing_components, "forecast_usable": False, "t12_eligible": False}

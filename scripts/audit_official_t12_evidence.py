"""Independent, fail-closed reinspection of immutable official HTTP evidence.

A pre-cutoff complete observation is NOT formal forecast eligibility.
"""
import argparse
import hashlib
import json
from datetime import datetime, timedelta
from pathlib import Path

from scripts.inspect_official_beforeinfo_json import inspect


def recheck(directory, cutoff_iso, expected_race_code):
    path = Path(directory)
    manifest = json.loads((path / "manifest.json").read_text(encoding="utf-8"))
    original = (path / "beforeinfo.json").read_bytes()
    cutoff = datetime.fromisoformat(cutoff_iso)
    start = datetime.fromisoformat(manifest["request_started_at_jst"])
    received = datetime.fromisoformat(manifest["received_at_jst"])
    if not all(t.utcoffset() == timedelta(hours=9) for t in (cutoff, start, received)):
        raise ValueError("all timestamps must be JST")
    if start > received:
        raise ValueError("request chronology reversed")
    if manifest.get("race_code") != expected_race_code:
        raise ValueError("race identity mismatch")
    day, venue, race = expected_race_code[:8], str(int(expected_race_code[8:10])), str(int(expected_race_code[10:]))
    if manifest.get("sha256") != hashlib.sha256(original).hexdigest() or manifest.get("bytes") != len(original):
        raise ValueError("source bytes do not match original manifest")
    payload = json.loads(original)
    main = payload["maindata"]
    if str(main.get("hd")) != day or str(main.get("jcd")) != venue or str(main.get("rno")) != race:
        raise ValueError("source race identity mismatch")
    result = inspect(payload)
    deadline = result.get("deadline_display")
    if not isinstance(deadline, str):
        raise ValueError("missing source deadline")
    clock = datetime.strptime(deadline, "%H:%M").time()
    deadline_at = datetime.combine(start.date(), clock, tzinfo=start.tzinfo)
    if deadline_at - timedelta(minutes=12) != cutoff:
        raise ValueError("source deadline and claimed cutoff disagree")
    full = (result["six_unique_boats"] and result["exhibition_time_nonempty_six"]
            and result["tilt_observed_boats"] == 6
            and result["start_exhibition_six_valid_rows"])
    return {
        "race_code": expected_race_code,
        "received_at_jst": received.isoformat(),
        "deadline_display": deadline,
        "source_sha256_verified": True,
        "complete_official_beforeinfo_observed_before_t12": bool(full and received <= cutoff),
        "exhibition_time_observed_boats": result["exhibition_time_observed_boats"],
        "tilt_observed_boats": result["tilt_observed_boats"],
        "start_exhibition_six_valid_rows": result["start_exhibition_six_valid_rows"],
        "t12_eligible": False,
        "forecast_usable": False,
        "status": "research_evidence_rechecked_not_forecast_certified",
    }


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("directory")
    p.add_argument("--cutoff", required=True)
    p.add_argument("--race-code", required=True)
    a = p.parse_args()
    print(json.dumps(recheck(a.directory, a.cutoff, a.race_code), ensure_ascii=False, indent=2))

"""Read-only official exhibition fallback; never a formal forecast input."""
import hashlib
import json
import re
from datetime import datetime, timedelta
from urllib.request import Request, urlopen

from research_model import JST
from scripts.inspect_official_beforeinfo_json import inspect


def preview(code, deadline, racers, fetch=None, clock=None):
    audit = {"status": "not_published_or_unavailable", "formal_t12_certified": False}
    try:
        if (not re.fullmatch(r"20[0-9]{10}", code)
                or deadline.utcoffset() != timedelta(hours=9)
                or deadline.strftime("%Y%m%d") != code[:8]):
            raise ValueError("invalid_race_or_deadline")
        clock = clock or (lambda: datetime.now(JST))
        started = clock()
        if started.utcoffset() != timedelta(hours=9) or started >= deadline:
            raise ValueError("deadline_passed")
        url = ("https://www.boatrace.jp/owsp/sp/spdata?type=beforeinfo&hd=" + code[:8]
               + "&jcd=" + code[8:10] + "&rno=" + str(int(code[10:])))
        if fetch is None:
            request = Request(url, headers={"User-Agent": "BOAT-EDGE-CLEAN/1.0",
                              "Accept": "application/json",
                              "X-Requested-With": "XMLHttpRequest"})
            with urlopen(request, timeout=10) as response:
                if response.status != 200 or response.geturl() != url:
                    raise ValueError("unexpected_official_response")
                raw = response.read(1_000_001)
        else:
            raw = fetch(url)
        received = clock()
        if (received.utcoffset() != timedelta(hours=9)
                or not started <= received < deadline):
            raise ValueError("receipt_not_before_deadline")
        if not isinstance(raw, bytes) or not 0 < len(raw) <= 1_000_000:
            raise ValueError("invalid_response_size")
        data = json.loads(raw)
        main = data["maindata"]
        if (str(main.get("hd")) != code[:8] or str(main.get("jcd")).zfill(2) != code[8:10]
                or str(main.get("rno")) != str(int(code[10:]))
                or main.get("deadline") != deadline.strftime("%H:%M")):
            raise ValueError("official_race_or_deadline_mismatch")
        checked = inspect(data)
        # Preserve field-level evidence even when the official endpoint returns
        # a racecard before the six exhibition measurements are published.
        audit["official_measurement_counts"] = {
            "racers": checked["racers_listed"],
            "exhibition_time": checked["exhibition_time_observed_boats"],
            "tilt": checked["tilt_observed_boats"],
            "start_rows": checked["start_exhibition_rows"],
            "start_valid_six": checked["start_exhibition_six_valid_rows"],
        }
        missing = []
        if not checked["six_unique_boats"]:
            missing.append("six_unique_boats")
        if not checked["exhibition_time_nonempty_six"]:
            missing.append("exhibition_time")
        if checked["tilt_observed_boats"] != 6:
            missing.append("tilt")
        if not checked["start_exhibition_six_valid_rows"]:
            missing.append("start_exhibition")
        if missing:
            audit["missing_official_fields"] = missing
            raise ValueError("incomplete_official_exhibition")
        expected = {str(r["lane"]): str(r["registration_no"]) for r in racers}
        rows = main["teiinfolist"]
        actual = {str(r["teino"]): str(r["racerno"]) for r in rows}
        if (set(expected) != set("123456") or len(set(expected.values())) != 6
                or actual != expected or any(r.get("absentflag") not in (0, "0") for r in rows)):
            raise ValueError("official_racer_or_absence_mismatch")
        exhibitions = [{"lane": int(r["teino"]), "exhibition_time": float(r["extime"]),
                        "tilt": float(r["tilt"])} for r in rows]
        if any(not 5 <= r["exhibition_time"] <= 9 or not -1 <= r["tilt"] <= 3 for r in exhibitions):
            raise ValueError("invalid_exhibition_measurement")
        starts = [{"lane": int(r["teino"]), "course": int(r["cs"]), "st": r["st"].strip()}
                  for r in main["sttenjiinfolist"]]
        if any(re.fullmatch(r"(?:F|L)?\.\d{1,2}|\d?\.\d{1,2}", r["st"]) is None for r in starts):
            raise ValueError("unsupported_start_measurement")
        digest = hashlib.sha256(raw).hexdigest()
        audit.update(status="ok", source="BOAT RACE official beforeinfo JSON", source_url=url,
                     fetched_at=received.isoformat(), sha256=digest, received_at_jst=received.isoformat(),
                     observation_time_basis="local HTTP completion; upstream measurement time unproven",
                     sources={"official": {"url": url, "sha256": digest,
                                           "received_at_jst": received.isoformat()}})
        return {"racers": sorted(exhibitions, key=lambda r: r["lane"]),
                "start_exhibition": sorted(starts, key=lambda r: r["lane"])}, audit
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
        audit["reason"] = str(exc)[:120] if isinstance(exc, ValueError) else type(exc).__name__
        return None, audit

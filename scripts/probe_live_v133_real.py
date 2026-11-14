"""One-shot read-only production V127/V133 probe using genuinely upcoming races.

Does not create, save, backfill or score predictions. A source-unavailable verdict
is NOT evidence of successful forecast generation. No new schedule is installed.
"""
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import json
import re

JST = timezone(timedelta(hours=9))
ROOT = Path(__file__).resolve().parents[1]
BASE = "https://boat-edge-clean.onrender.com"
MODEL = "V127_V133_SOURCE_PORT_INPUT_GUARDED_REFERENCE_V1"


def upcoming(schedule, now):
    if str(schedule.get("date") or "").replace("-", "") != now.strftime("%Y%m%d"):
        return []
    items = []
    for venue in schedule.get("venues") or []:
        jcd = str(venue.get("jcd", "")).zfill(2)
        if not re.fullmatch(r"0[1-9]|1[0-9]|2[0-4]", jcd):
            continue
        for race in venue.get("races") or []:
            rno = race.get("race_no")
            cutoff = race.get("deadline")
            if type(rno) is not int or not 1 <= rno <= 12:
                continue
            if not isinstance(cutoff, str) or not re.fullmatch(r"[0-2][0-9]:[0-5][0-9]", cutoff):
                continue
            try:
                deadline = datetime.strptime(now.strftime("%Y%m%d") + cutoff,
                                             "%Y%m%d%H:%M").replace(tzinfo=JST)
            except ValueError:
                continue
            remaining = (deadline - now).total_seconds() / 60
            if 2 < remaining <= 65:
                items.append((remaining, now.strftime("%Y%m%d"), jcd, rno))
    return sorted(items)[:2]


def read_probe(url):
    try:
        with urlopen(Request(url, headers={"User-Agent": "BOAT-EDGE-CLEAN-V133-one-shot-e2e/1",
                                           "Cache-Control": "no-cache"}), timeout=45) as res:
            return res.status, json.load(res)
    except HTTPError as exc:
        try:
            return exc.code, json.load(exc)
        except (ValueError, UnicodeError):
            return exc.code, {"status": "non_json_error"}
    except (TimeoutError, OSError, URLError) as exc:
        return None, {"status": "transport_unavailable", "error_type": type(exc).__name__}


def main():
    now = datetime.now(JST)
    path = ROOT / "schedule_snapshots" / (now.strftime("%Y%m%d") + ".json")
    if not path.is_file():
        print("LIVE_V133_NO_SCHEDULE_SNAPSHOT: no future-race claim", flush=True)
        return
    records = upcoming(json.loads(path.read_text(encoding="utf-8")), now)
    if not records:
        print("LIVE_V133_NO_UPCOMING_RACE: no current-source claim", flush=True)
        return
    verified = 0
    for delta, hd, jcd, rno in records:
        code = hd + jcd + f"{rno:02d}"
        url = BASE + "/api/v133-reference-preview?" + urlencode({"hd": hd, "jcd": jcd, "rno": rno})
        status, payload = read_probe(url)
        evidence = {
            "race_code": code,
            "minutes_to_scheduled_deadline_at_probe": round(delta, 1),
            "http_status": status,
            "api_status": payload.get("status"),
            "reason": payload.get("reason"),
            "model_version": payload.get("model_version"),
            "pre_result_only": payload.get("formal") is False,
            "modes": {k: len(v.get("tickets") or [])
                      for k, v in (payload.get("modes") or {}).items()},
            "racecard_verified": (payload.get("source_audit") or {}).get("race_card", {}).get("status") == "ok",
            "beforeinfo_verified": (payload.get("source_audit") or {}).get("beforeinfo", {}).get("status") == "ok",
        }
        if status == 200:
            expected = {"narrow": 3, "hit": 10, "balance": 10}
            assert payload.get("ok") is True and payload.get("model_version") == MODEL
            assert payload.get("formal") is False and payload.get("calibrated") is False
            assert payload.get("production_buy_approved") is False
            assert evidence["racecard_verified"] and evidence["beforeinfo_verified"]
            assert all(evidence["modes"].get(k) == count for k, count in expected.items())
            assert evidence["modes"].get("hole") in (12, 15, 18)
            verified += 1
            evidence["outcome"] = "actual_same_race_v133_reference_http_200_verified"
        elif status in (404, 422, 503):
            evidence["outcome"] = "no_valid_v133_prediction_confirmed"
        elif status is None:
            evidence["outcome"] = "transport_not_verified"
        else:
            raise AssertionError("Unexpected V133 public HTTP or malformed response: " + json.dumps(evidence))
        print("LIVE_V133_REAL_SOURCE " + json.dumps(evidence, ensure_ascii=False, sort_keys=True), flush=True)
    print(f"LIVE_V133_SUCCESSFUL_RACES={verified}/{len(records)}; not a formal-accuracy claim", flush=True)


if __name__ == "__main__":
    main()

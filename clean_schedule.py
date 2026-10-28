"""Independent CLEAN daily schedule from the published third-party race-title CSV.

Does not read ikst2512-eng/boat-edge. This is schedule discovery, not a
verified official result, formal forecast, or guaranteed real-time feed.
"""
from collections import Counter
from datetime import datetime
from urllib.error import HTTPError, URLError
import logging
import re
from research_model import BASE, JST, read_rows


def parse_schedule(day, rows, received_at):
    if not re.fullmatch(r"[0-9]{8}", day):
        raise ValueError("invalid date")
    datetime.strptime(day, "%Y%m%d")
    counts = Counter(row.get("レースコード") for row in rows if isinstance(row, dict))
    if any(count != 1 for key, count in counts.items() if isinstance(key, str) and key.startswith(day)):
        raise ValueError("duplicate race identifiers")
    races = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        code = row.get("レースコード", "")
        if not isinstance(code, str) or not re.fullmatch(day + r"(0[1-9]|1[0-9]|2[0-4])(0[1-9]|1[0-2])", code):
            continue
        clock = row.get("電話投票締切予定", "")
        if not isinstance(clock, str) or not re.fullmatch(r"[0-2][0-9]:?[0-5][0-9]", clock):
            raise ValueError("missing deadline")
        hhmm = clock.replace(":", "")
        deadline = datetime.strptime(day + hhmm, "%Y%m%d%H%M").replace(tzinfo=JST)
        races.append({"race_code": code, "venue_code": code[8:10],
                      "race_no": int(code[10:12]), "deadline_jst": deadline.isoformat()})
    if not races:
        raise ValueError("no valid races")
    return {"ok": True, "date": day, "status": "published_schedule",
            "formal": False, "results_confirmed": False,
            "source": "boatracecsv.github.io/data/programs/title",
            "source_received_jst": received_at.isoformat(),
            "races": sorted(races, key=lambda r: (r["deadline_jst"], r["race_code"]))}


def clean_schedule(day):
    if not isinstance(day, str) or not re.fullmatch(r"[0-9]{8}", day):
        return 400, {"ok": False, "status": "invalid_date"}
    try:
        datetime.strptime(day, "%Y%m%d")
    except ValueError:
        return 400, {"ok": False, "status": "invalid_date"}
    path = f"{day[:4]}/{day[4:6]}/{day[6:8]}.csv"
    try:
        rows, received_at, digest = read_rows(BASE + "title/" + path)

    except HTTPError as exc:
        if exc.code in (404, 410):
            return 404, {"ok": False, "status": "schedule_not_published",
                         "source": "boatracecsv.github.io/data/programs/title",
                         "date": day, "upstream_http_status": exc.code,
                         "retryable": exc.code == 404}
        logging.warning("schedule_upstream_http_error date=%s status=%s", day, exc.code)
        return 503, {"ok": False, "status": "source_unavailable",
                     "reason": "upstream_http_error",
                     "upstream_http_status": exc.code,
                     "date": day,
                     "retryable": exc.code in (408,429,500,502,503,504)}
    except (TimeoutError, URLError, OSError) as exc:
        return 503, {"ok": False, "status": "source_unavailable",
                     "reason": type(exc).__name__, "date": day, "retryable": True}
    except (UnicodeError, ValueError, TypeError) as exc:
        logging.warning("schedule_source_invalid date=%s reason=%s", day, type(exc).__name__)
        return 502, {"ok": False, "status": "source_invalid",
                     "reason": type(exc).__name__, "date": day, "retryable": False}
    except Exception:
        logging.exception("schedule_internal_error date=%s", day)
        return 500, {"ok": False, "status": "internal_error", "date": day,
                     "retryable": False}
    try:
        result = parse_schedule(day, rows, received_at)
    except (ValueError, TypeError, KeyError) as exc:
        logging.warning("schedule_csv_invalid date=%s reason=%s", day, type(exc).__name__)
        return 502, {"ok": False, "status": "source_invalid",
                     "reason": type(exc).__name__, "date": day, "retryable": False}
    result["source_sha256"] = digest
    return 200, result

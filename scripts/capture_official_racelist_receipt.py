"""Research-only immutable official racecard HTML receipt; NOT T12 certification."""
import argparse
import hashlib
import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from research_model import JST
from scripts.publish_official_receipt import publish_receipt

MAX_BYTES = 1_500_000
HOST = "https://www.boatrace.jp"


def capture(race_code, root, observation_id, *, fetch=None, clock=None):
    if not isinstance(race_code, str) or not re.fullmatch(r"20[0-9]{10}", race_code):
        raise ValueError("invalid race code")
    day, venue, number = race_code[:8], int(race_code[8:10]), int(race_code[10:])
    datetime.strptime(day, "%Y%m%d")
    if not 1 <= venue <= 24 or not 1 <= number <= 12:
        raise ValueError("invalid race identity")
    if not isinstance(observation_id, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", observation_id):
        raise ValueError("invalid observation ID")
    url = HOST + "/owpc/pc/race/racelist?" + urlencode(
        {"hd": day, "jcd": f"{venue:02d}", "rno": str(number)})
    dest = Path(root) / "observations" / observation_id / day / race_code
    if dest.exists():
        raise FileExistsError("cannot overwrite immutable receipt")
    now = clock or (lambda: datetime.now(JST))
    started = now()
    report = {
        "race_code": race_code, "official_url": url,
        "request_started_at_jst": started.isoformat(),
        "racecard_content_verified": False, "entry_verified": False,
        "t12_eligible": False, "forecast_usable": False,
    }
    try:
        if fetch is not None:
            raw = fetch(url)
        else:
            request = Request(url, headers={"User-Agent": "Mozilla/5.0", "Accept": "text/html"})
            with urlopen(request, timeout=18) as response:
                if response.status != 200 or response.geturl() != url:
                    raise ValueError("unexpected racecard source response")
                raw = response.read(MAX_BYTES + 1)
        received = now()
        report["received_at_jst"] = received.isoformat()
        if (started.utcoffset() != timedelta(hours=9) or received.utcoffset() != timedelta(hours=9)
                or received < started):
            raise ValueError("invalid JST chronology")
        if not isinstance(raw, bytes) or not 0 < len(raw) <= MAX_BYTES:
            raise ValueError("invalid original bytes")
        prefix = raw.lstrip()[:256].lower()
        if not (prefix.startswith(b"<!doctype html") or prefix.startswith(b"<html")):
            raise ValueError("non-HTML source response")
        report.update(status="official_racelist_html_observed_research_only",
                      sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw))
        publish_receipt(dest, "racelist.html", raw, report)
    except Exception as exc:
        report.update(status="official_racelist_probe_failed", error=type(exc).__name__,
                      error_reason=(str(exc)[:180] if isinstance(exc, ValueError) else ""),
                      http_status=getattr(exc, "code", None))
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("race_code")
    parser.add_argument("--root", default="official_racelist_evidence")
    parser.add_argument("--observation-id", required=True)
    args = parser.parse_args()
    print(json.dumps(capture(args.race_code, args.root, args.observation_id),
                     ensure_ascii=False, indent=2))

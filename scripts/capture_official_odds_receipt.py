"""Immutable, research-only original official 3T odds HTTP receipt."""
import argparse
import hashlib
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from scripts.inspect_official_odds_receipt import inspect_odds_receipt
from server import parse_official_odds_table

JST = timezone(timedelta(hours=9))
MAX_BYTES = 1_500_000


def capture(race_code, deadline_jst, root, observation_id, *, fetch=None, clock=None):
    if not isinstance(race_code, str) or not re.fullmatch(r"20\d{10}", race_code):
        raise ValueError("invalid race code")
    day, venue, race = race_code[:8], int(race_code[8:10]), int(race_code[10:])
    datetime.strptime(day, "%Y%m%d")
    if venue not in range(1, 25) or race not in range(1, 13):
        raise ValueError("invalid race")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", observation_id):
        raise ValueError("invalid observation ID")
    # Must come from an independently verified official race deadline.
    deadline = datetime.fromisoformat(deadline_jst)
    if deadline.utcoffset() != timedelta(hours=9) or deadline.strftime("%Y%m%d") != day:
        raise ValueError("deadline must be independently supplied as same-date JST")
    url = "https://www.boatrace.jp/owpc/pc/race/odds3t?" + urlencode(
        {"hd": day, "jcd": f"{venue:02d}", "rno": str(race)})
    dest = Path(root) / "observations" / observation_id / day / race_code
    if dest.exists():
        raise FileExistsError("immutable observation already exists")
    now = clock or (lambda: datetime.now(JST))
    started = now()
    report = {"race_code": race_code, "official_url": url,
              "request_started_at_jst": started.isoformat(),
              "deadline_at_jst": deadline.isoformat(),
              "forecast_usable": False, "t12_eligible": False}
    try:
        if fetch:
            raw = fetch(url)
        else:
            request = Request(url, headers={"User-Agent": "Mozilla/5.0", "Accept": "text/html"})
            with urlopen(request, timeout=20) as response:
                if response.status != 200 or response.geturl() != url:
                    raise ValueError("unexpected official response source")
                raw = response.read(MAX_BYTES + 1)
        received = now()
        report["received_at_jst"] = received.isoformat()
        if (started.utcoffset() != timedelta(hours=9)
                or received.utcoffset() != timedelta(hours=9)
                or received < started):
            raise ValueError("invalid JST observation chronology")
        if not isinstance(raw, bytes) or not 0 < len(raw) <= MAX_BYTES:
            raise ValueError("invalid original response bytes")
        odds = parse_official_odds_table(raw.decode("utf-8", "replace"))
        report.update(inspect_odds_receipt(
            odds, race_code=race_code, received_at_jst=received.isoformat(),
            deadline_jst=deadline.isoformat()))
        report.update(status="official_odds_observed_research_only",
                      sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw))
        dest.mkdir(parents=True, exist_ok=False)
        (dest / "original.html").write_bytes(raw)
        (dest / "manifest.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception as exc:
        report.update(status="official_odds_probe_failed", error=type(exc).__name__)
    return report


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("race_code")
    p.add_argument("--deadline-jst", required=True)
    p.add_argument("--observation-id", required=True)
    p.add_argument("--root", default="official_odds_evidence")
    a = p.parse_args()
    result = capture(a.race_code, a.deadline_jst, a.root, a.observation_id)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    if result["status"] != "official_odds_observed_research_only":
        raise SystemExit(1)

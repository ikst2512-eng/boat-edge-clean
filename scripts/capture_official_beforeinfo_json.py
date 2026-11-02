"""Immutable research-only official beforeinfo JSON HTTP observation."""
import argparse
import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from research_model import JST
from scripts.inspect_official_beforeinfo_json import inspect

HOST = "https://www.boatrace.jp"
PATH = "/owsp/sp/spdata"
MAX_BYTES = 1_000_000

def capture(race_code, root, observation_id, fetch=None, clock=None):
    if not isinstance(race_code, str) or not re.fullmatch(r"20[0-9]{10}", race_code):
        raise ValueError("invalid race code")
    day, venue, race = race_code[:8], int(race_code[8:10]), int(race_code[10:])
    datetime.strptime(day, "%Y%m%d")
    if not 1 <= venue <= 24 or not 1 <= race <= 12:
        raise ValueError("invalid race identity")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", observation_id):
        raise ValueError("invalid observation ID")
    url = HOST + PATH + "?" + urlencode(
        {"type": "beforeinfo", "hd": day, "jcd": f"{venue:02d}", "rno": str(race)})
    dest = Path(root) / "observations" / observation_id / day / race_code
    if dest.exists():
        raise FileExistsError("observation must not overwrite prior evidence")
    now = clock or (lambda: datetime.now(JST))
    started = now()
    report = {"race_code": race_code, "url": url,
              "request_started_at_jst": started.isoformat(),
              "t12_eligible": False, "forecast_usable": False}
    try:
        if fetch:
            raw = fetch(url)
        else:
            req = Request(url, headers={"User-Agent": "Mozilla/5.0",
                          "Accept": "application/json, text/javascript, */*; q=0.01",
                          "X-Requested-With": "XMLHttpRequest",
                          "Referer": HOST + "/owsp/sp/race/beforeinfo?" +
                              urlencode({"hd": day, "jcd": f"{venue:02d}", "rno": str(race)})})
            with urlopen(req, timeout=18) as response:
                if response.status != 200 or response.geturl() != url:
                    raise ValueError("unexpected official source response")
                raw = response.read(MAX_BYTES + 1)
        received = now()
        report["received_at_jst"] = received.isoformat()
        if started.utcoffset() is None or received < started:
            raise ValueError("invalid chronology")
        if not isinstance(raw, bytes) or not 0 < len(raw) <= MAX_BYTES:
            raise ValueError("invalid response bytes")
        payload = json.loads(raw)
        verdict = inspect(payload)
        # Valid official race identity must be independently tied to URL input.
        main = payload["maindata"]
        if str(main.get("rno")) != str(race):
            raise ValueError("race number mismatch")
        if str(main.get("jcd")).zfill(2) != f"{venue:02d}" or str(main.get("hd")) != day:
            raise ValueError("race date or venue mismatch")
        report.update(verdict)
        report.update(status="official_json_observed_not_t12_certified",
                      sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw))
        dest.mkdir(parents=True, exist_ok=False)
        (dest / "beforeinfo.json").write_bytes(raw)
        (dest / "manifest.json").write_text(json.dumps(report, ensure_ascii=False, indent=2),
                                             encoding="utf-8")
    except Exception as exc:
        report.update(status="official_json_probe_failed", error=type(exc).__name__)
    return report

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("race_code")
    p.add_argument("--root", default="official_json_probe")
    p.add_argument("--observation-id", required=True)
    args = p.parse_args()
    result = capture(args.race_code, args.root, args.observation_id)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result["status"] != "official_json_observed_not_t12_certified":
        raise SystemExit(1)

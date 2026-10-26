"""Read-only real-source acquisition diagnostic. Never stores payloads or publishes data."""
import argparse
import hashlib
import json
from datetime import datetime, timezone
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from pathlib import Path

SOURCES = {
    "race_csv": "https://boatracecsv.github.io/data/programs/race_cards/{year}/{month}/{day}.csv",
    "preview_stt": "https://boatracecsv.github.io/data/previews/stt/{year}/{month}/{day}.csv",
    "preview_tkz": "https://boatracecsv.github.io/data/previews/tkz/{year}/{month}/{day}.csv",
    "preview_sui": "https://boatracecsv.github.io/data/previews/sui/{year}/{month}/{day}.csv",
    "official_racelist": "https://www.boatrace.jp/owpc/pc/race/racelist?hd={date}&jcd={venue}&rno={race}",
}

def probe(date, venue, race, opener=urlopen):
    datetime.strptime(date, "%Y%m%d")
    if not (venue.isdigit() and 1 <= int(venue) <= 24 and race.isdigit() and 1 <= int(race) <= 12):
        raise ValueError("invalid venue or race")
    vals = dict(date=date, year=date[:4], month=date[4:6], day=date[6:8],
                venue=f"{int(venue):02d}", race=str(int(race)))
    report = {"race_key": f"{date}-{vals['venue']}-{int(race):02d}",
              "observed_at": datetime.now(timezone.utc).isoformat(),
              "status": "UNVERIFIED", "sources": {}}
    for name, template in SOURCES.items():
        url = template.format(**vals)
        entry = {"url": url, "status": "unavailable"}
        try:
            request = Request(url, headers={"User-Agent": "BOAT-EDGE-CLEAN-STAGING/1.0"})
            with opener(request, timeout=12) as response:
                body = response.read(2_000_001)
                entry["http_status"] = response.status
                entry["content_type"] = response.headers.get("Content-Type", "")
                if response.status != 200 or not body or len(body) > 2_000_000:
                    raise ValueError("invalid response or size")
                entry["bytes"] = len(body)
                entry["sha256"] = hashlib.sha256(body).hexdigest()
                entry["status"] = "retrieved_unverified"
        except (HTTPError, URLError, TimeoutError, OSError, ValueError) as exc:
            entry["error_type"] = type(exc).__name__
        report["sources"][name] = entry
    return report

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", required=True)
    parser.add_argument("--venue", required=True)
    parser.add_argument("--race", required=True)
    parser.add_argument("--output", default="source-probe-report.json")
    args = parser.parse_args()
    result = probe(args.date, args.venue, args.race)
    output = Path(args.output)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"race_key": result["race_key"], "statuses": {k:v["status"] for k,v in result["sources"].items()}}, ensure_ascii=False))

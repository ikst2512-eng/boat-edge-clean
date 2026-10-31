"""Read-only official beforeinfo accessibility probe.

Does not parse, save or interpret exhibition/entry data. Fails closed if the
source is inaccessible; never labels pre-race information as verified from a URL alone.
"""
import argparse
import hashlib
import json
from datetime import datetime
from urllib.request import Request, urlopen
from urllib.parse import urlencode
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from research_model import JST

BASE = "https://www.boatrace.jp/owpc/pc/race/beforeinfo"

def probe(day, venue, race, fetch=None):
    date = datetime.strptime(day, "%Y%m%d")
    if date.strftime("%Y%m%d") != day or not 1 <= venue <= 24 or not 1 <= race <= 12:
        raise ValueError("invalid race key")
    url = BASE + "?" + urlencode({"rno": race, "jcd": f"{venue:02d}", "hd": day})
    if fetch is None:
        def fetch(target):
            with urlopen(Request(target, headers={"User-Agent": "BOAT-EDGE-CLEAN-RESEARCH/1.0"}), timeout=10) as response:
                if response.status != 200:
                    raise ValueError("official source unavailable")
                raw = response.read(1_000_001)
                if len(raw) > 1_000_000:
                    raise ValueError("official response too large")
                return raw
    raw = fetch(url)
    if not isinstance(raw, bytes) or not raw:
        raise ValueError("empty or invalid official response")
    return {"race_code": f"{day}{venue:02d}{race:02d}",
            "source_url": url, "received_at_jst": datetime.now(JST).isoformat(),
            "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw),
            "exhibition_verified": False, "entry_verified": False,
            "status": "raw_response_only_not_parsed"}

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", required=True)
    parser.add_argument("--venue", type=int, required=True)
    parser.add_argument("--race", type=int, required=True)
    args = parser.parse_args()
    print(json.dumps(probe(args.date, args.venue, args.race), ensure_ascii=False, indent=2))

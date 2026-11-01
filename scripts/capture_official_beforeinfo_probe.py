"""Experimental official beforeinfo HTTP evidence; never an approved T-12 forecast input."""
import argparse
import hashlib
import json
from datetime import datetime, timedelta
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.parse import urlparse, parse_qs
from research_model import JST

MAX_BYTES=2_000_000
BASE="https://www.boatrace.jp/owsp/sp/race/beforeinfo"

def capture(race_code, root="official_preview_probe", fetch=None, clock=None):
    if not isinstance(race_code,str) or len(race_code)!=12 or not race_code.isascii() or not race_code.isdigit():
        raise ValueError("race code must be 12 ASCII digits")
    day, venue, race = race_code[:8],int(race_code[8:10]),int(race_code[10:])
    datetime.strptime(day,"%Y%m%d")
    if not 1<=venue<=24 or not 1<=race<=12:
        raise ValueError("invalid venue or race")
    now=clock or (lambda: datetime.now(JST))
    url=f"{BASE}?hd={day}&jcd={venue:02d}&rno={race}"
    started=now()
    received=None
    try:
        if fetch is not None:
            raw=fetch(url)
            final_url=url
            status=200
        else:
            with urlopen(Request(url,headers={"User-Agent":"BOAT-EDGE-CLEAN-EVIDENCE/1.0"}),timeout=8) as response:
                final_url=response.geturl()
                status=response.status
                raw=response.read(MAX_BYTES+1)
        received=now()
        if started.utcoffset()!=timedelta(hours=9) or received.utcoffset()!=timedelta(hours=9) or received<started:
            raise ValueError("invalid HTTP observation chronology")
        parsed=urlparse(final_url)
        if (parsed.scheme!="https" or parsed.hostname not in ("www.boatrace.jp","boatrace.jp")
                or parsed.path!="/owsp/sp/race/beforeinfo"
                or parse_qs(parsed.query)!={"hd":[day],"jcd":[f"{venue:02d}"],"rno":[str(race)]}):
            raise ValueError("unexpected official response URL")
        if status!=200 or not isinstance(raw,bytes) or not raw or len(raw)>MAX_BYTES:
            raise ValueError("invalid official HTTP response")
        # A 200 response can still be a JSON/API error or plain text, not HTML evidence.
        prefix=raw.removeprefix(bytes.fromhex("efbbbf")).lstrip(b" \t\r\n").lower()
        if not (prefix.startswith(b"<!doctype html") or prefix.startswith(b"<html")):
            raise ValueError("official response is not an HTML document")
        # Never infer publication time or 6-lane completeness from a valid HTTP response.
        result={"race_code":race_code,"source":"official_beforeinfo_html",
                "url":url,"response_url":final_url,"request_started_at_jst":started.isoformat(),"received_at_jst":received.isoformat(),
                "http_status":status,"bytes":len(raw),"sha256":hashlib.sha256(raw).hexdigest(),
                "status":"raw_http_observed_not_t12_certified",
                "complete_six_lanes":"unverified","deadline_jst":None,
                "t12_eligible":False,"forecast_usable":False}
        root=Path(root)
        dest=root/day/race_code
        if dest.exists():
            raise FileExistsError("append-only official observation already exists")
        dest.mkdir(parents=True,exist_ok=False)
        # Manifest is written last: its presence means the raw bytes were saved.
        html_path=dest/"beforeinfo.html"
        try:
            with html_path.open("xb") as body:
                body.write(raw)
                body.flush()
            with (dest/"manifest.json").open("x",encoding="utf-8") as manifest:
                manifest.write(json.dumps(result,ensure_ascii=False,indent=2)+"\n")
        except Exception:
            (dest/"manifest.json").unlink(missing_ok=True)
            html_path.unlink(missing_ok=True)
            dest.rmdir()
            raise
        return result
    except Exception as exc:
        # A missing/invalid page cannot be treated as evidence of six boats.
        if isinstance(exc,(KeyboardInterrupt,SystemExit)):
            raise
        return {"race_code":race_code,"source":"official_beforeinfo_html","url":url,
                "request_started_at_jst":started.isoformat(),
                "received_at_jst":(received or now()).isoformat(),
                "status":"official_probe_failed","error":type(exc).__name__,
                "complete_six_lanes":"unverified","t12_eligible":False,"forecast_usable":False}

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("race_code")
    parser.add_argument("--root",default="official_preview_probe")
    args=parser.parse_args()
    report=capture(args.race_code,args.root)
    print(json.dumps(report,ensure_ascii=False,indent=2))
    if report["status"]!="raw_http_observed_not_t12_certified":
        raise SystemExit(1)

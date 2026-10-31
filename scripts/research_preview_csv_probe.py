"""Read-only diagnostics of nonofficial realtime preview CSV availability.

These snapshots are typically produced around cutoff-minus-five-minutes;
they MUST NOT be inserted into the existing cutoff-minus-twelve-minute
research snapshots. No prediction or persisted archive writes.
"""
import csv
import io
import json
import hashlib
from datetime import datetime
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from research_model import JST
from scripts.preview_timing_integrity import classify

BASE="https://boatracecsv.github.io/data/previews/"
KINDS=("stt","tkz","sui","original_exhibition","od3")

def inspect(day, fetch=None):
    datetime.strptime(day,"%Y%m%d")
    if len(day)!=8 or not day.isascii() or not day.isdigit():
        raise ValueError("invalid date")
    path=f"{day[:4]}/{day[4:6]}/{day[6:]}.csv"
    records={}
    for kind in KINDS:
        url=BASE+kind+"/"+path
        try:
            if fetch is None:
                with urlopen(Request(url,headers={"User-Agent":"BOAT-EDGE-CLEAN-RESEARCH/1.0"}),timeout=8) as response:
                    raw=response.read(3_000_001)
            else:
                raw=fetch(url)
            if len(raw)>3_000_000:raise ValueError("oversize source")
            rows=list(csv.DictReader(io.StringIO(raw.decode("utf-8-sig"))))
            codes={r.get("レースコード") for r in rows if r.get("レースコード")}
            if any(len(c)!=12 or not c.isascii() or not c.isdigit() or not c.startswith(day) for c in codes):
                raise ValueError("invalid race code")
            received=datetime.now(JST)
            timing={"pre_cutoff_observed":0,"too_late":0,"unknown_time":0}
            for row in rows:
                timing[classify(row, received)]+=1
            records[kind]={"status":"retrieved","rows":len(rows),"race_codes":len(codes),"timing_12min":timing,"timestamp_samples":[{"締切時刻":r.get("締切時刻"),"取得日時":r.get("取得日時")} for r in rows[:2]],
                           "sha256":hashlib.sha256(raw).hexdigest(),"column_names":list(rows[0])[:18] if rows else [],
                           "received_at_jst":received.isoformat()}
        except (HTTPError,URLError,TimeoutError,OSError,ValueError,UnicodeError) as exc:
            records[kind]={"status":"unavailable","error_type":type(exc).__name__}
    return {"date":day,"forecast_12min_cutoff_compatible":False,
            "warning":"Source is typically a 5-min preview; availability alone does not establish pre-12min timing",
            "sources":records}

if __name__=="__main__":
    print(json.dumps(inspect(datetime.now(JST).strftime("%Y%m%d")),ensure_ascii=False,indent=2))

"""One-shot read/capture of predeadline preview CSV; local only, no git push."""
import json
import csv
import io
from datetime import datetime
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from research_model import JST
from late_preview_capture import save_preview, KINDS, six_lane_status
from scripts.preview_timing_integrity import classify

BASE="https://boatracecsv.github.io/data/previews/"
def collect(day=None, root=None, fetch=None, clock=None):
    now=clock or (lambda:datetime.now(JST))
    day=day or now().strftime("%Y%m%d")
    if len(day)!=8 or not day.isascii() or not day.isdigit():
        raise ValueError("invalid date")
    datetime.strptime(day,"%Y%m%d")
    root=Path(root or "late_preview_evidence")
    report={"date":day,"status":"read_only_local_capture","kinds":{}}
    for kind in KINDS:
        url=f"{BASE}{kind}/{day[:4]}/{day[4:6]}/{day[6:]}.csv"
        try:
            if fetch:
                raw=fetch(url)
            else:
                with urlopen(Request(url,headers={"User-Agent":"BOAT-EDGE-CLEAN-RESEARCH/1.0"}),timeout=8) as response:
                    raw=response.read(3_000_001)
            received=now()
            rows=list(csv.DictReader(io.StringIO(raw.decode("utf-8-sig"))))
            gate={"pre_cutoff_observed":0,"too_late":0,"unknown_time":0}
            six_lanes={"complete":0,"incomplete":0,"not_applicable":0}
            for row in rows:
                gate[classify(row,received,margin_minutes=2)]+=1
                six_lanes[six_lane_status(kind,row)]+=1
            written=save_preview(raw,kind,day,received,root)
            report["kinds"][kind]={"received_at_jst":received.isoformat(),"saved":len(written),
                                   "race_codes":written[:5],"source_rows":len(rows),
                                   "pre_deadline_2min":gate,"six_lane_validation":six_lanes}
        except (HTTPError,URLError,TimeoutError,OSError,ValueError,UnicodeError,FileExistsError) as err:
            # A missing upstream daily CSV is different from invalid rows or a transport failure.
            # Never log full response bodies, credentials, or make a failed read look successful.
            reason=("upstream_http" if isinstance(err,HTTPError) else
                    "upstream_transport" if isinstance(err,(URLError,TimeoutError)) else
                    "local_or_invalid_source")
            report["kinds"][kind]={"status":"unavailable","reason":reason,
                                   "http_status":err.code if isinstance(err,HTTPError) else None,
                                   "received_at_jst":now().isoformat(),"saved":0,
                                   "source_rows":None,"pre_deadline_2min":None,
                                   "six_lane_validation":None}
    return report

if __name__=="__main__":
    report=collect()
    output=Path("late_preview_capture_report.json")
    output.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print(output.read_text(encoding="utf-8"))

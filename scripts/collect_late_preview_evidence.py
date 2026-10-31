"""Capture live preview CSV into a separate ephemeral evidence directory.

Never merges into 12-minute research snapshots. A missing or late row is skipped.
"""
import json
from datetime import datetime
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.error import HTTPError,URLError
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from research_model import JST
from late_preview_capture import save_preview,KINDS

BASE="https://boatracecsv.github.io/data/previews/"
def capture(day=None,root="late_preview_evidence",fetch=None,now=None):
    day=day or datetime.now(JST).strftime("%Y%m%d")
    datetime.strptime(day,"%Y%m%d")
    path=f"{day[:4]}/{day[4:6]}/{day[6:]}.csv"
    summary={}
    for kind in KINDS:
        url=BASE+kind+"/"+path
        try:
            if fetch is None:
                with urlopen(Request(url,headers={"User-Agent":"BOAT-EDGE-CLEAN-RESEARCH/1.0"}),timeout=8) as response:
                    raw=response.read(3_000_001)
            else:
                raw=fetch(url)
            receipt=now or datetime.now(JST)
            saved=save_preview(raw,kind,day,receipt,root)
            summary[kind]={"saved":len(saved),"status":"captured" if saved else "no_eligible_predeadline_rows"}
        except (HTTPError,URLError,TimeoutError,OSError,ValueError,UnicodeError) as exc:
            summary[kind]={"saved":0,"status":"unavailable","error_type":type(exc).__name__}
    return {"day":day,"research_snapshots_modified":False,"sources":summary}

if __name__=="__main__":
    print(json.dumps(capture(),ensure_ascii=False,indent=2))

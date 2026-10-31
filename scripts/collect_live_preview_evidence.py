"""Fetch live preview CSV and archive only observations made before race deadline.

Output belongs exclusively to an Actions artifact, not research_snapshots or
published predictions. Safe to run even when no eligible races exist.
"""
import json, sys, tempfile
from datetime import datetime
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError,URLError
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from research_model import JST
from late_preview_capture import save_preview, KINDS
from scripts.research_preview_csv_probe import BASE

def collect(day, root, fetch=None):
    datetime.strptime(day,"%Y%m%d")
    summary={"day":day,"capture_policy":"before_deadline_minus_2min_buffer","kinds":{}}
    for kind in KINDS:
        url=f"{BASE}{kind}/{day[:4]}/{day[4:6]}/{day[6:]}.csv"
        try:
            if fetch is None:
                with urlopen(Request(url,headers={"User-Agent":"BOAT-EDGE-CLEAN-RESEARCH/1.0"}),timeout=8) as response:
                    raw=response.read(3_000_001)
                    received=datetime.now(JST)
            else:
                raw,received=fetch(url)
            records=save_preview(raw,kind,day,received,root)
            summary["kinds"][kind]={"status":"ok","saved":len(records)}
        except (HTTPError,URLError,TimeoutError,OSError,ValueError,UnicodeError,FileExistsError) as error:
            summary["kinds"][kind]={"status":"unavailable_or_invalid","error":type(error).__name__}
    return summary

if __name__=="__main__":
    day=datetime.now(JST).strftime("%Y%m%d")
    print(json.dumps(collect(day,Path("late_preview_evidence")),ensure_ascii=False))

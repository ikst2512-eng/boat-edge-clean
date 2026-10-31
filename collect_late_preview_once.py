"""One-shot read/capture of predeadline preview CSV; local only, no git push."""
import json
from datetime import datetime
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from research_model import JST
from late_preview_capture import save_preview, KINDS

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
            written=save_preview(raw,kind,day,received,root)
            report["kinds"][kind]={"received_at_jst":received.isoformat(),"saved":len(written),
                                   "race_codes":written[:5]}
        except (HTTPError,URLError,TimeoutError,OSError,ValueError,UnicodeError,FileExistsError) as err:
            report["kinds"][kind]={"error":type(err).__name__,"saved":0}
    return report

if __name__=="__main__":
    print(json.dumps(collect(),ensure_ascii=False,indent=2))

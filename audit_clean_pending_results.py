"""Read-only missing result coverage; no prediction mutation or miss verdicts."""
import argparse
import json
from datetime import datetime
from pathlib import Path
from research_model import JST

def audit(root,day,now=None):
    now=now or datetime.now(JST)
    root=Path(root)
    rows={"saved_forecasts":0,"confirmed_result_file_present":0,"before_deadline":0,"awaiting_result_overdue":0,"invalid_archive":0}
    pending=[]
    for path in sorted((root/"four_mode_forecasts").glob(day+"????.json")):
        rows["saved_forecasts"]+=1
        try:
            rec=json.loads(path.read_text(encoding="utf-8"))
            if rec.get("race_code")!=path.stem:raise ValueError("identity")
            deadline=datetime.fromisoformat(rec["deadline_jst"])
            if deadline.utcoffset() is None:raise ValueError("timezone")
        except (ValueError,KeyError,TypeError,OSError):
            rows["invalid_archive"]+=1
            continue
        if (root/"confirmed_results"/(path.stem+".json")).is_file():
            rows["confirmed_result_file_present"]+=1
        elif now<deadline:
            rows["before_deadline"]+=1
        else:
            rows["awaiting_result_overdue"]+=1
            pending.append(path.stem)
    return {"schema":"CLEAN_PENDING_RESULT_COVERAGE_V1","day_jst":day,**rows,
            "overdue_race_codes":pending,"no_result_is_not_a_miss":True,
            "official_results_validated":False,"hit_rate_calculated":False}

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("day")
    a=ap.parse_args()
    print(json.dumps(audit(Path(__file__).resolve().parent,a.day),ensure_ascii=False,sort_keys=True))

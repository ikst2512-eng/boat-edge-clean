"""Read-only daily prospective four-mode evidence audit; does not certify Git first-add."""
import argparse
import json
import re
from datetime import datetime, timedelta
from pathlib import Path

MODES={"hit","balance","hole","narrow"}
KEY=re.compile(r"20\d{10}")

def audit(root,day):
    if not re.fullmatch(r"20\d{6}",day):raise ValueError("invalid_day")
    datetime.strptime(day,"%Y%m%d")
    directory=Path(root)/"four_mode_forecasts"
    records=sorted(directory.glob(day+"*.json")) if directory.exists() else []
    issues=[];valid=0;awaiting=0;completed=0
    for path in records:
        code=path.stem
        try:
            if not KEY.fullmatch(code) or not (1<=int(code[8:10])<=24 and 1<=int(code[10:12])<=12):
                raise ValueError("invalid_filename")
            rec=json.loads(path.read_text(encoding="utf-8"))
            if rec.get("race_code")!=code or rec.get("schema")!="CLEAN_FOUR_MODES_PREDEADLINE_V1":
                raise ValueError("archive_identity")
            t=datetime.fromisoformat(rec["generated_at_jst"])
            deadline=datetime.fromisoformat(rec["deadline_jst"])
            if t.utcoffset() is None or deadline.utcoffset() is None or t>deadline-timedelta(minutes=20):
                raise ValueError("deadline_or_time")
            if t.strftime("%Y%m%d")!=day or deadline.strftime("%Y%m%d")!=day:
                raise ValueError("date_mismatch")
            digests=rec["source_sha256"]
            if not isinstance(digests,dict) or any(not re.fullmatch("[0-9a-f]{64}",str(digests.get(k,""))) for k in ("title","race_cards")):
                raise ValueError("missing_source_digest")
            rates=rec["input_national_win_rates"]
            if not isinstance(rates,list) or len(rates)!=6 or any(type(x) not in (int,float) or not 0<x<20 for x in rates):
                raise ValueError("six_rate_invalid")
            modes=rec["modes"]
            if not isinstance(modes,dict) or set(modes)!=MODES:raise ValueError("missing_mode")
            for mode in modes.values():
                tickets=mode["tickets"]
                if not isinstance(tickets,list) or not tickets:raise ValueError("missing_tickets")
                combos=[row["combo"] for row in tickets]
                if len(combos)!=len(set(combos)):raise ValueError("duplicate_ticket")
                for combo in combos:
                    parts=combo.split("-")
                    if len(parts)!=3 or len(set(parts))!=3 or any(v not in "123456" or len(v)!=1 for v in parts):
                        raise ValueError("invalid_ticket")
            valid+=1
            if (Path(root)/"confirmed_results"/(code+".json")).is_file():
                completed+=1
            else:awaiting+=1
        except (OSError,ValueError,TypeError,KeyError,AttributeError) as exc:
            issues.append({"race_code":code,"issue":str(exc)[:100]})
    return {"schema":"CLEAN_DAILY_FOUR_MODE_EVIDENCE_AUDIT_V1","day_jst":day,
            "archives":len(records),"structurally_valid":valid,"awaiting_result_file":awaiting,
            "result_file_present_unverified":completed,"issues":issues,
            "git_first_add_audited":False,"official_result_verified":False,
            "actual_hit_rate_calculated":False}

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("day")
    args=parser.parse_args()
    result=audit(Path(__file__).resolve().parent,args.day)
    print(json.dumps(result,ensure_ascii=False,sort_keys=True))
    if result["issues"]:raise SystemExit(1)

"""Report missing payout evidence without substituting unverified values."""
import argparse
import json
from pathlib import Path
from evaluate_clean_prospective_cohort import verified_payout

ROOT=Path(__file__).resolve().parent

def coverage(day,root=ROOT):
    if not isinstance(day,str) or len(day)!=8 or not day.isascii() or not day.isdigit() or not day.startswith("20"):
        raise ValueError("invalid day")
    records=sorted((Path(root)/"confirmed_results").glob(day+"????.json"))
    valid=missing=invalid=0
    for p in records:
        if p.is_symlink() or p.stat().st_size>20000:
            invalid+=1
            continue
        try:
            record=json.loads(p.read_text(encoding="utf-8"))
            code=p.stem
            finish=record["finish_order"]
            if record.get("race_code")!=code or record.get("status")!="confirmed" or type(finish) is not list or len(finish)!=3 or any(type(x) is not int or x not in range(1,7) for x in finish) or len(set(finish))!=3:
                raise ValueError("invalid result")
            expected="-".join(map(str,finish))
            proof=verified_payout(code,root)
            if proof is None or proof[0]!=expected:
                missing+=1
            else:
                valid+=1
        except (OSError,ValueError,TypeError,KeyError):
            invalid+=1
    return {"day":day,"schema":"CLEAN_PAYOUT_COVERAGE_AUDIT_V1",
            "confirmed_result_files":len(records),"payout_verified":valid,
            "payout_missing_or_mismatched":missing,"invalid_result_files":invalid,
            "roi_ready":valid>0,"formal":False}

if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("days",nargs="+")
    print(json.dumps([coverage(day) for day in parser.parse_args().days],sort_keys=True))

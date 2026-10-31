"""Validate archived late-preview pairs without editing stored observations.

Each record must have a nonfuture receipt and source timestamp before deadline
with a >=2-minute buffer. Grouping requires both six-boat STT and TKZ rows.
"""
import json
from collections import defaultdict
from pathlib import Path
from datetime import timedelta
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.preview_timing_integrity import classify, parse_jst
from late_preview_capture import six_lane_status

def audit(root="late_preview_evidence"):
    pairs=defaultdict(dict)
    invalid=0
    total=0
    for path in Path(root).rglob("*.json"):
        total+=1
        try:
            row=json.loads(path.read_text(encoding="utf-8"))
            code=row["race_code"]
            kind=row["kind"]
            source=row["source_row"]
            received=parse_jst(row["received_at_jst"])
            if (not code.isdigit() or len(code)!=12 or source["レースコード"]!=code
                or path.stem!=code or path.parent.name!=kind
                or path.parent.parent.name!=code[:8] or received is None
                or classify(source,received,margin_minutes=2)!="pre_cutoff_observed"):
                raise ValueError("invalid source provenance or predeadline time")
            if kind in pairs[code]:
                raise ValueError("duplicate kind")
            # Never trust a stored completeness label without recomputing all six boats.
            row["six_lane_validation"]=six_lane_status(kind,source)
            pairs[code][kind]=row
        except (ValueError,TypeError,KeyError,AttributeError,OSError):
            invalid+=1
    complete=0
    missing=[]
    for code, entries in sorted(pairs.items()):
        if ("stt" in entries and "tkz" in entries
            and entries["stt"].get("six_lane_validation")=="complete"
            and entries["tkz"].get("six_lane_validation")=="complete"):
            complete+=1
        else:
            missing.append(code)
    return {"records":total,"invalid":invalid,"races":len(pairs),
            "paired_complete_6boat_stt_tkz":complete,
            "not_paired_complete":len(missing),
            "note":"No evidence of prediction accuracy or forecast at -12 minutes"}

if __name__=="__main__":
    print(json.dumps(audit(),ensure_ascii=False,indent=2))

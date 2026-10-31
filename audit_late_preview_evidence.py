"""Audit append-only isolated preview evidence: completeness and paired race coverage.

Never trusts row existence alone as a six-lane validation. Read only artifacts
saved by the deadline gate; this is NOT evidence of improved hit rates.
"""
import json
from pathlib import Path
from collections import Counter
from datetime import datetime
from research_model import JST
from late_preview_capture import six_lane_status

def audit(root="late_preview_evidence"):
    base=Path(root)
    by_race={}
    failures=Counter()
    valid_files=0
    for path in sorted(base.rglob("*.json")):
        try:
            obj=json.loads(path.read_text(encoding="utf-8"))
            code=obj["race_code"]
            kind=obj["kind"]
            row=obj["source_row"]
            if (not isinstance(code,str) or len(code)!=12 or not code.isdigit() or
                kind not in ("stt","tkz","sui","od3","original_exhibition") or
                path.stem!=code or path.parent.name!=kind or
                path.parent.parent.name!=code[:8]):
                raise ValueError("provenance mismatch")
            received=datetime.fromisoformat(obj["received_at_jst"])
            if received.tzinfo is None or received.astimezone(JST).strftime("%Y%m%d")!=code[:8]:
                raise ValueError("receipt timestamp invalid")
            if obj.get("cutoff_policy")!="before_deadline_minus_2min_buffer":
                raise ValueError("policy mismatch")
            if obj.get("status")!="late_preview_unvalidated_not_research_forecast":
                raise ValueError("status mismatch")
            if row.get("レースコード")!=code:
                raise ValueError("row mismatch")
            # Current source-row completeness is recomputed from raw fields.
            complete=six_lane_status(kind,row)
            by_race.setdefault(code,{})[kind]=complete
            valid_files+=1
        except (OSError,ValueError,KeyError,TypeError,AttributeError):
            failures["invalid_artifact"]+=1
    matched=[(code,kinds) for code,kinds in by_race.items() if kinds.get("stt")=="complete" and kinds.get("tkz")=="complete"]
    return {"valid_files":valid_files,"invalid_files":failures["invalid_artifact"],
            "races":len(by_race),
            "stt_complete":sum(v.get("stt")=="complete" for v in by_race.values()),
            "tkz_complete":sum(v.get("tkz")=="complete" for v in by_race.values()),
            "paired_stt_tkz_six_lanes":len(matched),
            "paired_race_codes":sorted(code for code,_ in matched),
            "research_12min_forecasts_modified":False}
if __name__=="__main__":
    print(json.dumps(audit(),ensure_ascii=False,indent=2))

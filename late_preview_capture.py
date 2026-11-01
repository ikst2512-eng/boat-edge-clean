"""Isolated, append-only preview evidence. Never part of 12-minute research forecasts."""
import csv, hashlib, io, json, os
from datetime import datetime, timedelta
from pathlib import Path
from research_model import JST
from scripts.preview_timing_integrity import classify, parse_jst

KINDS=("stt","tkz","sui","original_exhibition","od3")
def six_lane_status(kind, row):
    """Classify source completeness without claiming a research prediction."""
    if kind not in ("tkz", "stt"):
        return "not_applicable"
    if kind == "tkz":
        try:
            times=[float(row[f"艇{i}_展示タイム"]) for i in range(1,7)]
            tilts=[float(row[f"艇{i}_チルト"]) for i in range(1,7)]
        except (KeyError, ValueError, TypeError):
            return "incomplete"
        return "complete" if all(5 <= v <= 9 for v in times) and all(-1 <= v <= 3 for v in tilts) else "incomplete"
    try:
        courses=[int(row[f"艇{i}_コース"]) for i in range(1,7)]
        starts=[str(row[f"艇{i}_スタート展示"]).strip() for i in range(1,7)]
    except (KeyError, ValueError, TypeError):
        return "incomplete"
    import re
    valid_st=re.compile(r"(?:[+-]?(?:\d+(?:\.\d+)?|\.\d+)|F\.?\d{1,2})")
    # Numeric syntax alone is not six-lane evidence: reject implausible ST.
    import math
    def plausible_st(st):
        if not valid_st.fullmatch(st):
            return False
        if st.startswith("F"):
            return 0 <= float(st[1:]) <= 0.99
        value=float(st)
        return math.isfinite(value) and -1 <= value <= 1
    return "complete" if sorted(courses)==[1,2,3,4,5,6] and all(plausible_st(st) for st in starts) else "incomplete"

def save_preview(raw, kind, day, received_at, root):
    if kind not in KINDS or len(day)!=8 or not day.isascii() or not day.isdigit():
        raise ValueError("invalid dataset key")
    if received_at.tzinfo is None: raise ValueError("naive receipt")
    if len(raw)>3_000_000 or not raw:raise ValueError("invalid source size")
    reader=csv.DictReader(io.StringIO(raw.decode("utf-8-sig")))
    # Duplicate source headers are ambiguous: DictReader silently overwrites
    # columns, so never treat them as trustworthy six-boat evidence.
    headers=reader.fieldnames
    if not headers or any(not name for name in headers) or len(headers)!=len(set(headers)):
        raise ValueError("missing or duplicate preview CSV headers")
    rows=list(reader)
    selected=[]
    seen=set()
    for row in rows:
        code=row.get("レースコード","")
        if not isinstance(code,str) or len(code)!=12 or not code.isascii() or not code.isdigit() or not code.startswith(day):
            continue
        if code in seen:raise ValueError("duplicate race")
        seen.add(code)
        # Strictly before the deadline, but separate from research minus-12-minute cutoffs.
        if classify(row,received_at,margin_minutes=2)!="pre_cutoff_observed":continue
        deadline=parse_jst(row["締切時刻"])
        if deadline is None:
            deadline=datetime.strptime(day+row["締切時刻"],"%Y%m%d%H:%M").replace(tzinfo=JST)
        # Receipt must leave a minimum two-minute operational buffer.
        if received_at>=deadline-timedelta(minutes=2):continue
        selected.append((code,row))
    # Preflight all destinations before writing any evidence. A collision must not
    # leave an apparently successful subset of the same capture batch on disk.
    destinations=[Path(root)/day/kind/(code+".json") for code,_ in selected]
    for target in destinations:
        if target.exists():
            raise FileExistsError(f"append-only evidence already exists: {target}")
    output=[]
    for (code,row),target in zip(selected,destinations):
        target.parent.mkdir(parents=True,exist_ok=True)
        record={"race_code":code,"kind":kind,"received_at_jst":received_at.isoformat(),
                "source_observed_jst":row["取得日時"],"cutoff_policy":"before_deadline_minus_2min_buffer",
                "source_csv_sha256":hashlib.sha256(raw).hexdigest(),"source_row":row,
                "six_lane_validation":six_lane_status(kind,row),
                "status":"late_preview_unvalidated_not_research_forecast"}
        data=json.dumps(record,ensure_ascii=False,sort_keys=True)
        with target.open("x",encoding="utf-8") as file:
            file.write(data)
            file.flush()
            os.fsync(file.fileno())
        output.append(code)
    return output

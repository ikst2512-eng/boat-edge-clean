"""Third-party BoatraceCSV payouts ingestion for EXPLORATORY paired comparisons.
Officially verified flags MUST remain false until separately authenticated.
"""
import csv
import io
import re
from collections import Counter

def parse_payouts_csv(text):
    reader=csv.DictReader(io.StringIO(text.lstrip("\ufeff")))
    required={"レースコード","3連単_組番"}
    if not required.issubset(reader.fieldnames or []):
        raise ValueError("missing_required_payout_columns")
    rows=[]
    seen=set()
    problems=Counter()
    for item in reader:
        key=(item.get("レースコード") or "").strip()
        ticket=(item.get("3連単_組番") or "").strip().translate(str.maketrans("１２３４５６－","123456-"))
        if not re.fullmatch(r"20[0-9]{6}(?:0[1-9]|1[0-9]|2[0-4])(?:0[1-9]|1[0-2])",key):
            problems["invalid_race_code"]+=1
            continue
        if key in seen:
            problems["duplicate_race_code"]+=1
            rows=[r for r in rows if r["race_code"]!=key]
            continue
        seen.add(key)
        parts=ticket.split("-")
        if len(parts)!=3 or len(set(parts))!=3 or any(x not in "123456" for x in parts):
            problems["missing_or_invalid_ticket"]+=1
            continue
        rows.append({"race_code":key,"ticket":ticket,
                    "status":"third_party_snapshot","source_kind":"third_party",
                    "verification_status":"UNVERIFIED_THIRD_PARTY"})
    return {"results":rows,"excluded":dict(problems),"matched_payout_rows":len(rows)}

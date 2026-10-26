"""Isolated prospective 120-way research capture; never imports results or Formal Fresh."""
import argparse
import hashlib
import json
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from research_model import probabilities

JST = timezone(timedelta(hours=9))
SHA40 = re.compile(r"[0-9a-f]{40}\Z")
SHA64 = re.compile(r"[0-9a-f]{64}\Z")

def freeze(destination, *, race_code, rates, model_sha, input_sha256,
           source_received_at, cutoff_jst, title_bytes, cards_bytes):
    """Create new forecast bytes only while both source and clock precede cutoff."""
    if not isinstance(race_code, str) or not re.fullmatch(r"20[0-9]{10}", race_code):
        raise ValueError("invalid race code")
    if not (1 <= int(race_code[8:10]) <= 24 and 1 <= int(race_code[10:12]) <= 12):
        raise ValueError("race venue or number out of range")
    try:
        datetime.strptime(race_code[:8], "%Y%m%d")
    except ValueError as exc:
        raise ValueError("invalid race calendar date") from exc
    if not isinstance(model_sha, str) or not SHA40.fullmatch(model_sha):
        raise ValueError("invalid model SHA")
    if not isinstance(input_sha256, str) or not SHA64.fullmatch(input_sha256):
        raise ValueError("invalid input digest")
    if any(not isinstance(raw, bytes) or not raw for raw in (title_bytes, cards_bytes)):
        raise ValueError("both raw title and race_cards CSV bytes required")
    title_sha256 = hashlib.sha256(title_bytes).hexdigest()
    cards_sha256 = hashlib.sha256(cards_bytes).hexdigest()
    composite = hashlib.sha256((title_sha256 + ":" + cards_sha256).encode("ascii")).hexdigest()
    if composite != input_sha256:
        raise ValueError("source CSV bytes do not match declared composite input SHA256")
    cutoff = datetime.fromisoformat(cutoff_jst)
    received = datetime.fromisoformat(source_received_at)
    if any(t.tzinfo is None or t.utcoffset() is None for t in (cutoff,received)):
        raise ValueError("timezone required")
    if cutoff.astimezone(JST).strftime("%Y%m%d") != race_code[:8]:
        raise ValueError("cutoff race date mismatch")
    now = datetime.now(JST)
    if received > now or now >= cutoff or received >= cutoff:
        raise ValueError("source or current time is not before cutoff")
    ordered = probabilities(rates)
    p = {"-".join(map(str,t)):value for t,value in ordered}
    if len(p) != 120 or abs(sum(p.values())-1) > 1e-8:
        raise ValueError("invalid 120-way output")
    record = {
        "race_code":race_code, "status":"research", "validated":False,
        "model_id":"national-beta0.4-exploratory-v1",
        "model_sha":model_sha, "input_sha256":input_sha256,
        "input_hash_scope":"source_csv_byte_hashes_ordered_title_cards",
        "source_title_sha256":title_sha256,"source_cards_sha256":cards_sha256,
        "source_received_at":received.isoformat(),
        "generated_at":now.isoformat(), "cutoff_jst":cutoff.isoformat(),
        "predictions":list(p)[:10], "probabilities":p,
        "receipt_status":"LOCAL_EXCLUSIVE_CREATE_NOT_INDEPENDENTLY_VERIFIED",
    }
    data=(json.dumps(record,ensure_ascii=False,sort_keys=True,allow_nan=False)+"\n").encode("utf-8")
    dest=Path(destination)
    with dest.open("xb") as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    return {"status":record["receipt_status"],"sha256":hashlib.sha256(data).hexdigest(),
            "race_code":race_code,"tickets":120,"path":str(dest)}

def main():
    p=argparse.ArgumentParser(description="Research-only fresh 120-way snapshot")
    p.add_argument("destination",type=Path)
    p.add_argument("--race-code",required=True)
    p.add_argument("--rates-json",required=True,help="six pre-cutoff national win rates")
    p.add_argument("--model-sha",required=True)
    p.add_argument("--input-sha256",required=True)
    p.add_argument("--title-csv",required=True,type=Path,help="raw title CSV bytes")
    p.add_argument("--cards-csv",required=True,type=Path,help="raw race_cards CSV bytes")
    p.add_argument("--source-received-at",required=True)
    p.add_argument("--cutoff-jst",required=True)
    a=p.parse_args()
    result=freeze(a.destination,race_code=a.race_code,rates=json.loads(a.rates_json),
                  model_sha=a.model_sha,input_sha256=a.input_sha256,
                  source_received_at=a.source_received_at,cutoff_jst=a.cutoff_jst,
                  title_bytes=a.title_csv.read_bytes(),cards_bytes=a.cards_csv.read_bytes())
    print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=="__main__":
    main()

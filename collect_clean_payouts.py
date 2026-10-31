"""Independently collect trifecta payouts, cross-checked to immutable confirmed finishes."""
import csv
import hashlib
import io
import json
import os
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError

ROOT=Path(__file__).resolve().parent
JST=timezone(timedelta(hours=9))
CODE=re.compile(r"20[0-9]{6}(?:0[1-9]|1[0-9]|2[0-4])(?:0[1-9]|1[0-2])")

def parse(day, raw, root=ROOT):
    if len(day)!=8 or not day.isascii() or not day.isdigit():
        raise ValueError("invalid day")
    datetime.strptime(day,"%Y%m%d")
    if len(raw)>2_000_000:raise ValueError("oversized payout CSV")
    reader=csv.DictReader(io.StringIO(raw.decode("utf-8-sig")))
    cols={"レースコード","3連単_組番","3連単_払戻金"}
    if not reader.fieldnames or not cols.issubset(reader.fieldnames):
        raise ValueError("unexpected payout columns")
    digest=hashlib.sha256(raw).hexdigest()
    seen=set()
    records={}
    for row in reader:
        code=row["レースコード"]
        if not isinstance(code,str) or not CODE.fullmatch(code) or not code.startswith(day):
            continue
        if code in seen:raise ValueError("duplicate payout race")
        seen.add(code)
        combo=row["3連単_組番"].strip()
        money=row["3連単_払戻金"].strip().replace(",","").replace("円","")
        if not re.fullmatch(r"[1-6]-[1-6]-[1-6]",combo) or len(set(combo.split("-")))!=3:
            continue
        if not money.isascii() or not money.isdecimal() or not 100<=int(money)<=100_000_000:
            continue
        result=Path(root)/"confirmed_results"/(code+".json")
        if result.is_symlink() or not result.is_file() or result.stat().st_size>20000:
            continue
        saved=json.loads(result.read_text(encoding="utf-8"))
        finish=saved.get("finish_order")
        if saved.get("race_code")!=code or saved.get("status")!="confirmed" or type(finish) is not list or len(finish)!=3 or any(type(v) is not int or v not in range(1,7) for v in finish) or len(set(finish))!=3:
            continue
        if combo!="-".join(map(str,finish)):
            continue
        records[code]={"schema":"CLEAN_TRIFECTA_PAYOUT_EVIDENCE_V1","race_code":code,
            "winning_ticket":combo,"payout_yen_per_100":int(money),
            "source_url":f"https://boatracecsv.github.io/data/results/payouts/{day[:4]}/{day[4:6]}/{day[6:]}.csv",
            "source_sha256":digest,"confirmed_result_source_sha256":saved.get("source_sha256"),
            "verified_against_confirmed_finish":True,"formal":False}
    return records

def collect(day=None,root=ROOT):
    day=day or datetime.now(JST).strftime("%Y%m%d")
    datetime.strptime(day,"%Y%m%d")
    url=f"https://boatracecsv.github.io/data/results/payouts/{day[:4]}/{day[4:6]}/{day[6:]}.csv"
    try:
        with urlopen(Request(url,headers={"User-Agent":"BOAT-EDGE-CLEAN-PAYOUTS/1.0"}),timeout=15) as response:
            raw=response.read(2_000_001)
    except HTTPError as error:
        if error.code==404:return {"day":day,"status":"source_pending","saved":0}
        raise
    records=parse(day,raw,root)
    directory=Path(root)/"payout_evidence"
    saved=0
    for code,item in sorted(records.items()):
        directory.mkdir(exist_ok=True)
        path=directory/(code+".json")
        if path.is_symlink():raise ValueError("symlink payout")
        try:
            with path.open("x",encoding="utf-8") as f:
                json.dump(item,f,sort_keys=True,ensure_ascii=False)
                f.flush();os.fsync(f.fileno())
            saved+=1
        except FileExistsError:
            old=json.loads(path.read_text(encoding="utf-8"))
            if old.get("race_code")!=code or old.get("winning_ticket")!=item["winning_ticket"] or old.get("payout_yen_per_100")!=item["payout_yen_per_100"]:
                raise ValueError("payout conflict requires review")
    return {"day":day,"status":"checked","matched":len(records),"saved":saved}

if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser();p.add_argument("--date")
    print(json.dumps(collect(p.parse_args().date),sort_keys=True))

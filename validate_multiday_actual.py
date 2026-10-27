"""Actual historical research evaluation on published independent race results.

No forecasts are regenerated or edited. No historical predictions are promoted
to prospective/formal. Source result CSV is post-result public information.
"""
import csv, hashlib, io, json, urllib.request
from pathlib import Path
from datetime import datetime
from research_model import probabilities

ROOT=Path(__file__).resolve().parent
BASE="https://boatracecsv.github.io/data/results/realtime/"

def evaluate(days=("20261023","20261024","20261025","20261026","20261027")):
    report=[]
    for day in days:
        url=BASE+day[:4]+"/"+day[4:6]+"/"+day[6:]+".csv"
        with urllib.request.urlopen(urllib.request.Request(url,headers={"User-Agent":"CLEAN-RESEARCH-VALIDATION/1.0"}),timeout=25) as response:
            raw=response.read(3_000_001)
        if len(raw)>3_000_000:raise ValueError("oversized source")
        rows=list(csv.DictReader(io.StringIO(raw.decode("utf-8-sig"))))
        result={}
        for row in rows:
            code=row.get("レースコード","")
            if not (len(code)==12 and code.isascii() and code.isdigit() and code.startswith(day)):continue
            if code in result:raise ValueError("duplicate result "+code)
            winning=[row.get(f"{i}着_艇番","") for i in (1,2,3)]
            if len(set(winning))==3 and all(n in "123456" and len(n)==1 for n in winning):
                result[code]="-".join(winning)
        candidates=list(sorted((ROOT/"research_snapshots").glob(day+"*.json")))
        successes={3:0,5:0,10:0}
        eligible=0
        for path in candidates:
            if path.stem not in result:continue
            p=json.loads(path.read_text(encoding="utf-8"))
            if p.get("race_code")!=path.stem or p.get("status")!="research" or p.get("validated") is not False:raise ValueError("invalid research record")
            if datetime.fromisoformat(p["generated_at"])>=datetime.fromisoformat(p["cutoff_jst"]):raise ValueError("late prediction "+path.stem)
            actual=["-".join(map(str,t)) for t,_ in probabilities(p["national_win_rates"],beta=0.4)[:10]]
            if actual!=p["predictions"]:raise ValueError("cannot reproduce "+path.stem)
            eligible+=1
            for k in successes:successes[k]+=result[path.stem] in actual[:k]
        report.append({"day":day,"saved_research":len(candidates),"matched":eligible,"published_results":len(result),
                      "result_source_sha256":hashlib.sha256(raw).hexdigest(),
                      "top3":successes[3],"top5":successes[5],"top10":successes[10]})
    n=sum(x["matched"] for x in report)
    if n==0:raise ValueError("no actual matched races")
    totals={k:sum(x[k] for x in report) for k in ("top3","top5","top10")}
    return {"scope":"HISTORICAL_RESEARCH_ONLY_NOT_FORMAL","days":report,"matched_total":n,
            "hits":totals,"rates":{k:round(v/n*100,2) for k,v in totals.items()},
            "notes":"Actual archived research snapshots only, versus later-published independent results. No proof of remote pre-cutoff receipt."}

if __name__=="__main__":
    data=evaluate()
    print(json.dumps(data,ensure_ascii=False))
    Path("multiday_actual_validation.json").write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding="utf-8")

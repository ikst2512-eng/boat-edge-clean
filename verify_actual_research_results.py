"""Actual historical research-only vs independently collected CLEAN results.

Pure offline replay against committed inputs. Not formal-forecast performance.
"""
import json, subprocess
from datetime import datetime
from pathlib import Path
from research_model import probabilities
ROOT=Path(__file__).resolve().parent

def verify(day="20261027"):
    rows=[]
    for fp in sorted((ROOT/"research_snapshots").glob(day+"*.json")):
        rp=ROOT/"confirmed_results"/fp.name
        if not rp.exists():continue
        f=json.loads(fp.read_text(encoding="utf-8"));r=json.loads(rp.read_text(encoding="utf-8"))
        code=fp.stem
        if f.get("race_code")!=code or r.get("race_code")!=code or f.get("status")!="research" or f.get("validated") is not False or r.get("status")!="confirmed":
            raise ValueError("record identity/status mismatch "+code)
        replay=["-".join(map(str,t)) for t,_ in probabilities(f["national_win_rates"])[:10]]
        if f["predictions"]!=replay:raise ValueError("model replay mismatch "+code)
        generated=datetime.fromisoformat(f["generated_at"]);cutoff=datetime.fromisoformat(f["cutoff_jst"])
        if generated>=cutoff:raise ValueError("late research prediction "+code)
        win="-".join(map(str,r["finish_order"]))
        if len(set(r["finish_order"]))!=3:raise ValueError("invalid result "+code)
        history=subprocess.check_output(["git","log","--diff-filter=A","--format=%cI","--",str(fp.relative_to(ROOT))],cwd=ROOT,text=True).strip().splitlines()
        first=datetime.fromisoformat(history[-1]) if len(history)==1 else None
        first_before=bool(first and first<cutoff)
        idx=replay.index(win)+1 if win in replay else None
        rows.append({"code":code,"rank":idx,"pre_cutoff_generated":True,"first_git_commit_pre_cutoff":first_before,
                     "source":"CLEAN research archive vs CLEAN confirmed results"})
    n=len(rows)
    if n==0:raise ValueError("no actual paired results")
    report={"day":day,"scope":"RESEARCH_ONLY_NOT_FORMAL",
            "matched_races":n,"first_git_commit_before_cutoff":sum(r["first_git_commit_pre_cutoff"] for r in rows),
            "top3_hits":sum(bool(r["rank"] and r["rank"]<=3) for r in rows),
            "top5_hits":sum(bool(r["rank"] and r["rank"]<=5) for r in rows),
            "top10_hits":sum(bool(r["rank"] and r["rank"]<=10) for r in rows),
            "results":rows,"caveat":"Git committer timestamp does not prove remote first receipt; research model is exploratory and not formal."}
    for top in (3,5,10):report["top"+str(top)+"_rate"]=round(report["top"+str(top)+"_hits"]/n,6)
    return report

if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser();p.add_argument("--day",default="20261027")
    rep=verify(p.parse_args().day)
    print(json.dumps({k:v for k,v in rep.items() if k!="results"},ensure_ascii=False))
    Path("research_validation_report.json").write_text(json.dumps(rep,ensure_ascii=False,indent=2),encoding="utf-8")

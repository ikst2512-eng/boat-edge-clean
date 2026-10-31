"""Read-only pre-race feature audit; uses only immutable saved rates and confirmed results.

No exhibition, entry-course, wall or odds fields exist in these saved records:
do not invent or backfill them. Discovery / holdout are separated by race date.
"""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
ROOT=Path(__file__).resolve().parents[1]

def analyze(root=ROOT):
    output={}
    for cohort in ("discovery", "holdout"):
        output[cohort]={k:{"n":0,"top10":0} for k in ("all","lane1_strongest","lane1_not_strongest","lane1_lead_2plus","lane1_lead_under2")}
    rejected=0
    for path in sorted((root/"research_snapshots").glob("*.json")):
        result_path=root/"confirmed_results"/path.name
        if not result_path.is_file():continue
        try:
            p=json.loads(path.read_text())
            q=json.loads(result_path.read_text())
            code=path.stem
            if p.get("race_code")!=code or q.get("race_code")!=code or p.get("status")!="research" or q.get("status")!="confirmed":raise ValueError("invalid provenance")
            if p["generated_at"]>=p["cutoff_jst"]:raise ValueError("late forecast")
            rates=p["national_win_rates"]
            if len(rates)!=6 or any(not isinstance(x,(int,float)) or isinstance(x,bool) or not 0<x<20 for x in rates):raise ValueError("invalid rates")
            tickets=p["predictions"]
            if len(tickets)!=10:raise ValueError("invalid ticket count")
            winning="-".join(map(str,q["finish_order"][:3]))
            hit=int(winning in tickets)
            cohort="discovery" if code[:8]<="20261029" else "holdout"
            keys=("all","lane1_strongest" if rates[0]>=max(rates) else "lane1_not_strongest","lane1_lead_2plus" if rates[0]-max(rates[1:])>=2 else "lane1_lead_under2")
            for key in keys:
                output[cohort][key]["n"]+=1
                output[cohort][key]["top10"]+=hit
        except (ValueError,TypeError,KeyError,IndexError,OSError):
            rejected+=1
    for cohorts in output.values():
        for row in cohorts.values():
            row["hit_rate_pct"]=round(row["top10"]*100/row["n"],2) if row["n"] else None
    return {"scope":"national_win_rate_only_no_entry_or_exhibition_data","rejected":rejected,"cohorts":output}

if __name__=="__main__":
    print(json.dumps(analyze(),ensure_ascii=False,indent=2))

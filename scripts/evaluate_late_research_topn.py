"""Evaluate actual result against immutable early and prospective late picks on same races.

No betting advice. Results are descriptive and only eligible races are counted.
"""
import json
from datetime import datetime, timedelta
from pathlib import Path
from research_model import JST


def ticket_hits(predictions, finish):
    if not isinstance(predictions,list) or len(predictions)<10 or len(set(predictions[:10]))!=10:
        raise ValueError("invalid top ten")
    outcome="-".join(map(str,finish))
    return {str(n):int(outcome in predictions[:n]) for n in (3,5,10)}


def evaluate(day, late_root, repo_root):
    root=Path(repo_root)
    counts={str(n):{"early_hits":0,"late_hits":0} for n in (3,5,10)}
    rows=[]
    for file in sorted((Path(late_root)/day).glob("*.json")):
        code=file.stem
        if len(code)!=12 or not code.isascii() or not code.isdigit() or not code.startswith(day):
            continue
        early_file=root/"research_snapshots"/(code+".json")
        result_file=root/"confirmed_results"/(code+".json")
        if not early_file.is_file() or not result_file.is_file():
            continue
        try:
            late=json.loads(file.read_text(encoding="utf-8"))
            early=json.loads(early_file.read_text(encoding="utf-8"))
            result=json.loads(result_file.read_text(encoding="utf-8"))
            generated=datetime.fromisoformat(late["generated_at_jst"])
            received=datetime.fromisoformat(late["generated_from_received_at_jst"])
            deadline=datetime.fromisoformat(late["race_deadline_jst"])
            early_generated=datetime.fromisoformat(early["generated_at"])
            cutoff=datetime.fromisoformat(early["cutoff_jst"])
            if any(t.utcoffset() is None for t in (generated,received,deadline,early_generated,cutoff)):
                continue
            if not (received<=generated<deadline-timedelta(minutes=2)
                    and early_generated<cutoff<deadline):
                continue
            if (late.get("race_code")!=code or early.get("race_code")!=code
                    or result.get("race_code")!=code
                    or late.get("research_only") is not True
                    or late.get("status")!="research_candidate_unvalidated"
                    or early.get("status")!="research"
                    or result.get("status")!="confirmed"):
                continue
            finish=result["finish_order"][:3]
            if (len(finish)!=3 or any(type(x)!=int or x not in range(1,7) for x in finish)
                    or len(set(finish))!=3):
                continue
            early_hits=ticket_hits(early["predictions"],finish)
            late_hits=ticket_hits(late["predictions"],finish)
            for n in (3,5,10):
                counts[str(n)]["early_hits"]+=early_hits[str(n)]
                counts[str(n)]["late_hits"]+=late_hits[str(n)]
            rows.append({"race_code":code,"finish":"-".join(map(str,finish)),
                         "early_hits":early_hits,"late_hits":late_hits})
        except (ValueError,KeyError,TypeError,AttributeError,OSError,IndexError):
            continue
    paired=len(rows)
    for n in (3,5,10):
        entry=counts[str(n)]
        entry["paired_races"]=paired
        entry["early_hit_rate_pct"]=round(100*entry["early_hits"]/paired,2) if paired else None
        entry["late_hit_rate_pct"]=round(100*entry["late_hits"]/paired,2) if paired else None
        entry["difference_points"]=round(100*(entry["late_hits"]-entry["early_hits"])/paired,2) if paired else None
    return {"date":day,"paired_races":paired,"topn":counts,"rows":rows,
            "note":"unvalidated mechanical late baseline; comparison only, no proven lift"}


if __name__=="__main__":
    import argparse
    parser=argparse.ArgumentParser(description="Read-only prospective paired TopN audit")
    parser.add_argument("--day",default=datetime.now(JST).strftime("%Y%m%d"),
                        help="Race date YYYYMMDD; archived evidence must already exist")
    parser.add_argument("--late-root",default="late_research_candidates",
                        help="Local directory containing archived prospective candidates")
    args=parser.parse_args()
    parsed=datetime.strptime(args.day,"%Y%m%d")
    if parsed.strftime("%Y%m%d")!=args.day or parsed.date()>datetime.now(JST).date():
        parser.error("invalid or future race day")
    print(json.dumps(evaluate(args.day,Path(args.late_root),Path(".")),ensure_ascii=False))

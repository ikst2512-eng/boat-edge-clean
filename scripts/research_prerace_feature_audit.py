"""Read-only pre-race feature audit; uses only immutable saved rates and confirmed results.

No exhibition, entry-course, wall or odds fields exist in these saved records:
do not invent or backfill them. Discovery / holdout are separated by race date.
"""
import json, sys
from datetime import datetime, timedelta
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from research_model import probabilities
ROOT=Path(__file__).resolve().parents[1]


def outside_second_candidate(rates):
    """Research-only post-hoc hypothesis, never an evidence-backed model change."""
    ranked = probabilities(rates)
    return ["-".join(map(str, t)) for t, _ in sorted(
        ranked, key=lambda item: (-item[1] * (1.25 if item[0][0] == 1 and item[0][1] >= 4 else 1.0), -item[1])
    )[:10]]


def analyze(root=ROOT):
    output={}
    for cohort in ("discovery", "holdout"):
        output[cohort]={k:{"n":0,"top3":0,"top5":0,"top10":0,"head1_actual":0,"head1_top10_hit":0,"head1_top10_miss":0} for k in ("all","lane1_strongest","lane1_unique_strongest","lane1_tied_strongest","lane1_not_strongest","lane1_lead_2plus","lane1_lead_under2")}
    rejected=0
    advanced_fields=("motor","exhibition","entry","st","wind","course")
    feature_presence={cohort:{"records":0,"direct_fields":{key:0 for key in advanced_fields}} for cohort in ("discovery","holdout")}
    comparison={k:{"n":0,"baseline_hits":0,"candidate_hits":0,"gained":0,"lost":0,"unchanged_hits":0,"actual_second_counts":{str(i):0 for i in range(2,7)},"baseline_second_counts":{str(i):0 for i in range(2,7)},"candidate_second_counts":{str(i):0 for i in range(2,7)}} for k in ("discovery","holdout")}
    strongest_head1_misses={"discovery":[],"holdout":[]}
    for path in sorted((root/"research_snapshots").glob("*.json")):
        result_path=root/"confirmed_results"/path.name
        if not result_path.is_file():continue
        try:
            p=json.loads(path.read_text())
            q=json.loads(result_path.read_text())
            code=path.stem
            if p.get("race_code")!=code or q.get("race_code")!=code or p.get("status")!="research" or p.get("validated") is not False or q.get("status")!="confirmed":raise ValueError("invalid provenance")
            if p.get("model_version") not in (None, "national-beta0.4-exploratory-v1"):
                raise ValueError("unmatched research model version")
            generated=datetime.fromisoformat(p["generated_at"])
            cutoff=datetime.fromisoformat(p["cutoff_jst"])
            deadline=datetime.fromisoformat(p["source_deadline_jst"])
            received = [datetime.fromisoformat(p[k]) for k in ("source_title_received_jst", "source_cards_received_jst")]
            confirmed = datetime.fromisoformat(q["confirmed_at_jst"])
            if (any(x.utcoffset() != timedelta(hours=9) for x in (generated, cutoff, deadline, *received, confirmed))
                    or deadline-cutoff != timedelta(minutes=12)
                    or max(generated, *received) >= cutoff or max(received) > generated
                    or deadline.strftime("%Y%m%d") != code[:8]
                    or confirmed <= deadline):
                raise ValueError("unverified predeadline forecast")
            finish=q["finish_order"]
            if (not isinstance(finish,list) or len(finish)<3
                    or any(type(n) is not int or n not in range(1,7) for n in finish[:3])
                    or len(set(finish[:3]))!=3):
                raise ValueError("invalid finish")
            rates=p["national_win_rates"]
            if not isinstance(rates,list) or len(rates)!=6 or any(type(x) not in (int,float) or not 0<x<20 for x in rates):raise ValueError("invalid rates")
            tickets=p["predictions"]
            if (not isinstance(tickets,list) or len(tickets)!=10 or len(set(tickets))!=10
                    or any(not isinstance(t,str) or len(t.split("-"))!=3
                           or len(set(t.split("-")))!=3
                           or any(v not in {"1","2","3","4","5","6"} for v in t.split("-"))
                           for t in tickets)):
                raise ValueError("invalid tickets")
            winning="-".join(map(str,q["finish_order"][:3]))
            rank=tickets.index(winning)+1 if winning in tickets else None
            hit=int(rank is not None)
            actual_head1=finish[0]==1
            cohort="discovery" if code[:8]<="20261029" else "holdout"
            feature_presence[cohort]["records"]+=1
            for field in advanced_fields:
                feature_presence[cohort]["direct_fields"][field]+=int(field in p and p[field] is not None)
            keys=("all","lane1_strongest" if rates[0]>=max(rates) else "lane1_not_strongest","lane1_lead_2plus" if rates[0]-max(rates[1:])>=2 else "lane1_lead_under2")
            if rates[0] > max(rates[1:]):
                keys += ("lane1_unique_strongest",)
            elif rates[0] == max(rates):
                keys += ("lane1_tied_strongest",)
            if "lane1_strongest" in keys:
                alternative=outside_second_candidate(rates)
                c=comparison[cohort]
                c["n"]+=1
                c["baseline_hits"]+=hit
                alternative_hit=int(winning in alternative)
                c["candidate_hits"]+=alternative_hit
                c["gained"]+=int(alternative_hit and not hit)
                c["lost"]+=int(hit and not alternative_hit)
                c["unchanged_hits"]+=int(hit and alternative_hit)
                if actual_head1:
                    c["actual_second_counts"][str(finish[1])]+=1
                for ticket in tickets:
                    if ticket.startswith("1-"):
                        c["baseline_second_counts"][ticket.split("-")[1]]+=1
                for ticket in alternative:
                    if ticket.startswith("1-"):
                        c["candidate_second_counts"][ticket.split("-")[1]]+=1
            if actual_head1 and not hit and "lane1_strongest" in keys:
                strongest_head1_misses[cohort].append({
                    "race_code":code,"winning_ticket":winning,
                    "second_boat":finish[1],"third_boat":finish[2],
                    "top10_head1_tickets":sum(t.startswith("1-") for t in tickets),
                    "national_win_rates":rates,
                })
            for key in keys:
                output[cohort][key]["n"]+=1
                output[cohort][key]["top10"]+=hit
                output[cohort][key]["top3"]+=int(rank is not None and rank<=3)
                output[cohort][key]["top5"]+=int(rank is not None and rank<=5)
                output[cohort][key]["head1_actual"]+=int(actual_head1)
                output[cohort][key]["head1_top10_hit"]+=int(actual_head1 and hit)
                output[cohort][key]["head1_top10_miss"]+=int(actual_head1 and not hit)
        except (ValueError,TypeError,KeyError,IndexError,OSError,AttributeError):
            rejected+=1
    for cohorts in output.values():
        baseline=cohorts["all"]
        baseline_pct=100*baseline["top10"]/baseline["n"] if baseline["n"] else None
        for row in cohorts.values():
            row["hit_rate_pct"]=round(row["top10"]*100/row["n"],2) if row["n"] else None
            row["selection_pct"]=round(100*row["n"]/baseline["n"],2) if baseline["n"] else None
            row["lift_pp"]=round(100*row["top10"]/row["n"]-baseline_pct,2) if row["n"] and baseline_pct is not None else None
            row["sample_sufficient_30"]=row["n"]>=30
            row["head1_actual_pct"]=round(100*row["head1_actual"]/row["n"],2) if row["n"] else None
            row["head1_top10_hit_given_head1_pct"]=round(100*row["head1_top10_hit"]/row["head1_actual"],2) if row["head1_actual"] else None
            row["head1_top10_miss_given_head1"]=row["head1_top10_miss"]
            for top in ("top3","top5"):
                row[top+"_rate_pct"]=round(100*row[top]/row["n"],2) if row["n"] else None
    return {"scope":"national_win_rate_only_no_entry_or_exhibition_data","rejected":rejected,"cohorts":output,
            "strongest_lane1_head1_top10_misses":strongest_head1_misses,
            "fixed_outside_second_comparison":comparison,
            "saved_advanced_feature_presence":feature_presence}

if __name__=="__main__":
    print(json.dumps(analyze(),ensure_ascii=False,indent=2))

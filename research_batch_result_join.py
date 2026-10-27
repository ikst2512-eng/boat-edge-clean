"""Batch join frozen research Top10 to independently supplied official results.

Exploratory diagnostic ONLY. Does not fetch results, unlock formal Fresh, claim
receipt authenticity, or select favorable matches. Missing races remain missing.
"""
import argparse
import json
from collections import Counter
from pathlib import Path

def reconcile(snapshots, results):
    if not isinstance(results, list):
        raise ValueError("results must be an array")
    indexed, duplicates = {}, set()
    for row in results:
        if not isinstance(row, dict) or not isinstance(row.get("race_code"), str):
            continue
        key = row["race_code"]
        if key in indexed:
            duplicates.add(key)
        indexed[key] = row
    totals, exclusions = Counter(), Counter()
    examples = []
    for path in sorted(Path(snapshots).glob("*.json")):
        totals["snapshots"] += 1
        key = path.stem
        if key in duplicates:
            exclusions["duplicate_result"] += 1
            continue
        result = indexed.get(key)
        if result is None:
            exclusions["missing_result"] += 1
            continue
        if (result.get("status") != "final" or result.get("source_kind") != "official"
                or not isinstance(result.get("ticket"), str)):
            exclusions["unverified_or_nonfinal_result"] += 1
            continue
        ticket = result["ticket"]
        parts = ticket.split("-")
        if len(parts) != 3 or len(set(parts)) != 3 or any(p not in "123456" or len(p) != 1 for p in parts):
            exclusions["invalid_result_ticket"] += 1
            continue
        try:
            forecast = json.loads(path.read_text(encoding="utf-8"))
            picks = forecast["predictions"]
            if (forecast.get("race_code") != key or forecast.get("status") != "research"
                    or forecast.get("validated") is not False
                    or not isinstance(picks,list) or len(picks) != 10 or len(set(picks)) != 10):
                raise ValueError("invalid snapshot")
        except (ValueError, OSError, KeyError, TypeError):
            exclusions["invalid_snapshot"] += 1
            continue
        totals["exploratory_matched"] += 1
        rank = picks.index(ticket)+1 if ticket in picks else None
        for n in (1,3,5,10):
            totals[f"top{n}_hits"] += int(rank is not None and rank <= n)
        examples.append({"race_code":key,"rank":rank})
    return {"status":"EXPLORATORY_JOIN_NOT_FORMAL_SCORING",
            "counts":dict(totals),"excluded":dict(exclusions),
            "matches":examples,
            "eligible_formal":0,
            "warning":"Official source claims and GitHub receipt time are not authenticated here. Do not promote a version from these rates."}

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("results_json", help="independently prepared result manifest; no network access")
    p.add_argument("--snapshots",default="research_snapshots")
    a=p.parse_args()
    print(json.dumps(reconcile(a.snapshots,json.loads(Path(a.results_json).read_text(encoding="utf-8"))),ensure_ascii=False,indent=2))

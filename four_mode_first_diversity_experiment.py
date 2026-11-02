"""Exploratory, result-blind reranking of frozen hit-mode top ten.

Fixed ticket membership, fixed scoring rule; no production or prospective claim.
"""
import json
import re
from collections import defaultdict
from pathlib import Path
from four_mode_frozen_diagnostic import compare_race

ROOT = Path(__file__).resolve().parent
BONUSES = (0.0, 0.15, 0.30)

def rerank(tickets, bonus):
    if len(tickets) < 10:
        raise ValueError("insufficient hit-mode tickets")
    remaining = list(tickets[:10])
    if len({x["combo"] for x in remaining}) != 10:
        raise ValueError("duplicate ticket")
    selected = []
    while remaining:
        seen_first = {x["combo"][0] for x in selected}
        best = max(remaining, key=lambda x: (float(x["p"]) *
                   (1 + bonus * (x["combo"][0] not in seen_first)),
                   float(x["p"]), x["combo"]))
        selected.append(best)
        remaining.remove(best)
    return [x["combo"] for x in selected]

def audit(root=ROOT):
    root = Path(root)
    counters = defaultdict(lambda: {str(b): {"n": 0, "baseline": {f"top{k}": 0 for k in (3,5,10)},
                                           "candidate": {f"top{k}": 0 for k in (3,5,10)},
                                           "gained_top3": 0, "lost_top3": 0} for b in BONUSES})
    excluded = defaultdict(int)
    for path in sorted((root / "four_mode_forecasts").glob("*.json")):
        if not re.fullmatch(r"20[0-9]{10}", path.stem):
            continue
        comp = compare_race(path.stem, root)
        if comp.get("status") != "historical_comparison_only":
            excluded[comp.get("status","unavailable")] += 1
            continue
        try:
            if path.is_symlink() or path.stat().st_size > 30000:
                raise ValueError("unsafe")
            archive = json.loads(path.read_text(encoding="utf-8"))
            if archive.get("race_code") != path.stem:
                raise ValueError("identity")
            version = archive["model_version"]
            tickets = archive["modes"]["hit"]["tickets"]
            winner = comp["winning_ticket"]
            baseline = [x["combo"] for x in tickets[:10]]
            if len(baseline) != 10 or len(set(baseline)) != 10:
                raise ValueError("tickets")
            if any(type(x["p"]) not in (int,float) or not 0 <= x["p"] <= 100 for x in tickets[:10]):
                raise ValueError("probabilities")
            for b in BONUSES:
                candidate = rerank(tickets,b)
                if set(candidate) != set(baseline):
                    raise ValueError("membership_changed")
                row = counters[(version,path.stem[:8])][str(b)]
                row["n"] += 1
                for k in (3,5,10):
                    row["baseline"][f"top{k}"] += winner in baseline[:k]
                    row["candidate"][f"top{k}"] += winner in candidate[:k]
                row["gained_top3"] += winner in candidate[:3] and winner not in baseline[:3]
                row["lost_top3"] += winner in baseline[:3] and winner not in candidate[:3]
        except (OSError,ValueError,KeyError,TypeError,AttributeError):
            excluded["invalid_record"] += 1
    groups = {}
    for (version,day),data in sorted(counters.items()):
        groups.setdefault(version,{})[day] = data
    return {"status":"historical_exploration_only","formal":False,
            "independent_holdout":False,"remote_first_seen_verified":False,
            "fixed_top10_membership":True,"groups":groups,"excluded":dict(excluded),
            "warning":"Already inspected dates, not independent holdout; no model improvement proven."}

if __name__ == "__main__":
    print("DIVERSITY_RERANK=" + json.dumps(audit(),sort_keys=True))

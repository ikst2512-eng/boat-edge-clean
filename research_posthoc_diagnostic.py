"""Post-hoc diagnostic only. Never use its scores for model promotion."""
from research_model import probabilities
from research_scenario_candidate import scenario_probabilities

def paired_diagnostic(records, results):
    ks=(1,3,5,10)
    output={k:{"baseline":0,"candidate":0,"candidate_only":0,"baseline_only":0} for k in ks}
    n=0
    for row in records:
        actual=results.get(row["race_code"])
        if actual is None:
            continue
        rates=row["national_win_rates"]
        base=["-".join(map(str,t)) for t,p in probabilities(rates)[:10]]
        if base!=row["predictions"]:
            raise ValueError("baseline replay mismatch")
        # Candidate receives only pre-race rates; never post-race entry.
        alt=["-".join(map(str,t)) for t,p in scenario_probabilities(rates)[:10]]
        n+=1
        for k in ks:
            b=actual in base[:k]
            c=actual in alt[:k]
            output[k]["baseline"]+=int(b)
            output[k]["candidate"]+=int(c)
            output[k]["candidate_only"]+=int(c and not b)
            output[k]["baseline_only"]+=int(b and not c)
    return {"n":n,"top":{str(k):v for k,v in output.items()},
            "prospective_verified":False,
            "note":"Post-hoc hypothesis check only; candidate was developed after these races."}

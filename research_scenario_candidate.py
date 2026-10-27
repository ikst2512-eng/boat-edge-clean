"""Research-only conditional 1st/2nd/3rd scenario candidate.

Uses ONLY saved pre-race national win rates. This is NOT true ST/entry/exhibition
scenario inference, and must never replace saved formal predictions.
"""
from itertools import permutations
import math

def scenario_candidates(rates):
    if not isinstance(rates,list) or len(rates)!=6 or any(type(x) not in (int,float) or not math.isfinite(x) or x<=0 or x>=20 for x in rates):
        raise ValueError("invalid pre-race rates")
    strength=[math.exp(0.35*(r-sum(rates)/6)) for r in rates]
    # Explicit successive conditional ordering, not independent winner scores.
    # Modest lane priors are hypotheses, not learned tactics.
    first=[strength[i]*[1.65,0.95,0.92,0.88,0.66,0.56][i] for i in range(6)]
    probs=[]
    for a,b,c in permutations(range(6),3):
        pa=first[a]/sum(first)
        second=[strength[i]*([1.0,1.1,1.06,1.04,1.0,0.98][i]) if i!=a else 0 for i in range(6)]
        pb=second[b]/sum(second)
        third=[strength[i] if i!=a and i!=b else 0 for i in range(6)]
        pc=third[c]/sum(third)
        probs.append((f"{a+1}-{b+1}-{c+1}",pa*pb*pc))
    probs.sort(key=lambda t:(-t[1],t[0]))
    return [{"ticket":t,"estimated_probability_pct":round(p*100,3),
             "scenario":"1着先行→2着追走→3着残り（基礎仮説・展開未実証）"} for t,p in probs[:10]]

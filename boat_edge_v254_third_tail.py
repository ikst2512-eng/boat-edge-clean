"""Exact result-blind V254 third-tail ticket selector, reference only.

Copied from old scripts/boat_edge_v254_third_tail.py (blob 677229cfcd6d29ef2dfcd8353da31e438a477637).
No importing old mutable data, future results, network, or formal prediction.
The 37/89 vs 34/89 provisional retrospective observation was NOT proof
of a significant improvement. Keep it separate from original 4 modes.
"""
import re
TRI = re.compile(r"^[1-6]-[1-6]-[1-6]$")

def valid(c):
    return isinstance(c,str) and bool(TRI.fullmatch(c)) and len(set(c.split('-')))==3

def third_tail_candidate(hit,hole):
    """Top7 stays byte-identical; only extra tickets with SAME (1st,2nd) pairs.

    Source holes are pre-frozen ranks; never reorder by odds, results, or payouts.
    If fewer than 3 independent such tickets exist, backfill ORIGINAL Hit10,
    not imputed or post-result tickets. Always exactly 10 distinct valid tickets.
    """
    if (len(hit)!=10 or len(set(hit))!=10 or len(hole)<10 or len(set(hole))!=len(hole) or
        not all(valid(c) for c in hit+hole)):return None
    fixed=hit[:7];prefix={c[:3] for c in fixed}
    novel=[c for c in hole if c not in hit and c[:3] in prefix]
    result=list(fixed)
    for c in novel+hit[7:]:
        if c not in result:result.append(c)
        if len(result)==10:break
    if len(result)!=10:return None
    return result

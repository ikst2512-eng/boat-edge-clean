"""Read-only course-aware challenger for matched prospective TopN evaluation.

Never publishes or rewrites existing forecasts. Uses research_model's historical
boat-index prior; course effects are hypothetical, not empirically calibrated.
"""
from itertools import permutations
from math import exp, isfinite, log
from research_model import probabilities

TICKETS = tuple(permutations(range(1, 7), 3))
TOPNS = (3, 5, 10)


def _entry(value):
    if type(value) not in (tuple, list) or len(value) != 6 or set(value) != set(range(1, 7)):
        raise ValueError("invalid_six_boat_entry")
    if any(type(n) is not int for n in value):
        raise ValueError("invalid_six_boat_entry")
    return tuple(value)


def _records(entry, rows, min_starts):
    if not isinstance(rows, (tuple, list)) or len(rows) != 6:
        raise ValueError("missing_course_records")
    by_boat = {}
    for row in rows:
        if not isinstance(row, dict) or type(row.get("boat")) is not int:
            raise ValueError("invalid_course_record")
        boat = row["boat"]
        if boat in by_boat:
            raise ValueError("duplicate_course_record")
        by_boat[boat] = row
    if set(by_boat) != set(range(1, 7)):
        raise ValueError("missing_course_records")
    for course, boat in enumerate(entry, 1):
        record = by_boat[boat]
        n = record.get("courseStarts")
        if (record.get("course") != course or type(n) is not int or n < min_starts
                or record.get("courseDataSource") != "third_party_historical_asof"
                or not isinstance(record.get("observedAt"), str)
                or record.get("sufficient_sample") is not True):
            raise ValueError("course_sample_or_provenance_inadequate")
        for k in ("courseWinRate", "courseTop2Rate", "courseTop3Rate"):
            v = record.get(k)
            if type(v) not in (float, int) or not isfinite(v) or not 0 <= v <= 1:
                raise ValueError("invalid_course_rate")
        if not (record["courseWinRate"] <= record["courseTop2Rate"] <= record["courseTop3Rate"]):
            raise ValueError("invalid_course_rate_order")
        st = record.get("courseAverageST")
        if type(st) not in (float, int) or not isfinite(st) or not 0 <= st <= 0.5:
            raise ValueError("missing_course_average_st")
    return by_boat


def challenger_rank(national_rates, entry, course_records, *, include_st=False, min_starts=10):
    """Returns three TopN lists in historical *boat numbers*, not course numbers.

    Fixed rule (research hypothesis, not trained): shrink observed course
    1/2/3 finish rates toward common priors using 20 pseudostarts. The baseline
    120-combination distribution is unchanged when adjustment=0. ST treatment
    applies a modest 0.5 ST-difference multiplier, with all parameters frozen.
    """
    entry = _entry(entry)
    by_boat = _records(entry, course_records, min_starts)
    # Existing research model assumes the order maps to positions 1..6.
    positional = probabilities([national_rates[boat-1] for boat in entry])
    # position tuple->boat number tuple; confidence is NOT empirical hit probability
    baseline = [(tuple(entry[c-1] for c in t), p) for t, p in positional]
    # Roles: 1st uses win rate, 2nd uses Top2, 3rd uses Top3.
    priors = (1/6, 2/6, 3/6)
    roles = ("courseWinRate", "courseTop2Rate", "courseTop3Rate")
    raw = []
    for ticket, p in baseline:
        boost = 0.0
        for pos, boat in enumerate(ticket):
            row = by_boat[boat]
            n = row["courseStarts"]
            rate = (n*row[roles[pos]] + 20*priors[pos])/(n+20)
            boost += 0.35*log(rate/priors[pos])
        if include_st:
            # Lower average ST is assigned a modest positive correction.
            boost += sum(0.5*(0.16-by_boat[boat]["courseAverageST"]) for boat in ticket)
        raw.append((ticket, p*exp(boost)))
    total = sum(p for _, p in raw)
    if not isfinite(total) or total <= 0:
        raise ValueError("invalid_candidate_normalization")
    candidate = sorted(((t,p/total) for t,p in raw),key=lambda x:(-x[1], x[0]))
    baseline = sorted(baseline,key=lambda x:(-x[1], x[0]))
    return {"baseline": [("-".join(map(str,t)),p) for t,p in baseline],
            "course": [("-".join(map(str,t)),p) for t,p in
                       challenger_rank._rank_course_without_st(national_rates,entry,by_boat)] if include_st else
                      [("-".join(map(str,t)),p) for t,p in candidate],
            "course_plus_st": [("-".join(map(str,t)),p) for t,p in candidate] if include_st else None,
            "research_only": True, "validated": False, "forecast_usable": False,
            "calibration": "unverified_fixed_hypothesis"}


def _course_only(national_rates,entry,by_boat):
    # Reuse the exact pure candidate path without changing the stored records.
    return [(tuple(int(n) for n in ticket.split("-")),p) for ticket,p in
            challenger_rank(national_rates,entry,list(by_boat.values()),include_st=False)["course"]]
challenger_rank._rank_course_without_st = _course_only


def evaluate_matched(records):
    """Matched, frozen-before-cutoff evaluation, never a buy recommendation.

    rows: [{race_code, cutoff_at, frozen_at, result_received_at,
            result, baseline: [120 tickets], course:[120], course_plus_st:[120]}]
    Ranking format can contain strings or (ticket, model-mass) tuples.
    Invalid or future-leaking rows are excluded from every model equally.
    """
    from datetime import datetime
    def timestamp(s):
        try:
            t=datetime.fromisoformat(s)
            return t if t.utcoffset() is not None else None
        except (TypeError, ValueError):
            return None
    counts={k:{n:0 for n in TOPNS} for k in ("baseline","course","course_plus_st")}
    excluded={}
    used=set()
    total=0
    for row in records:
        try:
            code=row["race_code"]
            cutoff=timestamp(row["cutoff_at"])
            frozen=timestamp(row["frozen_at"])
            result_time=timestamp(row["result_received_at"])
            result=row["result"]
            if not isinstance(code,str) or len(code)!=12 or not code.isascii() or not code.isdigit() or code in used:
                raise ValueError("duplicate_or_bad_race")
            if not cutoff or not frozen or not result_time or frozen>cutoff or result_time<=cutoff:
                raise ValueError("leaky_or_missing_receipt")
            if not isinstance(result,str) or result not in {"-".join(map(str,t)) for t in TICKETS}:
                raise ValueError("invalid_trifecta_result")
            rankings={}
            for name in counts:
                ranking=row[name]
                if type(ranking) not in (list,tuple) or len(ranking)!=120:
                    raise ValueError("incomplete_rankings")
                tickets=[t[0] if isinstance(t,(list,tuple)) else t for t in ranking]
                if len(set(tickets))!=120 or set(tickets)!={"-".join(map(str,t)) for t in TICKETS}:
                    raise ValueError("invalid_rankings")
                rankings[name]=tickets
        except (KeyError,TypeError,ValueError) as exc:
            key=str(exc) if isinstance(exc,ValueError) else "invalid_row"
            excluded[key]=excluded.get(key,0)+1
            continue
        used.add(code)
        total+=1
        for name,ranked in rankings.items():
            for n in TOPNS:
                counts[name][n]+=result in ranked[:n]
    return {"matched_races":total,"excluded":excluded,
            "modes":{k:{"Top"+str(n):{"hits":v[n],"races":total,
                       "hit_rate":round(v[n]/total,6) if total else None} for n in TOPNS}
                     for k,v in counts.items()},
            "research_only":True, "empirical_improvement_verified":False}

"""Outcome-blind feature extraction and retrospective missing 1st-2nd pair audit.

The immutable archive has national win rates, but not reliable per-course second
rates, entrance, exhibition, motor, T-12, or calibrated probabilities.
Never describe these diagnostics as demonstrated causal boat dynamics.
"""
import hashlib
import json
import math
from collections import Counter
from pathlib import Path

from four_mode_archive_api import archived_four_modes
from four_mode_frozen_diagnostic import compare_race, classify_ticket_miss
from four_mode_historical_cohort import run as cohort_run
from hole_top5_safe_bundle_research import proposals

START_NEW="20261103"
PAIR_STATES=("correct_pair_in_hit_and_balance","correct_pair_hit_only",
             "correct_pair_balance_only","correct_pair_not_in_donors")


def pair(ticket):
    return tuple(ticket.split("-")[:2])


def extract_features(code,root,archive):
    """Pre-result features only; raw 6 national rates are optional and uncalibrated."""
    source=Path(root)/"four_mode_forecasts"/(code+".json")
    if source.is_symlink() or not source.is_file() or source.stat().st_size>30000:
        raise ValueError("invalid_source")
    raw=json.loads(source.read_text(encoding="utf-8"))
    rates=raw.get("input_national_win_rates")
    if rates is not None and (not isinstance(rates,list) or len(rates)!=6
        or any(type(v) not in (float,int) or not math.isfinite(v) or v<0 or v>10 for v in rates)):
        raise ValueError("invalid_national_rates")
    m=archive["modes"]
    baseline=[x["combo"] for x in m["hole"]["tickets"][:10]]
    hit=[x["combo"] for x in m["hit"]["tickets"]]
    balance=[x["combo"] for x in m["balance"]["tickets"]]
    # Candidate selection is frozen before looking at the result.
    candidates=proposals(archive)
    def ordered_pairs(items):
        return list(dict.fromkeys(pair(t) for t in items))
    return {"baseline":baseline,
            "hit_pairs":ordered_pairs(hit),"balance_pairs":ordered_pairs(balance),
            "baseline_pairs":ordered_pairs(baseline),
            "protected_bundle":candidates["bundle_protect_top5"],
            "top5_preserved":candidates["bundle_protect_top5"][:5]==baseline[:5],
            "national_rates":rates,
            "feature_available":rates is not None,
            "source_sha256":hashlib.sha256(source.read_bytes()).hexdigest()}


def classify(features,winner):
    """Uses the confirmed winner ONLY for post-hoc attribution."""
    actual_pair=pair(winner)
    if winner in features["baseline"]:
        category="covered"
    else:
        category=classify_ticket_miss(features["baseline"],winner)
    if category=="winner_second_pair_absent":
        h=actual_pair in features["hit_pairs"]
        b=actual_pair in features["balance_pairs"]
        pair_state=("correct_pair_in_hit_and_balance" if h and b else
                    "correct_pair_hit_only" if h else
                    "correct_pair_balance_only" if b else
                    "correct_pair_not_in_donors")
        rank_h=features["hit_pairs"].index(actual_pair)+1 if h else None
        rank_b=features["balance_pairs"].index(actual_pair)+1 if b else None
        proposed_pair=next((pair(t) for t in features["protected_bundle"]
                            if t not in features["baseline"][:10]),None)
        return {"miss_class":category,"pair_state":pair_state,
                "winning_pair_rank_in_hit":rank_h,"winning_pair_rank_in_balance":rank_b,
                "selected_pair_matches_winner":proposed_pair==actual_pair,
                "eligible_pair_head_present":any(pair(t)[0]==actual_pair[0]
                                                 for t in features["baseline"]),
                "winning_second_national_win_rate":
                    (features["national_rates"][int(actual_pair[1])-1]
                     if features["national_rates"] is not None else None)}
    return {"miss_class":category}


def audit_codes(codes,root):
    classes=Counter();donor=Counter();eligible=Counter()
    statuses=Counter();correct_pair_selected=0
    rate_values=[];rank_h=[];rank_b=[];rows=[]
    for code in codes:
        status,archive=archived_four_modes(code,root)
        if status!=200:
            statuses["archive_invalid_or_missing"]+=1;continue
        features=extract_features(code,root,archive)
        if not features["top5_preserved"]:
            raise ValueError("top5_must_remain_unchanged")
        # No confirmed outcome accessed before candidate/feature extraction.
        outcome=compare_race(code,root)
        if outcome.get("status")!="historical_comparison_only":
            statuses["result_unavailable"]+=1;continue
        result=classify(features,outcome["winning_ticket"])
        classes[result["miss_class"]]+=1
        if result["miss_class"]=="winner_second_pair_absent":
            donor[result["pair_state"]]+=1
            eligible["same_head_in_hole"]+=int(result["eligible_pair_head_present"])
            correct_pair_selected+=int(result["selected_pair_matches_winner"])
            if result["winning_pair_rank_in_hit"] is not None:
                rank_h.append(result["winning_pair_rank_in_hit"])
            if result["winning_pair_rank_in_balance"] is not None:
                rank_b.append(result["winning_pair_rank_in_balance"])
            if result["winning_second_national_win_rate"] is not None:
                rate_values.append(result["winning_second_national_win_rate"])
        rows.append({"race_code":code,"outcome_diagnostic":result,
                     "feature_available":features["feature_available"]})
    return {"compared":len(rows),"missing_by_reason":dict(sorted(statuses.items())),
            "coverage_classes":dict(sorted(classes.items())),
            "missing_pair_donor_support":{name:donor[name] for name in PAIR_STATES},
            "missing_pair_selected_by_top5_safe_bundle":correct_pair_selected,
            "missing_pair_same_head_in_baseline":eligible["same_head_in_hole"],
            "winning_pair_donor_pair_rank":{"hit":sorted(Counter(rank_h).items()),
                                            "balance":sorted(Counter(rank_b).items())},
            "national_rate_feature":{"usable_missing_pair_cases":len(rate_values),
                 "mean_winning_second_boat_national_rate":(
                     round(sum(rate_values)/len(rate_values),3) if rate_values else None),
                 "unit":"national win-rate score, not 2nd-place probability"},
            "rows":rows}


def run(root=None):
    root=Path(root) if root else Path(__file__).resolve().parent
    c=cohort_run(root=root,limit=120)
    if c.get("status")!="historical_research_only":
        return {"status":"no_cohort","formal":False}
    # Explicitly remove Nov 3 from reused historical block, avoiding overlap.
    older=sorted(x for x in c["cohort_codes"] if x[:8]<START_NEW)
    current=sorted(x.stem for x in (root/"four_mode_forecasts").glob(START_NEW+"????.json")
                   if not x.is_symlink())
    return {"schema":"HOLE_SECOND_PAIR_EVIDENCE_V1","status":"descriptive_research_only",
            "formal":False,"independent_holdout":False,
            "independent_first_receipt_verified":False,"prospective_validation":False,
            "production_forecast_changed":False,"score_calibrated":False,
            "features_not_available":["second_course_rate","course_entry","exhibition",
                                      "motor","T_minus_12","verified_first_publication"],
            "reused_prior_dates":audit_codes(older,root),
            "nov03_followup":audit_codes(current,root),
            "prior_date_cohort_sha256":hashlib.sha256("\n".join(older).encode()).hexdigest(),
            "warning":"Retrospective diagnosis only: actual winning pair is used for attribution, NEVER candidate selection. Existing 120-cohort has been repeatedly studied and Nov 3 already inspected."}


if __name__=="__main__":
    print(json.dumps(run(),ensure_ascii=False,sort_keys=True))

"""Research-only attribution of locked two-pair Top10 misses and donor coverage.

The existing prospective and production selectors are not modified.
All candidates are selected before confirmed results are read.
Historical results were repeatedly inspected, not an independent holdout.
"""
import json
from collections import Counter
from pathlib import Path

from four_mode_archive_api import archived_four_modes
from four_mode_frozen_diagnostic import compare_race
from four_mode_historical_cohort import run as cohort_run
from hole_chronological_exploratory import date_blocks
from hole_error_attribution_research import failure_class
from hole_pair_diversification_research import first_second
from hole_third_choice_research import national_rates, variants

CAUSES=("hit","first_head_absent","second_pair_absent","third_boat_absent")
SOURCE_BUCKETS=("hole_tail","both_donors","hit_only","balance_only",
                "no_saved_candidate")
SOURCE_STATES=("exact_ticket_in_donors","pair_only_in_donors","no_donor_pair")


def source_bucket(archive, winning):
    """Diagnose an unselected full winning pair, not why it was unselected."""
    pair=first_second(winning)
    hole=[t["combo"] for t in archive["modes"]["hole"]["tickets"]]
    hit=[t["combo"] for t in archive["modes"]["hit"]["tickets"]]
    balance=[t["combo"] for t in archive["modes"]["balance"]["tickets"]]
    if any(first_second(t)==pair for t in hole[10:]):
        return "hole_tail"
    found_hit=any(first_second(t)==pair for t in hit)
    found_balance=any(first_second(t)==pair for t in balance)
    if found_hit and found_balance:return "both_donors"
    if found_hit:return "hit_only"
    if found_balance:return "balance_only"
    return "no_saved_candidate"


def third_donor_state(archive, winning):
    donor=[t["combo"] for mode in ("hit","balance")
           for t in archive["modes"][mode]["tickets"]]
    if winning in donor:
        return "exact_ticket_in_donors"
    if any(first_second(t)==first_second(winning) for t in donor):
        return "pair_only_in_donors"
    return "no_donor_pair"


def inspect(codes,root):
    counts=Counter();transitions=Counter();sources=Counter();third=Counter()
    by_date={};examples=[];missing=Counter();codes_scored=[]
    for code in codes:
        status,archive=archived_four_modes(code,root)
        if status!=200:
            missing["invalid_archive"]+=1
            continue
        rates=national_rates(code,root)
        picks=variants(archive,rates)
        baseline=picks["baseline"]
        locked=picks["third_national_rate"]
        if (len(baseline)!=10 or len(locked)!=10 or
                len(set(locked))!=10 or locked[:5]!=baseline[:5] or
                not {first_second(t) for t in baseline}.issubset(
                    {first_second(t) for t in locked})):
            raise ValueError("locked_top5_budget_or_original_pairs_changed")
        # Do not open the confirmed result until all selectors have run.
        record=compare_race(code,root)
        if record.get("status")!="historical_comparison_only":
            missing["unconfirmed_result"]+=1
            continue
        winning=record["winning_ticket"]
        base_cause=failure_class(baseline,winning)
        cause=failure_class(locked,winning)
        if base_cause not in CAUSES or cause not in CAUSES:
            raise ValueError("unexpected_miss_class")
        counts[cause]+=1
        transitions[base_cause+"__to__"+cause]+=1
        day=by_date.setdefault(code[:8],Counter())
        day["races"]+=1
        day[cause]+=1
        if cause=="second_pair_absent":
            bucket=source_bucket(archive,winning)
            sources[bucket]+=1
            day["pair_"+bucket]+=1
        if cause=="third_boat_absent":
            bucket=third_donor_state(archive,winning)
            third[bucket]+=1
            day["third_"+bucket]+=1
        if base_cause=="hit" and cause!="hit":
            counts["baseline_hit_displaced"]+=1
        if base_cause!="hit" and cause=="hit":
            counts["baseline_miss_rescued"]+=1
        codes_scored.append(code)
        if cause!="hit" and len(examples)<30:
            examples.append({
                "race_code":code,"baseline_cause":base_cause,
                "locked_cause":cause,"winning_pair":"-".join(first_second(winning)),
                "winning_ticket":winning,
                "pair_source":source_bucket(archive,winning)
                               if cause=="second_pair_absent" else None,
                "third_donor_status":third_donor_state(archive,winning)
                                      if cause=="third_boat_absent" else None})
    comparable=len(codes_scored)
    if sum(counts[k] for k in CAUSES)!=comparable:
        raise ValueError("locked_cause_denominator_mismatch")
    if sum(transitions.values())!=comparable:
        raise ValueError("baseline_to_locked_transition_mismatch")
    if sum(sources.values())!=counts["second_pair_absent"]:
        raise ValueError("pair_source_denominator_mismatch")
    if sum(third.values())!=counts["third_boat_absent"]:
        raise ValueError("third_source_denominator_mismatch")
    if (counts["baseline_miss_rescued"]-counts["baseline_hit_displaced"] !=
            counts["hit"]-sum(n for k,n in transitions.items()
                              if k.startswith("hit__to__"))):
        raise ValueError("gained_lost_mismatch")
    return {
        "comparable":comparable,"excluded":dict(missing),
        "miss_classes":{k:counts[k] for k in CAUSES},
        "gain_loss":{"rescued":counts["baseline_miss_rescued"],
                     "displaced":counts["baseline_hit_displaced"],
                     "net":counts["baseline_miss_rescued"]-
                           counts["baseline_hit_displaced"]},
        "baseline_to_locked":dict(sorted(transitions.items())),
        "missing_pair_sources":{k:sources[k] for k in SOURCE_BUCKETS},
        "wrong_third_donor_availability":{k:third[k] for k in SOURCE_STATES},
        "by_date":{k:dict(v) for k,v in sorted(by_date.items())},
        "examples":examples,
        "race_codes":codes_scored,
    }


def run(root=None):
    root=Path(root) if root is not None else Path(__file__).resolve().parent
    cohort=cohort_run(root=root,limit=120)
    if cohort.get("status")!="historical_research_only":
        return {"status":"historical_cohort_unavailable","formal":False}
    old=sorted(c for c in cohort["cohort_codes"] if c[:8]<"20261103")
    blocks=date_blocks(old)
    nov03=sorted(p.stem for p in (root/"four_mode_forecasts").glob(
        "20261103????.json") if not p.is_symlink())
    return {
        "schema":"HOLE_LOCKED_TWO_PAIR_MISS_TAXONOMY_V1",
        "status":"already_inspected_retrospective_only",
        "formal":False,"independent_holdout":False,
        "prospective_validation":False,
        "independent_first_receipt_verified":False,
        "production_forecast_changed":False,"locked_selector_changed":False,
        "groups":{"historical_earlier_reused":inspect(blocks["earlier"],root),
                  "historical_later_reused":inspect(blocks["later"],root),
                  "nov03_already_inspected":inspect(nov03,root)},
        "warning":"Saved ticket availability is not evidence of a recoverable "
                  "live selection or race cause. Historical results already inspected."}


if __name__=="__main__":
    print(json.dumps(run(),ensure_ascii=False,sort_keys=True))

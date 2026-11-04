"""Read-only Nov 4 disjoint-RACE-ID retrospective replication of hole pair diversification.

This is NOT a prospective experiment: the historical outcomes and 2026-11-04
data were already studied. Reject overlap with both previously named 120-race
cohorts. Every forecast-derived candidate is chosen before compare_race reads
a confirmed result. Never treat a pending or missing forecast as a loss.
"""
import json
import re
from collections import Counter
from datetime import date
from pathlib import Path

from hole_fixed_cohort_segment_audit import (
    compare_one, fixed_codes, original_codes, summarize,
)

DAY = "20261104"
EXPECTED_PAIR_COHORT_SIZE = 93
EXPECTED_PAIRED_BEFORE_EXCLUSION = 110

def select_codes(root):
    root = Path(root)
    directory = root / "four_mode_forecasts"
    results = root / "confirmed_results"
    if directory.is_symlink() or results.is_symlink():
        raise ValueError("symlink_forecast_or_result_directory")
    prior_ids = set(fixed_codes()) | set(original_codes())
    files = sorted(directory.glob(DAY + "????.json")) if directory.is_dir() else []
    candidates = []
    counts = Counter()
    for p in files:
        if p.is_symlink() or not p.is_file() or not re.fullmatch(r"20[0-9]{10}", p.stem):
            counts["invalid_forecast_file"] += 1
            continue
        counts["forecast_files"] += 1
        if not (results / p.name).is_file() or (results / p.name).is_symlink():
            counts["result_file_absent"] += 1
            continue
        counts["paired_available"] += 1
        if p.stem in prior_ids:
            counts["already_in_prior_cohort"] += 1
            continue
        candidates.append(p.stem)
    if len(candidates) != len(set(candidates)):
        raise ValueError("duplicate_race_key")
    if len(candidates) != EXPECTED_PAIR_COHORT_SIZE or (
            counts["paired_available"] != EXPECTED_PAIRED_BEFORE_EXCLUSION):
        # Fixed retrospective membership: files silently arriving/removing
        # must never rewrite the published comparison denominator.
        raise ValueError("nov04_cohort_membership_drift")
    if set(candidates) & prior_ids:
        raise ValueError("previously_researched_race_overlap")
    return candidates, dict(counts)

def inspect(root):
    root = Path(root)
    codes, file_counts = select_codes(root)
    rows = [compare_one(code, root) for code in codes]
    if len(rows) != len(codes):
        raise ValueError("unaccounted_race")
    grouped = {}
    for key, classifier in {
        "by_model_version":lambda x:x["model_version"],
        "by_race_round_band":lambda x:"R1-R2" if x["race_number"]<=2 else "R3-R12",
        "by_venue":lambda x:x["venue_code"]
    }.items():
        values={}
        for row in rows: values.setdefault(classifier(row),[]).append(row)
        grouped[key]={name:summarize(selected) for name, selected in sorted(values.items())}
        if sum(x["n"] for x in grouped[key].values()) != len(rows):
            raise ValueError("stratum_denominator_mismatch:" + key)
    summary = summarize(rows)
    for policy in ("same_pair","two_pairs"):
        metrics = summary["policies"][policy]
        baseline = summary["policies"]["baseline"]["hits"]
        if metrics["hits"]["top1"] != baseline["top1"] or (
                metrics["hits"]["top3"] != baseline["top3"] or
                metrics["hits"]["top5"] != baseline["top5"]):
            raise ValueError("top5_must_be_protected")
        for k in ("top1","top3","top5","top10"):
            if metrics["hits"][k] - baseline[k] != metrics["gain"][k] - metrics["loss"][k]:
                raise ValueError("gain_loss_does_not_reconcile")
    return {
        "schema":"HOLE_NOV04_DISJOINT_RETROSPECTIVE_V1",
        "status":"retrospective_replay_only",
        "race_date_jst":date(2026,11,4).isoformat(),
        "previous_historical_cohorts_excluded":True,
        "other_prior_studies_or_tuning_not_excluded":True,
        "formal":False,"prospective_validation":False,
        "independent_first_receipt_verified":False,
        "production_forecast_changed":False,
        "file_counts":file_counts,
        "comparable":len(rows),
        "overall":summary,
        **grouped,
        "race_codes":codes,
        "rows":rows,
        "warning":"Disjoint from TWO named historical cohorts only. Nov 4 outcomes and candidate methods had already been inspected. Not a blind temporal holdout or formal accuracy improvement."
    }

if __name__=="__main__":
    print(json.dumps(inspect(Path(__file__).resolve().parent),ensure_ascii=False,sort_keys=True))

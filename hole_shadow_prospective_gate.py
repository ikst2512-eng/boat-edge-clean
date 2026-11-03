"""Prepare result-blind hole shadow forecasts; evidence stays unverified until externally attested.

No result files are read during freezing. Local timestamps are NOT proof of predeadline
publication; a separate independent first-receipt attestation is required.
"""
import argparse
import hashlib
import json
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path

from four_mode_archive_api import archived_four_modes
from hole_upper_rank_pair_protection import propose
from hole_pair_third_bundle_research import bundle
from hole_third_choice_research import national_rates, variants
from hole_future_locked_eval import FIRST_ELIGIBLE_DAY, verify_locked_selection

JST = timezone(timedelta(hours=9))
TOPS = (3, 5, 10)


def freeze(code, root, now=None, clock=None):
    root = Path(root)
    status, archived = archived_four_modes(code, root)
    if status != 200:
        return {"status": "archive_unavailable", "race_code": code,
                "prospective_verified": False}
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError("naive_now")
    deadline = datetime.fromisoformat(archived["deadline_jst"])
    if deadline.utcoffset() != timedelta(hours=9):
        return {"status": "invalid_deadline_timezone", "race_code": code,
                "prospective_verified": False}
    cutoff = deadline - timedelta(minutes=12)
    if now >= cutoff:
        return {"status": "after_t_minus_12", "race_code": code,
                "prospective_verified": False}
    # Check the real completion time too: a forecast that starts before T-12
    # but finishes later must never be labelled a pre-T-12 frozen candidate.
    clock = clock or (lambda: datetime.now(timezone.utc))
    modes = {name: [x["combo"] for x in archived["modes"][name]["tickets"]]
             for name in ("hole", "hit", "balance")}
    baseline = modes["hole"][:10]
    shadow = propose(baseline, modes["hit"], 3)
    donor = list(dict.fromkeys(modes["hit"] + modes["balance"]))
    shadow_bundle2 = bundle(baseline, donor, 3, 2)
    if len(shadow_bundle2) != len(baseline) or len(set(shadow_bundle2)) != len(shadow_bundle2):
        raise ValueError("bundle_budget_changed")
    if len(shadow) != len(baseline):
        raise ValueError("budget_changed")
    source_path = root / "four_mode_forecasts" / (code + ".json")
    if source_path.is_symlink():
        raise ValueError("symlink_source")
    source_bytes = source_path.read_bytes()
    record = {
        "schema": "HOLE_SHADOW_FREEZE_V1",
        "status": "shadow_frozen_unverified",
        "race_code": code,
        "deadline_jst": archived["deadline_jst"],
        "local_freeze_at_jst": now.astimezone(JST).isoformat(),
        "source_sha256": hashlib.sha256(source_bytes).hexdigest(),
        "model_version": archived["model_version"],
        "candidate_algorithm": "hole_upper_rank_pair_protection.propose:hit_rank3:v1",
        "baseline": baseline, "shadow": shadow,
        "shadow_bundle2": shadow_bundle2,
        "bundle2_algorithm": "hole_pair_third_bundle_research.bundle:hit_balance_rank3_width2:v1",
        "prospective_verified": False,
        "independent_first_receipt_verified": False,
        "production_forecast": False,
        "warning": "Local freeze timestamp is not independent proof. Never call formal performance until independent timestamp+hash proof is verified."
    }
    # The already-locked 2026-11-04+ research method is frozen at the same
    # publication-job timestamp. Never reconstruct an alleged frozen pick
    # using a settled result. Old-period files retain the original V1 schema.
    if deadline.date() >= FIRST_ELIGIBLE_DAY:
        locked=verify_locked_selection()
        choices=variants(archived,national_rates(code,root))
        expected=("baseline","donor_order","max_ticket_score","third_national_rate")
        if set(choices)!=set(expected) or choices["baseline"]!=baseline:
            raise ValueError("unexpected_locked_candidate")
        if any(choices[name][:5]!=baseline[:5] or len(choices[name])!=len(baseline)
               or len(set(choices[name]))!=len(baseline)
               for name in expected):
            raise ValueError("locked_candidate_budget")
        record["future_locked_candidates"]={name:choices[name] for name in expected}
        record["future_locked_method"]="hole_third_choice_research.variants:nov04_locked_v1"
        record["future_locked_selector_git_blobs"]=locked
        record["future_locked_first_eligible_jst"]=FIRST_ELIGIBLE_DAY.isoformat()
    return record


def evaluate(frozen, result, proof=None):
    """Fail closed: do not attribute formal accuracy to unverified local snapshots."""
    if frozen.get("status") != "shadow_frozen_unverified":
        return {"status": "ineligible_freeze", "formal": False}
    if not proof or proof.get("verified_by_independent_process") is not True:
        return {"status": "awaiting_independent_receipt_proof", "formal": False}
    # A self-asserted proof file is not an independent verification implementation.
    return {"status": "independent_proof_review_required", "formal": False}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("race_code")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    print(json.dumps(freeze(args.race_code, args.root), ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()

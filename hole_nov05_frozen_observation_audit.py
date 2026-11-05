"""2026-11-05 hole-shadow/remote-observation gated partial research comparison.

Research-only: same-job frozen research shadow & server observed BEFORE T-12,
NOT independently certified first remote receipt. Never promote these
figures as formal accuracy. Missing/unsettled result files are excluded.
"""
import argparse
import hashlib
import json
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

from hole_future_shadow_audit import audit as frozen_shadow_audit, POLICIES, TOPS
from hole_fixed_cohort_segment_audit import frozen_proposals
from four_mode_archive_api import archived_four_modes
from four_mode_frozen_diagnostic import compare_race

DAY = "20261105"
RUN_ID = 41953950959
PUBLICATION_SHA = "e5fd8ffacd7e0f1a721cfe7d755b9085df5f04fa"
EXPECTED_FROZEN = 106

def load_json(path):
    p = Path(path)
    if p.is_symlink() or not p.is_file() or p.stat().st_size>2000000:
        raise ValueError("missing_untrusted_evidence_file")
    return json.loads(p.read_text(encoding="utf-8"))

def validate_early_server_observation(shadow, observed, root):
    """Fail closed on record loss, mismatched bytes, weak or late observations."""
    if not (shadow.get("status") == "research_only_after_confirmed_push"
            and shadow.get("schema") == "HOLE_SHADOW_PUBLISHED_SAME_JOB_V1"
            and shadow.get("publication_commit_sha") == PUBLICATION_SHA
            and shadow.get("formal") is False
            and shadow.get("independent_first_receipt_verified") is False
            and shadow.get("frozen_count") == EXPECTED_FROZEN
            and shadow.get("validation_error_count") == 0
            and observed.get("status") == "remote_observation_audited_nonformal"
            and observed.get("github_server_observation_not_first_receipt") is True
            and observed.get("independent_first_remote_receipt_verified") is False
            and observed.get("publication_commit_sha") == PUBLICATION_SHA
            and observed.get("publication_count") == EXPECTED_FROZEN
            and observed.get("observed_before_t_minus_12") == EXPECTED_FROZEN
            and observed.get("observed_after_t_minus_12") == 0
            and observed.get("unverified_count") == 0):
        raise ValueError("shadow_or_observation_contract_mismatch")
    sr=shadow.get("records");orows=observed.get("records")
    if not isinstance(sr,list) or not isinstance(orows,list) or (
            len(sr)!=EXPECTED_FROZEN or len(orows)!=EXPECTED_FROZEN):
        raise ValueError("evidence_count_mismatch")
    def indexed(rows):
        mapping={}
        for x in rows:
            if not isinstance(x,dict) or x.get("race_code") in mapping or (
                    not isinstance(x.get("race_code"),str) or
                    not x["race_code"].startswith(DAY) or
                    len(x["race_code"])!=12):
                raise ValueError("evidence_race_code_invalid_or_duplicate")
            mapping[x["race_code"]]=x
        return mapping
    shadow_by_code=indexed(sr);observed_by_code=indexed(orows)
    if set(shadow_by_code)!=set(observed_by_code):
        raise ValueError("observed_code_coverage_incomplete")
    for code,x in shadow_by_code.items():
        r=observed_by_code[code]
        if x.get("status")!="shadow_frozen_unverified" or (
                x.get("independent_first_receipt_verified") is not False) or (
                r.get("status")!="github_server_observed_before_t_minus_12") or (
                r.get("first_add_blob_matches_remote") is not True) or (
                r.get("first_add_commit")!=PUBLICATION_SHA) or (
                x.get("source_sha256")!=r.get("original_sha256")):
            raise ValueError("unproven_or_hash_mismatch:"+code)
        observed_at=datetime.fromisoformat(r["github_api_server_date_utc"])
        cutoff=datetime.fromisoformat(x["t_minus_12_jst"])
        frozen_at=datetime.fromisoformat(x["local_freeze_at_jst"])
        if (observed_at.utcoffset() is None or
                cutoff.utcoffset()!=timedelta(hours=9) or
                frozen_at.utcoffset()!=timedelta(hours=9) or
                observed_at>=cutoff or frozen_at>=cutoff):
            raise ValueError("not_observed_and_frozen_before_t_minus_12:"+code)
        path=Path(root)/"four_mode_forecasts"/(code+".json")
        if path.is_symlink() or not path.is_file() or (
                hashlib.sha256(path.read_bytes()).hexdigest()!=x["source_sha256"]):
            raise ValueError("published_source_bytes_differ:"+code)
    return shadow_by_code

def score(root, shadow_path, observed_path):
    root=Path(root)
    shadow=load_json(shadow_path); observed=load_json(observed_path)
    by_code=validate_early_server_observation(shadow, observed, root)
    frozen=frozen_shadow_audit(root,shadow_path)
    if frozen.get("status")!="research_only_matched_local_freezes" or (
            frozen.get("formal") is not False or
            frozen.get("independent_first_receipt_verified") is not False):
        raise ValueError("unusable_frozen_shadow_replay")
    codes=frozen.get("eligible_codes",[])
    if len(codes)!=EXPECTED_FROZEN or set(codes)!=set(by_code) or (
            frozen.get("excluded_by_reason",{}).get("candidate_replay_mismatch",0)>0):
        raise ValueError("candidate_not_replay_verified")
    rows=frozen["rows"]
    if len({r["race_code"] for r in rows})!=len(rows) or (
            not set(r["race_code"] for r in rows).issubset(set(codes))):
        raise ValueError("unbacked_or_duplicate_comparison")
    # Same-pair/two-pair are separately labelled historical replay, not
    # candidate arrays frozen within this Nov-5 artifact.
    scenarios=("baseline","same_pair","two_pairs")
    hits={p:{f"top{k}":0 for k in TOPS} for p in scenarios}
    gained={p:Counter() for p in scenarios}
    lost={p:Counter() for p in scenarios}
    retained_rank_worse=Counter()
    frozen_top1={p:0 for p in POLICIES}
    frozen_head_first={p:0 for p in POLICIES}
    frozen_head_in_top10={p:0 for p in POLICIES}
    pair_top1={p:0 for p in scenarios}
    pair_head_first={p:0 for p in scenarios}
    full_rows=[]
    for row in rows:
        code=row["race_code"]
        state, archive=archived_four_modes(code,root)
        if state!=200:
            raise ValueError("archive_disappeared:"+code)
        candidates=frozen_proposals(archive)  # Result-blind.
        if candidates["baseline"]!=by_code[code]["baseline"]:
            raise ValueError("baseline_vs_stored_freeze_mismatch:"+code)
        result=compare_race(code,root)
        if result.get("status")!="historical_comparison_only":
            raise ValueError("settled_result_disappeared:"+code)
        winner=result["winning_ticket"]
        stored=by_code[code]["future_locked_candidates"]
        for policy in POLICIES:
            frozen_picks=stored[policy]
            frozen_top1[policy]+=int(frozen_picks[0]==winner)
            frozen_head_first[policy]+=int(frozen_picks[0].split("-")[0]==winner.split("-")[0])
            frozen_head_in_top10[policy]+=int(any(
                t.split("-")[0]==winner.split("-")[0] for t in frozen_picks[:10]))
        for policy in scenarios:
            pair_top1[policy]+=int(candidates[policy][0]==winner)
            pair_head_first[policy]+=int(
                candidates[policy][0].split("-")[0]==winner.split("-")[0])
        flags={p:{f"top{k}":winner in picks[:k] for k in TOPS}
               for p,picks in candidates.items()}
        if flags["baseline"]!=row["flags"]["baseline"]:
            raise ValueError("independent_frozen_baseline_score_mismatch:"+code)
        for p in scenarios:
            for k in TOPS:
                key=f"top{k}"; flag=flags[p][key]
                hits[p][key]+=int(flag)
                if flag and not flags["baseline"][key]:gained[p][key]+=1
                if not flag and flags["baseline"][key]:lost[p][key]+=1
            if p!="baseline" and winner in candidates["baseline"][:10] and (
                    winner in candidates[p][:10]) and candidates[p].index(winner)>candidates["baseline"].index(winner):
                retained_rank_worse[p]+=1
        full_rows.append({"race_code":code,"flag_frozen":row["flags"],
                          "flag_replayed":flags})
    # Same-job frozen selector counts must exactly match original audit.
    for p in POLICIES:
        for k in TOPS:
            key=f"top{k}"
            original=sum(int(row["flag_frozen"][p][key]) for row in full_rows)
            if original != frozen["hits"][p][key]:
                raise ValueError("frozen_policy_attribution_mismatch")
    for p in scenarios:
        for k in TOPS:
            key=f"top{k}"
            if hits[p][key]-hits["baseline"][key]!=gained[p][key]-lost[p][key]:
                raise ValueError("retrospective_pair_attribution_mismatch")
    if any(hits[p][f"top{k}"]!=hits["baseline"][f"top{k}"]
           for p in scenarios[1:] for k in (3,5)):
        raise ValueError("top5_protection_failed")
    return {
        "schema":"HOLE_NOV05_FROZEN_SERVER_OBSERVED_PARTIAL_V1",
        "status":"pre_t12_server_observed_research_only",
        "race_day_jst":"2026-11-05",
        "capture_run_id":RUN_ID,
        "publication_commit_sha":PUBLICATION_SHA,
        "formal":False,
        "independent_first_receipt_verified":False,
        "prospective_validation":False,
        "production_forecast_changed":False,
        "observed_pre_t12":len(by_code),
        "frozen_selector_replay_eligible":len(codes),
        "paired_confirmed":len(rows),
        "not_yet_comparable":len(codes)-len(rows),
        "frozen_policies":frozen["hits"],
        "frozen_top1_exact_ticket":frozen_top1,
        "frozen_head_of_first_ticket_correct":frozen_head_first,
        "frozen_head_represented_in_top10":frozen_head_in_top10,
        "frozen_delta":frozen["delta"],
        "replayed_pair_policies":hits,
        "replayed_top1_exact_ticket":pair_top1,
        "replayed_head_of_first_ticket_correct":pair_head_first,
        "replayed_pair_delta":{p:{f"top{k}":{"gained":gained[p][f"top{k}"],
                                          "lost":lost[p][f"top{k}"],
                                          "net":gained[p][f"top{k}"]-lost[p][f"top{k}"]}
                                   for k in TOPS} for p in scenarios[1:]},
        "replayed_existing_top10_rank_worse":dict(retained_rank_worse),
        "excluded_by_reason":frozen["excluded_by_reason"],
        "per_race_flags":{r["race_code"]:{"frozen":r["flag_frozen"],
                                         "posthoc_pair":r["flag_replayed"]} for r in full_rows},
        "warning":"Live-job same-day frozen predictions & GitHub server observation are NOT independent first remote receipt. Pair strategies replayed after outcomes and must not be called prospective. Complete result and capture census not yet proven."
    }

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--root",default=".")
    parser.add_argument("--shadow",required=True)
    parser.add_argument("--observed",required=True)
    args=parser.parse_args()
    print(json.dumps(score(args.root,args.shadow,args.observed),ensure_ascii=False,sort_keys=True))

if __name__=="__main__":
    main()

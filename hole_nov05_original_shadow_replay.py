"""Research-only Nov 5 original GitHub-captured hole shadow replay.

No new or reconstructed winning ticket may enter the frozen cohort.
Compare solely the 106 records in the original publication-job artifact.
GitHub observed-before-T12 != independently verified first remote receipt.
The race day may have late, unconfirmed, or missing results.
"""
import argparse
import json
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

from four_mode_archive_api import archived_four_modes
from four_mode_frozen_diagnostic import compare_race, classify_ticket_miss
from hole_future_shadow_audit import audit as replay, POLICIES, TOPS

DAY = "20261105"
CAPTURE_RUN = 41953950959
EXPECTED_PUBLISHED = 106
EXPECTED_COMMIT = "e5fd8ffacd7e0f1a721cfe7d755b9085df5f04fa"

def shadow_vs_source_clock(rec, observed, cutoff):
    """A GitHub observation of the SOURCE cannot attest a later shadow freeze."""
    local=datetime.fromisoformat(rec["local_freeze_at_jst"])
    if (local.utcoffset()!=timedelta(hours=9)
            or observed.utcoffset()!=timedelta(0)
            or cutoff.utcoffset()!=timedelta(hours=9)):
        raise ValueError("invalid_source_shadow_timezone")
    if local>=cutoff:
        raise ValueError("shadow_local_freeze_not_before_t12")
    return {"source_observed_before_shadow_freeze":observed<local,
            "shadow_local_freeze_before_t12":True,
            "source_observation_to_shadow_freeze_seconds":round(
                  (local-observed).total_seconds(),6)}

def safe_json(path):
    path=Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size>4_000_000:
        raise ValueError("missing_or_unsafe_artifact_file:"+path.name)
    obj=json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(obj,dict):
        raise ValueError("artifact_not_object:"+path.name)
    return obj

def inspect(root, artifact):
    root=Path(root)
    folder=Path(artifact)
    if folder.is_symlink() or not folder.is_dir():
        raise ValueError("capture_directory_missing")
    evidence=folder/"four-mode-evidence"
    shadow_path=evidence/"hole-shadow.json"
    shadow=safe_json(shadow_path)
    remote=safe_json(evidence/"github-server-observation.json")
    publication=safe_json(evidence/"publication.json")
    if (shadow.get("status")!="research_only_after_confirmed_push"
            or shadow.get("schema")!="HOLE_SHADOW_PUBLISHED_SAME_JOB_V1"
            or shadow.get("formal") is not False
            or shadow.get("independent_first_receipt_verified") is not False
            or shadow.get("production_forecast_changed") is not False):
        raise ValueError("shadow_not_usable_nonformal")
    records=shadow.get("records")
    if (not isinstance(records,list)
            or len(records)!=EXPECTED_PUBLISHED
            or shadow.get("frozen_count")!=EXPECTED_PUBLISHED
            or shadow.get("published_new_count")!=EXPECTED_PUBLISHED
            or shadow.get("publication_commit_sha")!=EXPECTED_COMMIT):
        raise ValueError("shadow_cohort_identity_or_size")
    if (publication.get("outcome")!="pushed_to_main"
            or publication.get("commit_sha")!=EXPECTED_COMMIT
            or publication.get("added_forecasts")!=EXPECTED_PUBLISHED):
        raise ValueError("publication_not_original_106")
    if (remote.get("schema")!="FOUR_MODE_GITHUB_REMOTE_OBSERVATION_V1"
            or remote.get("status")!="remote_observation_audited_nonformal"
            or remote.get("github_server_observation_not_first_receipt") is not True
            or remote.get("formal") is not False
            or remote.get("independent_first_remote_receipt_verified") is not False
            or remote.get("publication_commit_sha")!=EXPECTED_COMMIT
            or remote.get("publication_count")!=EXPECTED_PUBLISHED
            or remote.get("observed_before_t_minus_12")!=EXPECTED_PUBLISHED
            or remote.get("observed_after_t_minus_12")!=0
            or remote.get("unverified_count")!=0):
        raise ValueError("remote_observation_not_early_and_nonformal")
    observed=remote.get("records")
    if not isinstance(observed,list) or len(observed)!=EXPECTED_PUBLISHED:
        raise ValueError("remote_observation_roster_missing")
    original={}
    for rec in records:
        if not isinstance(rec,dict) or rec.get("race_code","")[:8]!=DAY:
            raise ValueError("invalid_shadow_race_code")
        code=rec["race_code"]
        if code in original or rec.get("status")!="shadow_frozen_unverified":
            raise ValueError("duplicate_or_not_frozen_shadow")
        original[code]=rec
    seen=set()
    clock_rows={}
    for obs in observed:
        if not isinstance(obs,dict):
            raise ValueError("invalid_remote_row")
        code=obs.get("race_code")
        rec=original.get(code)
        if not rec or code in seen:
            raise ValueError("remote_shadow_race_mismatch")
        seen.add(code)
        if (obs.get("status")!="github_server_observed_before_t_minus_12"
                or obs.get("first_add_commit")!=EXPECTED_COMMIT
                or obs.get("first_add_blob_matches_remote") is not True
                or obs.get("original_sha256")!=rec.get("source_sha256")
                or obs.get("independent_first_remote_receipt_verified") is not False):
            raise ValueError("incorrect_remote_hash_or_status")
        observed_time=datetime.fromisoformat(obs["github_api_server_date_utc"])
        cutoff=datetime.fromisoformat(obs["deadline_minus_12_jst"])
        if (observed_time.utcoffset()!=timedelta(0)
                or cutoff.utcoffset()!=timedelta(hours=9)
                or cutoff.isoformat()!=rec.get("t_minus_12_jst")
                or not observed_time<cutoff):
            raise ValueError("remote_timestamp_not_early")
        clock_rows[code]=shadow_vs_source_clock(rec,observed_time,cutoff)
    if seen != set(original):
        raise ValueError("remote_roster_incomplete")
    # Source-level candidate identity: this comparison is entirely outcome-blind.
    def count_same(a,b):
        return sum(rec["future_locked_candidates"][a]==
                   rec["future_locked_candidates"][b]
                   for rec in original.values())
    policy_equivalence={
        "donor_order_equals_max_ticket_score":count_same("donor_order","max_ticket_score"),
        "donor_order_equals_third_national_rate":count_same("donor_order","third_national_rate"),
        "donor_order_equals_baseline":count_same("donor_order","baseline"),
        "third_national_rate_equals_baseline":count_same("third_national_rate","baseline"),
    }
    scored=replay(root,shadow_path)
    if (scored.get("formal") is not False
            or scored.get("independent_first_receipt_verified") is not False
            or scored.get("production_forecast_changed") is not False):
        raise ValueError("replay_claims_formal_evidence")
    replay_codes=scored.get("eligible_codes")
    rows=scored.get("rows")
    if (not isinstance(replay_codes,list) or len(replay_codes)!=len(set(replay_codes))
            or not set(replay_codes).issubset(original)
            or not isinstance(rows,list)
            or len(rows)!=scored.get("comparable")
            or not set(r["race_code"] for r in rows).issubset(set(replay_codes))):
        raise ValueError("replay_unbacked_race")
    for name in POLICIES:
        for k in TOPS:
            key=f"top{k}"
            calculated=sum(int(row["flags"][name][key]) for row in rows)
            if calculated!=scored["hits"][name][key]:
                raise ValueError("replay_hits_not_reconciled")
    # Score head and pair coverage only AFTER the verified snapshot candidates
    # and original remote publication records have been fully validated.
    heads=Counter()
    pair_misses=Counter()
    by_race={}
    for row in rows:
        code=row["race_code"]
        rec=original[code]
        status,archive=archived_four_modes(code,root)
        outcome=compare_race(code,root)
        if status!=200 or outcome.get("status")!="historical_comparison_only":
            raise ValueError("scored_race_not_confirmed")
        frozen=rec["future_locked_candidates"]["baseline"]
        if frozen!=rec["baseline"] or frozen!=[t["combo"] for t in archive["modes"]["hole"]["tickets"][:10]]:
            raise ValueError("baseline_changed_since_original_freeze")
        winning=outcome["winning_ticket"]
        heads["rank1_correct_head"]+=int(frozen[0].split("-")[0]==winning.split("-")[0])
        heads["rank1_exact_trifecta"]+=int(frozen[0]==winning)
        heads["head_exists_anywhere_top10"]+=int(any(t.split("-")[0]==winning.split("-")[0] for t in frozen))
        miss_class=classify_ticket_miss(frozen,winning)
        pair_misses[miss_class]+=1
        ranks={}
        for name in POLICIES:
            p=rec["future_locked_candidates"][name]
            ranks[name]=p.index(winning)+1 if winning in p else 0
            if bool(0<ranks[name]<=10) != row["flags"][name]["top10"]:
                raise ValueError("winning_rank_and_flag_conflict")
        by_race[code]={
            "winning_ticket":winning,
            "baseline_miss_class":miss_class,
            "frozen_candidate_winning_ranks":ranks,
            "baseline_top1_head_match":frozen[0].split("-")[0]==winning.split("-")[0]
        }
    paired_changes={}
    for name in POLICIES[1:]:
        gained=[];lost=[]
        for row in rows:
            code=row["race_code"]
            old=row["flags"]["baseline"]["top10"]
            new=row["flags"][name]["top10"]
            if new and not old:gained.append({"race_code":code,**by_race[code]})
            if old and not new:lost.append({"race_code":code,**by_race[code]})
        if (len(gained)!=scored["delta"][name]["top10"]["gained"]
                or len(lost)!=scored["delta"][name]["top10"]["lost"]):
            raise ValueError("race_level_gain_loss_mismatch")
        paired_changes[name]={
            "gained":gained, "lost":lost,
            "gained_winning_ticket_distribution":dict(sorted(
                Counter(item["winning_ticket"] for item in gained).items())),
            "lost_winning_ticket_distribution":dict(sorted(
                Counter(item["winning_ticket"] for item in lost).items())),
        }
    return {
        "schema":"HOLE_NOV05_ORIGINAL_106_SHADOW_REPLAY_V1",
        "status":("captured_cohort_all_results_matched_nonformal"
                  if len(rows)==EXPECTED_PUBLISHED else "partial_day_replay_nonformal"),
        "original_capture_run":CAPTURE_RUN,
        "original_publication_commit":EXPECTED_COMMIT,
        "race_date_jst":"2026-11-05",
        "original_frozen_count":EXPECTED_PUBLISHED,
        "github_observed_before_t12_not_first_receipt":len(seen),
        "source_forecast_github_observed_before_t12":len(seen),
        "source_observed_before_shadow_freeze_count":sum(
            r["source_observed_before_shadow_freeze"] for r in clock_rows.values()),
        "shadow_local_freeze_before_t12_count":sum(
            r["shadow_local_freeze_before_t12"] for r in clock_rows.values()),
        "source_observation_to_shadow_freeze_seconds_range":{
            "min":min(r["source_observation_to_shadow_freeze_seconds"] for r in clock_rows.values()),
            "max":max(r["source_observation_to_shadow_freeze_seconds"] for r in clock_rows.values()),
        },
        "source_remote_observation_is_shadow_receipt":False,
        "shadow_first_remote_receipt_independently_verified":False,
        "replay_verified_candidate_count":len(replay_codes),
        "comparable_confirmed":len(rows),
        "frozen_without_scored_result":len(replay_codes)-len(rows),
        "captured_cohort_all_results_matched":len(rows)==len(replay_codes)==EXPECTED_PUBLISHED,
        "replay_excluded_by_reason":scored.get("excluded_by_reason",{}),
        "head_metrics":dict(heads),
        "policy_equivalence_frozen_without_results":policy_equivalence,
        "baseline_top10_miss_classes":dict(pair_misses),
        "paired_top10_change_cases":paired_changes,
        "per_race_winning_rank_evidence":by_race,
        "hits":scored["hits"],
        "gain_loss":scored["delta"],
        "race_codes_scored":[r["race_code"] for r in rows],
        "per_race_flags":{r["race_code"]:r["flags"] for r in rows},
        "capture_window_complete_proven":False,
        "formal":False,"independent_first_receipt_verified":False,
        "prospective_validation":False,"production_forecast_changed":False,
        "warning":"GitHub server observations apply only to original forecast blobs, NOT to the later-produced shadow candidate list; these 106 shadow freezes all happened after original forecast observation. Both clocks are before T-12 but no independent first remote receipt exists for shadow candidates. This is historical research, not formal live accuracy."
    }

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--root",default=".")
    p.add_argument("--capture-dir",required=True)
    args=p.parse_args()
    print(json.dumps(inspect(args.root,args.capture_dir),ensure_ascii=False,sort_keys=True))

if __name__=="__main__":main()

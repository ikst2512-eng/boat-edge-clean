"""Reconcile Nov 5 historical archive outcomes with fixed hole rank3 proposal.

All candidate picks are computed from the frozen archived original BEFORE the
outcome reader is called by score_one. This is a *post-result replay*, NOT a
pre-result frozen candidate or prospective study sample. Never promote it.
"""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path

from nov05_four_mode_snapshot_audit import (
    DAY, inventory, _local_source_t12_status, run as snapshot_run,
)
from pinned_hole_rank3_research import (
    TOPS, score_one, paired_exact_two_sided_p,
)


def _digest(codes):
    return hashlib.sha256(("\n".join(codes) + "\n").encode("ascii")).hexdigest()


def run(root, *, git=None, scorer=score_one, snapshot_checker=snapshot_run):
    root = Path(root)
    git = git or (lambda args: subprocess.check_output(
        ["git", *args], cwd=root, timeout=35))
    main_sha, contents = inventory(root, git=git)
    # Explicitly refuse a detached or stale feature-branch checkout. CI uses
    # the same fetched refs/remotes/origin/main for the worktree and scoring.
    remote_main = git(["rev-parse", "--verify", "refs/remotes/origin/main"])
    if (type(remote_main) is not bytes
            or remote_main.decode("ascii").strip() != main_sha):
        raise ValueError("checked_out_main_ref_mismatch")
    original = contents["four_mode_forecasts"]
    outcomes = contents["confirmed_results"]
    evaluated_roster = sorted(original & outcomes)
    local_t12_failures = [code for code in evaluated_roster
                          if _local_source_t12_status(code, root)
                          != "local_claimed_T_minus_12_consistent"]
    rows = []
    invalid = []
    for code in evaluated_roster:
        if code in local_t12_failures:
            invalid.append({"race_code": code, "reason": "untrusted_local_source_t12"})
            continue
        try:
            record = scorer(code, root)
        except (KeyError, ValueError, TypeError, AttributeError, OSError,
                UnicodeError, IndexError) as exc:
            record = {"race_code": code,
                      "status": "scoring_exception_" + type(exc).__name__}
        if (type(record) is dict
                and record.get("race_code") == code
                and record.get("status") == "historical_comparison_only"
                and record.get("formal") is False):
            rows.append(record)
        else:
            invalid.append({"race_code": code, "reason": (
                record.get("status", "unknown") if type(record) is dict
                else "nonobject_response")})
    passed_codes = {r["race_code"] for r in rows}
    if (len(passed_codes) != len(rows)
            or not passed_codes.issubset(set(evaluated_roster))
            or len(rows) + len(invalid) != len(evaluated_roster)):
        raise ValueError("paired_research_roster_disagrees")

    # A strict historical snapshot scorer is a separate consistency check
    # against frozen four-mode records. This check also remains nonformal.
    same = snapshot_checker(root, git=git)
    if (same["examined_main_sha"] != main_sha
            or set(same["intersection_race_codes"]) != set(evaluated_roster)
            or same.get("four_mode_original_files") != len(original)
            or same.get("clean_separate_original_files") !=
                len(contents["prospective_predictions"])):
        raise ValueError("snapshot_roster_disagrees")
    complete = (bool(evaluated_roster) and not invalid
                and same["status"] == "main_snapshot_research_comparable"
                and same["result_content_comparable_count"] == len(evaluated_roster)
                and len(rows) == len(evaluated_roster))
    metrics = None
    if complete:
        metrics = {}
        for n in TOPS:
            key = f"top{n}"
            before = sum(r["topn"][key]["baseline"] is True for r in rows)
            after = sum(r["topn"][key]["candidate"] is True for r in rows)
            gained = sum(r["topn"][key]["gained"] is True for r in rows)
            lost = sum(r["topn"][key]["lost"] is True for r in rows)
            if (before != same["historical_topn_hits"]["hole"][key]
                    or after - before != gained - lost):
                raise ValueError("four_mode_hole_baseline_or_gain_loss_mismatch")
            metrics[key] = {
                "baseline_hits": before, "candidate_hits": after,
                "gained": gained, "lost": lost, "net": gained - lost,
                "baseline_pct": round(100 * before / len(rows), 2),
                "candidate_pct": round(100 * after / len(rows), 2),
                "exploratory_uncorrected_exact_p": (
                    round(paired_exact_two_sided_p(gained, lost), 6)
                    if gained + lost else None),
            }
    return {
        "schema": "FOUR_MODE_NOV05_HOLE_RANK3_POST_RESULT_REPLAY_V1",
        "status": ("retrospective_complete_not_prospective" if complete
                   else "no_complete_research_pairwise_cohort"),
        "day_jst": DAY,
        "main_sha": main_sha,
        "forecast_original_count": len(original),
        "independent_result_filename_count": len(outcomes),
        "forecast_and_result_filename_pairs": len(evaluated_roster),
        "forecast_pending_result_filename": len(original - outcomes),
        "clean_separate_collector_count": len(contents["prospective_predictions"]),
        "retrospective_roster_sha256": _digest(evaluated_roster),
        "retrospective_race_ids": evaluated_roster,
        "comparable": len(rows),
        "invalid_or_untrusted": invalid,
        "local_source_t12_inconsistent_codes": local_t12_failures,
        "simulated_candidate_changed": sum(bool(r["changed"]) for r in rows),
        "topn": metrics,
        "per_race": rows,
        "prospective_enrolled_races": None,
        "formal_eligible_races": None,
        "first_git_add_chronology_verified": False,
        "remote_predeadline_original_observation_verified": False,
        "all_capture_runs_verified": False,
        "pre_result_candidate_artifact_verified": False,
        "official_beforeinfo_six_racers_verified": False,
        "prospective_validation": False,
        "formal": False,
        "model_improvement_proven": False,
        "production_forecast_changed": False,
        "warning": ("Post-result replay from actual frozen archive file contents, "
                    "not a pre-result recorded shadow or proven first remote "
                    "publication. Historical p-values are unadjusted and "
                    "selection/reporting after seeing available results remains "
                    "vulnerable to bias. Do not enroll these scores into the "
                    "precommitted 300-race forward study.")
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--main-root", type=Path, required=True)
    parser.add_argument("--output", default="nov05_hole_rank3_post_result_replay.json")
    args = parser.parse_args()
    result = run(args.main_root)
    Path(args.output).write_text(json.dumps(result, indent=2, sort_keys=True,
                                            ensure_ascii=False) + "\n",
                                 encoding="utf-8")
    print("NOV05_HOLE_RANK3_POST_RESULT=" + json.dumps({
        k: result[k] for k in
        ("main_sha", "status", "forecast_original_count",
         "forecast_and_result_filename_pairs", "forecast_pending_result_filename",
         "comparable", "simulated_candidate_changed", "topn",
         "prospective_enrolled_races", "formal")
    }, ensure_ascii=False, sort_keys=True))
    return 0 if result["status"] == "retrospective_complete_not_prospective" else 2


if __name__ == "__main__":
    raise SystemExit(main())

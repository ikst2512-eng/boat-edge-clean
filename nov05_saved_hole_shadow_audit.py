"""Verify an actual Nov 5 Actions-frozen hole shadow against confirmed results.

Research-only, partial-day diagnostics; do not use for formal, preregistered
300-race effect estimation or model promotion. Candidate tickets come ONLY
from the original GitHub Actions artifact, never from post-result generation.
"""
import argparse
import hashlib
import json
import re
from collections import Counter
from functools import lru_cache
from pathlib import Path
import subprocess

from forward_hole_saved_evidence_gate import inspect_race

RUN_ID = 41953950959
RUN_HEAD_SHA = "ab579c62a425ef70bbfbcf59ce936627c5d8ce9e"
PUBLICATION_SHA = "e5fd8ffacd7e0f1a721cfe7d755b9085df5f04fa"
DAY = "20261105"
EXPECTED_PUBLICATION = 106
TOPS = ("top1", "top3", "top5", "top10")
OK = "matched_saved_shadow_and_remote_observation_research_only"
PRE = "pre_result_evidence_consistent_research_only"
PENDING = "pending_independent_result"


def read_json(path, limit):
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > limit:
        raise ValueError("missing_or_unsafe_actions_evidence")
    try:
        record = json.loads(path.read_bytes())
    except (UnicodeError, ValueError) as exc:
        raise ValueError("malformed_actions_evidence") from exc
    if type(record) is not dict:
        raise ValueError("non_object_actions_evidence")
    return record


def metadata_guard(metadata):
    if (metadata.get("id") != RUN_ID
            or metadata.get("name") != "Four-mode prospective capture (research only)"
            or metadata.get("event") != "schedule"
            or metadata.get("head_branch") != "main"
            or metadata.get("head_sha") != RUN_HEAD_SHA
            or metadata.get("status") != "completed"
            or metadata.get("conclusion") != "success"):
        raise ValueError("untrusted_capture_run_provenance")


def _common_codes(publication, hole, observation, links):
    if (publication.get("outcome") != "pushed_to_main"
            or publication.get("commit_sha") != PUBLICATION_SHA
            or type(publication.get("added_forecasts")) is not int
            or publication["added_forecasts"] != EXPECTED_PUBLICATION
            or hole.get("publication_commit_sha") != PUBLICATION_SHA
            or observation.get("publication_commit_sha") != PUBLICATION_SHA
            or hole.get("published_new_count") != EXPECTED_PUBLICATION
            or observation.get("publication_count") != EXPECTED_PUBLICATION
            or hole.get("frozen_count") != EXPECTED_PUBLICATION
            or hole.get("validation_error_count") != 0
            or observation.get("observed_before_t_minus_12") != EXPECTED_PUBLICATION
            or observation.get("observed_after_t_minus_12") != 0
            or observation.get("unverified_count") != 0
            or links.get("checked") != EXPECTED_PUBLICATION
            or links.get("hashes_present") != EXPECTED_PUBLICATION
            or links.get("day_jst") != DAY):
        raise ValueError("actions_capture_batch_provenance_not_complete")
    records = [hole.get("records"), observation.get("records"), links.get("rows")]
    if any(type(rows) is not list or len(rows) != EXPECTED_PUBLICATION
           for rows in records):
        raise ValueError("invalid_capture_evidence_roster")
    sets = []
    for rows in records:
        if any(type(r) is not dict for r in rows):
            raise ValueError("malformed_capture_evidence_record")
        codes = [r.get("race_code") for r in rows]
        if (len(set(codes)) != len(codes)
                or any(type(c) is not str or not re.fullmatch(r"20261105[0-9]{4}", c)
                       for c in codes)):
            raise ValueError("duplicate_or_invalid_frozen_race_code")
        sets.append(set(codes))
    if sets[0] != sets[1] or sets[0] != sets[2]:
        raise ValueError("cross_artifact_race_roster_disagrees")
    if any(r.get("status") != "both_hashes_present"
           or r.get("matches") != {"race_cards": True, "title": True}
           or r.get("independent_source_authenticity_verified") is not False
           for r in links["rows"]):
        raise ValueError("untrusted_source_links")
    return sorted(sets[0])


def accumulate(scores):
    """Only same-race, separately preserved baseline/candidate TopN bits."""
    n = len(scores)
    if n != len({r["race_code"] for r in scores}):
        raise ValueError("duplicated_result_score")
    out = {}
    for top in TOPS:
        a = sum(r["topn"][top]["baseline"] is True for r in scores)
        b = sum(r["topn"][top]["candidate"] is True for r in scores)
        gain = sum(r["topn"][top]["gained"] is True for r in scores)
        loss = sum(r["topn"][top]["lost"] is True for r in scores)
        if b - a != gain - loss:
            raise ValueError("gain_loss_arithmetic_disagrees")
        out[top] = {"baseline_hits": a, "candidate_hits": b,
                    "gained": gain, "lost": loss, "net": gain - loss,
                    "on_result_available_denominator": n,
                    "baseline_pct_research_only": round(100 * a / n, 2) if n else None,
                    "candidate_pct_research_only": round(100 * b / n, 2) if n else None}
    return out


def run(main_root, evidence_dir, metadata_path, inspector=inspect_race):
    metadata = read_json(metadata_path, 30000)
    metadata_guard(metadata)
    evidence = Path(evidence_dir) / "four-mode-evidence"
    publication = read_json(evidence / "publication.json", 50000)
    shadow = read_json(evidence / "hole-shadow.json", 5000000)
    remote = read_json(evidence / "github-server-observation.json", 2000000)
    links = read_json(evidence / "source-links.json", 500000)
    codes = _common_codes(publication, shadow, remote, links)
    main_root = Path(main_root)

    @lru_cache(maxsize=2048)
    def cached_git(tuple_args):
        return subprocess.check_output(["git", *tuple_args], cwd=main_root,
                                       timeout=45)

    def git(args):
        return cached_git(tuple(args))

    # Materialize the full pre-result roster BEFORE ANY read of confirmed
    # finishes. Future first-300 cohort membership must be handled separately.
    pre = [
        inspector(code, main_root, publication, shadow, remote,
                  git=git, score_outcome=False)
        for code in codes
    ]
    rejected_pre = [x for x in pre if x.get("status") != PRE]
    if rejected_pre:
        return {"schema": "HOLE_NOV05_SAME_JOB_DIAGNOSTIC_V1",
                "status": "pre_result_evidence_rejected",
                "examined_capture_run_id": RUN_ID,
                "published": EXPECTED_PUBLICATION,
                "pre_result_consistent": len(pre) - len(rejected_pre),
                "pre_result_rejected": rejected_pre,
                "historical_paired_topn": None, "formal": False,
                "model_improvement_proven": False,
                "capture_run_inventory_exhaustive": False}
    frozen_roster = sorted(
        pre, key=lambda x: (x["deadline_jst"], x["race_code"]))
    frozen_digest = hashlib.sha256(
        json.dumps([{"race_code": row["race_code"],
                     "source_sha256": row["source_sha256"],
                     "baseline_top10": row["baseline_top10"],
                     "candidate_top10": row["candidate_top10"]}
                    for row in frozen_roster], sort_keys=True,
                   separators=(",", ":")).encode("ascii")).hexdigest()

    scored = [
        inspector(code, main_root, publication, shadow, remote,
                  git=git, score_outcome=True)
        for code in codes
    ]
    observed = [x for x in scored if x.get("status") == OK]
    pending = sorted(x["race_code"] for x in scored if x.get("status") == PENDING)
    invalid = [x for x in scored if x.get("status") not in (OK, PENDING)]
    if len(observed) + len(pending) + len(invalid) != EXPECTED_PUBLICATION:
        raise ValueError("captured_race_result_census_inconsistent")
    metrics = accumulate(observed) if observed and not invalid else None
    return {
        "schema": "HOLE_NOV05_SAME_JOB_DIAGNOSTIC_V1",
        "status": ("saved_candidate_result_comparison_research_only" if
                   metrics is not None else
                   "no_valid_result_comparison_or_invalid_evidence"),
        "capture_run_id": RUN_ID,
        "capture_run_event": "schedule",
        "capture_run_head_sha": RUN_HEAD_SHA,
        "publication_commit_sha": PUBLICATION_SHA,
        "published_frozen": EXPECTED_PUBLICATION,
        "pre_result_consistent": len(pre),
        "pre_result_roster_committed_before_results": False,
        "pre_result_ticket_roster_sha256": frozen_digest,
        "confirmed_result_content_scored": len(observed),
        "pending_result_codes": pending,
        "invalid_result_evidence": invalid,
        "paired_historical_topn": metrics,
        "per_race_result_diagnostic": observed,
        "formal": False, "remote_first_received_verified": False,
        "official_beforeinfo_six_boat_verified": False,
        "capture_run_inventory_exhaustive": False,
        "fixed_300_primary_study_complete": False,
        "study_efficacy_p_value": None,
        "model_improvement_proven": False,
        "production_forecast_changed": False,
        "warning": ("Archived actual before-T12 GitHub-server observation and same-job "
                    "saved shadow, but selected 106-run partial research cohort, "
                    "not a fully authenticated/committed first-300 roster. "
                    "No formal prediction accuracy or early efficacy claim.")
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--main-root", type=Path, required=True)
    parser.add_argument("--evidence-dir", type=Path, required=True)
    parser.add_argument("--capture-run-metadata", type=Path, required=True)
    parser.add_argument("--output", default="nov05_saved_hole_shadow_audit.json")
    args = parser.parse_args()
    result = run(args.main_root, args.evidence_dir,
                 args.capture_run_metadata)
    Path(args.output).write_text(
        json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8")
    print("NOV05_SAVED_HOLE_SHADOW=" + json.dumps({
        key: result.get(key) for key in
        ("status", "published_frozen", "pre_result_consistent",
         "confirmed_result_content_scored", "pending_result_codes",
         "paired_historical_topn", "fixed_300_primary_study_complete",
         "formal", "model_improvement_proven")
    }, ensure_ascii=False, sort_keys=True))
    return 0 if result["status"] == "saved_candidate_result_comparison_research_only" else 2


if __name__ == "__main__":
    raise SystemExit(main())

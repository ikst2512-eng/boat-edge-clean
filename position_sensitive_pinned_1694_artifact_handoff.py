"""PINNED read-only #1694 source audit artifact -> #1698 full-ledger join.

Offline consumer. No API calls made here: GitHub run/artifact JSON must be
independently fetched by the CI caller and the artifact downloaded by GitHub
Actions. Source metadata pins are *integrity hints*, NOT authentication of
individual official HTTP bytes or first forecast Git remote receipt.
Never counts a candidate toward 300+300 or opens confirmed results.
"""
import json
import hashlib
from pathlib import Path
import re

from position_sensitive_cross_pr_t12_bridge import (
    assess_cross_pr_blockers, _read_json_file,
)

SOURCE_RUN_ID = 42620400791
SOURCE_HEAD_SHA = "e46094a1cdccf8faa3661c401188d9bb746a0ab6"
SOURCE_WORKFLOW = ".github/workflows/audit-official-pair-schedule-continuity.yml"
SOURCE_ARTIFACT_ID = 13676360800
SOURCE_ARTIFACT_NAME = "official-pair-schedule-audit-42620400791"
SOURCE_ARTIFACT_DIGEST = (
    "sha256:acffef2d77d754df6ebf90db42d1301d10ac2bffe55241b4eff5d2618be32e73"
)
# Independently extracted from that exact full ZIP whose SHA matched the
# GitHub artifact digest. Pins the precise original report bytes, not JSON
# formatting, so a substituted syntactically valid report is rejected.
SOURCE_REPORT_SHA256 = "cc7e94e16ecb9535d5dfaac81f0f6248a8ec7bb375efbe0030cdd799386d638d"
REPO = "ikst2512-eng/boat-edge-clean"
SCHEMA = "POSITION_SENSITIVE_PINNED_1694_REAL_ARTIFACT_HANDOFF_V1"
SHA40 = re.compile(r"[0-9a-f]{40}\Z")


def _strict_metadata(run, artifact):
    """Reject wrong workflow/run/artifact. Not a cryptographic verifier."""
    if type(run) is not dict or type(artifact) is not dict:
        raise ValueError("missing_github_metadata")
    if (type(run.get("id")) is not int or run["id"] != SOURCE_RUN_ID
            or run.get("head_sha") != SOURCE_HEAD_SHA
            or run.get("path") != SOURCE_WORKFLOW
            or run.get("event") != "pull_request"
            or run.get("status") != "completed"
            or run.get("conclusion") != "success"
            or run.get("head_repository", {}).get("full_name") != REPO
            or run.get("repository", {}).get("full_name") != REPO):
        raise ValueError("source_ci_run_not_pinned_or_unsuccessful")
    wr = artifact.get("workflow_run")
    if (type(wr) is not dict or wr.get("id") != SOURCE_RUN_ID
            or wr.get("head_sha") != SOURCE_HEAD_SHA
            or artifact.get("id") != SOURCE_ARTIFACT_ID
            or artifact.get("name") != SOURCE_ARTIFACT_NAME
            or artifact.get("digest") != SOURCE_ARTIFACT_DIGEST
            or artifact.get("expired") is not False):
        raise ValueError("source_artifact_metadata_not_pinned")


def read_exact_pinned_report(path):
    """Refuse replacement of the original audited report even if schema matches."""
    path = Path(path)
    if path.is_symlink() or not path.is_file() or not 0 < path.stat().st_size <= 250_000:
        raise ValueError("unsafe_pinned_report_path")
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != SOURCE_REPORT_SHA256:
        raise ValueError("pinned_source_report_raw_sha256_mismatch")
    from position_sensitive_cross_pr_t12_bridge import _reject_duplicate_keys
    return json.loads(raw, object_pairs_hook=_reject_duplicate_keys)


def pinned_handoff(run, artifact, report, roster):
    """Audits exact candidate codes vs historical official-source *claims*."""
    _strict_metadata(run, artifact)
    if type(roster) is not dict or type(report) is not dict:
        raise ValueError("invalid_report_inputs")
    count = roster.get("candidate_files")
    rows = roster.get("rows")
    if (roster.get("schema") != "POSITION_SENSITIVE_ALL_CANDIDATE_LIVE_HTTP_ROSTER_V1"
            or roster.get("status") != "whole_remote_ledger_snapshot_observed_nonformal"
            or type(count) is not int or not 0 <= count <= 600
            or type(rows) is not list or len(rows) != count
            or roster.get("candidate_original_exact_replays") != count
            or roster.get("candidate_first_remote_receipts_independently_verified") != 0
            or roster.get("all_candidate_observations_externally_first_arrival_attested") is not False
            or roster.get("complete_capture_and_rescue_run_inventory_verified") is not False
            or roster.get("official_T12_beforeinfo_six_and_120_odds_verified") is not False
            or roster.get("formal") is not False
            or roster.get("promotion_allowed") is not False
            or roster.get("model_improvement_proven") is not False
            or roster.get("production_changed") is not False
            or type(roster.get("fetched_research_branch_tip")) is not str
            or not SHA40.fullmatch(roster["fetched_research_branch_tip"])):
        raise ValueError("untrusted_or_partial_candidate_roster")
    ids = []
    for row in rows:
        if (type(row) is not dict
                or row.get("original_and_candidate_ticket_replay") is not True
                or row.get("independent_first_remote_receipt_verified") is not False
                or row.get("formal") is not False
                or row.get("promotion_allowed") is not False
                or type(row.get("candidate_sha256")) is not str
                or not re.fullmatch(r"[a-f0-9]{64}", row["candidate_sha256"])
                or type(row.get("original_sha256")) is not str
                or not re.fullmatch(r"[a-f0-9]{64}", row["original_sha256"])
                or row.get("status") not in (
                    "deadline_cutoff_elapsed_no_new_observation_attempt",
                    "predeadline_read_only_live_observation_not_enabled",
                    "remote_existence_observed_preT12_not_first_receipt")):
            raise ValueError("invalid_original_candidate_row")
        ids.append(row.get("race_code"))
    joined = assess_cross_pr_blockers(report, ids)
    return {
        "schema": SCHEMA,
        "status": "pinned_github_audit_artifact_race_join_without_formal_certification",
        "source_workflow_run_id": SOURCE_RUN_ID,
        "source_code_head_sha": SOURCE_HEAD_SHA,
        "source_artifact_id": SOURCE_ARTIFACT_ID,
        "source_artifact_metadata_digest": SOURCE_ARTIFACT_DIGEST,
        "source_report_raw_sha256_expected_by_pinned_cli": SOURCE_REPORT_SHA256,
        "source_artifact_metadata_pins_self_consistent": True,
        "candidate_remote_branch_tip_self_recorded": roster["fetched_research_branch_tip"],
        "source_races_in_pinned_report": report["races_compared"],
        "candidate_rows": count,
        "matched_same_race_rows": joined["matched_upstream_race_codes"],
        "unmatched_candidate_rows": joined["unmatched_candidate_codes"],
        "candidate_blockers": joined["by_race"],
        "blocker_counts_non_exclusive": joined["blocker_counts_non_exclusive"],
        "source_report_individual_http_originals_replayed_by_this_consumer": False,
        "github_artifact_zip_digest_independently_computed_by_this_consumer": False,
        "new_candidate_independent_first_remote_receipts": 0,
        "candidate_capture_roster_truly_complete": False,
        "official_six_odds120_same_race_candidate_lineage_verified": False,
        "formal_pilot": 0,
        "formal_confirmation": 0,
        "outcomes_read": False,
        "formal": False,
        "model_improvement_proven": False,
        "promotion_allowed": False,
        "production_changed": False,
        "warning": (
            "A pinned successful CI artifact report does not itself attest "
            "individual original HTTP bytes, forecast generation after source, "
            "independent first candidate Git remote acceptance, or formal "
            "prospective scoring. Never combine sources from different races."
        ),
    }


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-run-json", required=True)
    parser.add_argument("--source-artifact-json", required=True)
    parser.add_argument("--source-report", required=True)
    parser.add_argument("--candidate-roster", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    run = _read_json_file(args.source_run_json, 150_000)
    artifact = _read_json_file(args.source_artifact_json, 60_000)
    report = read_exact_pinned_report(args.source_report)
    roster = _read_json_file(args.candidate_roster, 250_000)
    result = pinned_handoff(run, artifact, report, roster)
    path = Path(args.output)
    if path.is_symlink() or path.exists() or path.parent.is_symlink():
        raise ValueError("refusing_to_overwrite_or_follow_output_symlink")
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True)
                    + "\n", encoding="utf-8")
    print("PINNED_REAL_SOURCE_REPORT_CANDIDATE_RACE_JOIN=" +
          json.dumps({key: value for key, value in result.items()
                      if key not in ("candidate_blockers", "blocker_counts_non_exclusive")},
                     sort_keys=True))


if __name__ == "__main__":
    main()

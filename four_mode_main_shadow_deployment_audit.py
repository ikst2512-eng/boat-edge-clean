"""Read-only deployment gate: distinguish production V2 capture from Draft shadows.

Reads one pinned origin/main workflow and the checked-out Draft workflow bytes.
A green PR test job does not mean optional four-mode candidate stages ran on
main; even a deployed stage would not establish a first remote candidate receipt.
No result reads, no actions dispatch, no Git writes, no official source claims.
"""
import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

WORKFLOW = ".github/workflows/four-mode-prospective-capture.yml"
GIT_SHA = re.compile(r"[a-f0-9]{40}\Z")
EXPECTED_NAME = "name: Four-mode prospective capture (research only)"
STEP_ORIGINAL = "Capture predeadline records"
STEP_FREEZE = "Freeze all four-mode research candidates from published original"
STEP_LEDGER = "Preserve four-mode candidates on existing write-once Git evidence branch"
STEP_REMOTE = "Observe first-add forecast bytes with GitHub API server Date"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def stages(raw):
    if type(raw) is not bytes or not 0 < len(raw) < 100_000:
        raise ValueError("missing_or_oversized_workflow")
    try:
        source = raw.decode("utf-8")
    except UnicodeError as exc:
        raise ValueError("non_utf8_workflow") from exc
    if (not source.startswith(EXPECTED_NAME + "\n")
            or "  capture:\n" not in source
            or "github.ref == 'refs/heads/main'" not in source
            or "github.event_name == 'pull_request'" not in source):
        raise ValueError("capture_workflow_identity_or_main_guard_drift")
    rows = re.findall(r"^\s{6}- name: (.+?)\s*$", source, flags=re.MULTILINE)
    for name in (STEP_ORIGINAL, STEP_FREEZE, STEP_LEDGER, STEP_REMOTE):
        if rows.count(name) > 1:
            raise ValueError("duplicated_capture_stage:" + name)
    if STEP_ORIGINAL not in rows or STEP_REMOTE not in rows:
        raise ValueError("base_capture_stage_missing")
    freeze = STEP_FREEZE in rows
    ledger = STEP_LEDGER in rows
    if freeze != ledger:
        raise ValueError("partial_candidate_pipeline_never_assume_deployed")
    # Only explicit names + exact stage script and output paths count as wired.
    if freeze and (
            "run: python four_mode_all_mode_same_job_shadow.py" not in source
            or "run: python four_mode_all_shadow_durable_ledger.py" not in source
            or "four-mode-evidence/all-mode-shadow.json" not in source
            or "four-mode-evidence/all-mode-shadow-ledger.json" not in source):
        raise ValueError("candidate_pipeline_wiring_incomplete")
    return {"original_capture_stage_present": True,
            "original_github_observation_stage_present": True,
            "all_mode_candidate_freeze_stage_present": freeze,
            "all_mode_candidate_ledger_stage_present": ledger,
            "candidate_pipeline_wired": freeze and ledger,
            "workflow_sha256": digest(raw)}


def review(main_workflow, draft_workflow, main_sha, draft_sha):
    if (type(main_sha) is not str or type(draft_sha) is not str
            or not GIT_SHA.fullmatch(main_sha)
            or not GIT_SHA.fullmatch(draft_sha)):
        raise ValueError("unpinned_workflow_commit")
    main = stages(main_workflow)
    draft = stages(draft_workflow)
    status = ("main_candidate_stages_present_execution_and_receipt_unverified"
              if main["candidate_pipeline_wired"] else
              "draft_candidate_stages_not_deployed_on_main")
    return {
        "schema": "FOUR_MODE_MAIN_VS_DRAFT_CANDIDATE_PIPELINE_V1",
        "main_commit_sha": main_sha, "draft_commit_sha": draft_sha,
        "workflow_path": WORKFLOW,
        "main": main, "draft": draft,
        "status": status,
        "main_candidate_stages_deployed_in_source": main["candidate_pipeline_wired"],
        "draft_candidate_stages_available_for_manual_review": draft["candidate_pipeline_wired"],
        "live_candidate_step_execution_verified": False,
        "independent_first_remote_candidate_receipt_verified": False,
        "official_racelist_beforeinfo_odds_120_verified": False,
        "complete_capture_attempt_inventory_verified": False,
        "formal": False, "admitted_prospective_pairs": 0,
        "model_improvement_proven": False, "model_promotion_allowed": False,
        "warning": "A Draft/PR check never runs its privileged main capture job. "
                   "Workflow stage presence does not establish actual execution, "
                   "official source completeness or independently first-seen candidate.",
    }


def git(*args):
    return subprocess.check_output(["git", *args], timeout=40)


def audit_live(main_ref="refs/remotes/origin/main", draft_ref="HEAD"):
    if (main_ref != "refs/remotes/origin/main"
            or (draft_ref != "HEAD" and not GIT_SHA.fullmatch(draft_ref))):
        raise ValueError("unsafe_nonpinned_workflow_ref")
    main_sha = git("rev-parse", "--verify", main_ref + "^{commit}").decode().strip()
    draft_sha = git("rev-parse", "--verify", draft_ref + "^{commit}").decode().strip()
    if not GIT_SHA.fullmatch(main_sha) or not GIT_SHA.fullmatch(draft_sha):
        raise ValueError("unverifiable_commit")
    main = git("show", main_sha + ":" + WORKFLOW)
    draft = git("show", draft_sha + ":" + WORKFLOW)
    report = review(main, draft, main_sha, draft_sha)
    report["draft_verified_at_exact_pr_head_sha"] = draft_ref != "HEAD"
    report["draft_source_warning"] = (
        "Exact PR head commit selected by caller and read via git show"
        if draft_ref != "HEAD" else
        "HEAD can be a GitHub PR synthetic merge checkout, not the real PR head")
    return report


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--output", type=Path)
    p.add_argument("--draft-sha", help="Exact GitHub PR-head commit SHA after fetching it")
    args = p.parse_args()
    result = audit_live(draft_ref=args.draft_sha or "HEAD")
    data = json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    if args.output:
        args.output.write_text(data, encoding="utf-8")
    print("FOUR_MODE_CANDIDATE_DEPLOYMENT_GATE=" + json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()

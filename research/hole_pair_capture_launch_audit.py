"""Read-only capture launch audit for Draft #1685.

A passing PR CI does not mean manual research capture can run. GitHub
workflow_dispatch requires that its workflow file exist on the default branch.
Never dispatch, collect, load outcomes, or infer independent first receipt here.
"""
import argparse
import json
import re
import subprocess

WORKFLOW = ".github/workflows/hole-future-pair-precommit.yml"
SCHEMA = "HOLE_PAIR_CAPTURE_LAUNCH_READINESS_V1"
REF = re.compile(r"[A-Za-z0-9_./-]+\Z")


def audit(default_tree_paths, main_sha):
    """Pure non-authorizing status for exact paths IN THE DEFAULT-BRANCH TREE."""
    if not isinstance(default_tree_paths, (list, tuple, set)) or any(
        type(path) is not str for path in default_tree_paths
    ):
        raise ValueError("invalid_default_tree_paths")
    if type(main_sha) is not str or not re.fullmatch(r"[0-9a-f]{40}", main_sha):
        raise ValueError("invalid_main_sha")
    registered = WORKFLOW in set(default_tree_paths)
    return {
        "schema": SCHEMA,
        "main_sha": main_sha,
        "default_branch_workflow_present": registered,
        "workflow_dispatch_registration": (
            "default_branch_workflow_file_present_not_proof_of_manual_access"
            if registered else "blocked_workflow_missing_from_default_branch"
        ),
        "default_branch_dispatch_prerequisite_satisfied": registered,
        "capture_run_executed_by_this_audit": False,
        "candidate_artifact_created_by_this_audit": False,
        "independent_first_candidate_receipt_verified": False,
        "official_t12_complete_verified": False,
        "eligible_formal_cohort_started_proven": False,
        "formal": False,
        "model_improvement_proven": False,
        "production_promotion_allowed": False,
        "main_or_production_modified": False,
        "blockers": (
            ([] if registered else ["workflow_dispatch_not_registered_on_default_branch"])
            + ["external_first_receipt_not_verified_by_this_audit",
               "official_t12_complete_not_verified_by_this_audit",
               "no_prospective_capture_or_eligibility_proven_by_this_audit"]
        ),
        "next_action": (
            "Manual architecture review of a separately authorized research-only "
            "dispatch path, independent candidate first-acceptance proof and "
            "official T-12 evidence; never merge main automatically."
        ),
    }


def _git(*args):
    return subprocess.check_output(
        ["git", *args], text=True, stderr=subprocess.PIPE
    ).strip()


def audit_git_default(default_ref):
    """Examine actual ref contents, not the PR tree or a self-reported flag."""
    if (type(default_ref) is not str or not REF.fullmatch(default_ref)
            or default_ref.startswith("-") or ".." in default_ref):
        raise ValueError("invalid_default_ref")
    sha = _git("rev-parse", "--verify", default_ref + "^{commit}")
    matches = _git("ls-tree", "--name-only", "-r", default_ref, "--", WORKFLOW)
    paths = [p for p in matches.splitlines() if p]
    if paths and paths != [WORKFLOW]:
        raise ValueError("unexpected_default_tree_result")
    return audit(paths, sha)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--default-ref", required=True)
    args = parser.parse_args()
    print(json.dumps(audit_git_default(args.default_ref),
                     sort_keys=True, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

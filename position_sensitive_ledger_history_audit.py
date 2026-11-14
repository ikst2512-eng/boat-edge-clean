"""Audit research-only position-sensitive ledger history; NEVER certify hits.

Standalone Git history verifier: linear descendant of a pinned main bootstrap,
only create-only candidate paths, exact first-added content still at branch tip.
It NEVER publishes, edits, dispatches, reads results or certifies first
remote receipt. A force-rewritten remote history could escape a single-current-
tip inspection: independent immutable witness is a separate requirement.
"""
import json
from pathlib import Path
import re
import subprocess

from position_sensitive_append_only_research import _no_duplicate_keys
from four_mode_position_sensitive_forward import (
    CODE, DATE_START, DATE_END, PROTOCOL_BLOB_SHA1, _verify_snapshot, protocol,
)

BASE = "6b371040fd2fc4398bfa882e6557c333cc0800c8"
LEDGER_BRANCH = "position-sensitive-forward-evidence-ledger"
README = "position_sensitive_research/README.md"
RECORD_PATTERN = re.compile(r"position_sensitive_research/(20[0-9]{10})\.json\Z")
SHA = re.compile(r"[0-9a-f]{40}\Z")
SCHEMA = "POSITION_SENSITIVE_LEDGER_LINEAR_HISTORY_AUDIT_V1"
MAX_COMMITS = 1500
MAX_CANDIDATES = 600


def _run(root, *argv):
    return subprocess.check_output(
        ["git", *argv], cwd=root, timeout=25, stderr=subprocess.DEVNULL)


def audit_ledger(root, branch_ref, base=BASE, git=None, original_read=None):
    """Read only local Git history (can be an independently fetched remote ref).

    Supplied original_read must itself come from independently authenticated
    exact archive bytes. Otherwise zero candidate evidence is certified.
    """
    if (type(branch_ref) is not str or not branch_ref
            or branch_ref.startswith("-") or type(base) is not str
            or SHA.fullmatch(base) is None):
        raise ValueError("unsafe_git_ref_or_bootstrap")
    run = git or (lambda *args: _run(Path(root), *args))
    try:
        tip = run("rev-parse", "--verify", branch_ref+"^{commit}").decode().strip()
        actual_base = run("rev-parse", "--verify", base+"^{commit}").decode().strip()
    except (subprocess.CalledProcessError, UnicodeError) as exc:
        raise ValueError("missing_git_branch_or_base") from exc
    if (SHA.fullmatch(tip) is None or actual_base != base
            or tip == base):
        raise ValueError("invalid_ledger_tip_or_base")
    try:
        run("merge-base", "--is-ancestor", base, tip)
    except subprocess.CalledProcessError as exc:
        raise ValueError("ledger_not_descended_from_bootstrap") from exc
    commits = run("rev-list", "--reverse", "--first-parent",
                  base+".."+tip).decode().splitlines()
    if not 1 <= len(commits) <= MAX_COMMITS:
        raise ValueError("ledger_commit_count_invalid")
    seen = set()
    readme_seen = False
    candidate_count = 0
    originally_replayed = 0
    previous = base
    p = protocol()
    for commit in commits:
        if SHA.fullmatch(commit) is None:
            raise ValueError("invalid_history_commit")
        parents = run("rev-list", "--parents", "-n", "1", commit).decode().split()
        if parents != [commit, previous]:
            raise ValueError("ledger_merge_or_non_linear_commit")
        changes = run("diff-tree", "--no-commit-id", "--name-status",
                      "-r", commit).decode().splitlines()
        if not changes:
            raise ValueError("empty_ledger_commit")
        for item in changes:
            chunks = item.split("\t")
            if len(chunks) != 2 or chunks[0] != "A":
                raise ValueError("ledger_update_delete_rename_forbidden")
            path = chunks[1]
            match = RECORD_PATTERN.fullmatch(path)
            if path != README and match is None:
                raise ValueError("unapproved_ledger_change_path")
            if path in seen:
                raise ValueError("repeated_ledger_path")
            seen.add(path)
            if path == README:
                readme_seen = True
            else:
                candidate_count += 1
                if candidate_count > MAX_CANDIDATES:
                    raise ValueError("too_many_candidate_races")
                code = match.group(1)
                if (CODE.fullmatch(code) is None
                        or not DATE_START[:10].replace("-", "") <= code[:8] <=
                        DATE_END[:10].replace("-", "")):
                    raise ValueError("candidate_race_outside_registered_period")
            try:
                exact = run("show", commit+":"+path)
                current = run("show", tip+":"+path)
            except (subprocess.CalledProcessError, OSError) as exc:
                raise ValueError("first_add_blob_mutated_or_invalid") from exc
            if (exact != current or
                    (path == README and not 0 < len(exact) < 20000) or
                    (path != README and not 0 < len(exact) <= 30000)):
                raise ValueError("first_add_blob_mutated_or_invalid")
            if match is not None:
                try:
                    record = json.loads(exact, object_pairs_hook=_no_duplicate_keys)
                except (ValueError, TypeError) as exc:
                    raise ValueError("candidate_json_invalid") from exc
                if (type(record) is not dict
                        or record.get("race_code") != code
                        or record.get("protocol_git_blob_sha1") != PROTOCOL_BLOB_SHA1
                        or record.get("candidate_selector_git_blob_sha1") !=
                        p["candidate_selector_git_blob_sha1"]
                        or record.get("status") != "local_only_unpublished"
                        or record.get("formal") is not False
                        or record.get("candidate_first_remote_receipt_verified") is not False
                        or any(name in record for name in
                               ("finish_order", "winning_ticket", "payout", "results"))):
                    raise ValueError("untrusted_candidate_forecast_record")
                if original_read is not None:
                    source = original_read(code)
                    if type(source) is not bytes:
                        raise ValueError("original_bytes_missing")
                    try:
                        _verify_snapshot(record, source, p)
                    except (KeyError, ValueError, TypeError) as exc:
                        raise ValueError("candidate_original_replay_failed") from exc
                    originally_replayed += 1
        previous = commit
    if not readme_seen:
        raise ValueError("ledger_bootstrap_readme_missing")
    return {
        "schema": SCHEMA,
        "status": "linear_create_only_history_local_git_view_only",
        "base_commit_sha": base,
        "observed_branch_commit_sha": tip,
        "recorded_first_add_commits_after_bootstrap": len(commits),
        "candidate_files": candidate_count,
        "candidate_original_exact_replays": originally_replayed,
        "candidate_first_remote_receipts_independently_verified": 0,
        "branch_tip_is_independently_pinned": False,
        "remote_history_rewrite_excluded": False,
        "complete_capture_run_inventory_verified": False,
        "all_official_T12_inputs_verified": False,
        "formal": False,
        "promotion_allowed": False,
        "model_improvement_proven": False,
        "production_changed": False,
        "warning": (
            "Linear create-only history is only an inspection of one Git tip. "
            "Does NOT exclude a force-push before observation. Candidate files, "
            "if any, are NOT authenticated first remote pre-T12 receipts. "
            "A separate independent append-only timestamp witness, complete "
            "capture run inventory, official 6/120 sources and outcomes "
            "are still necessary."
        ),
    }


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--branch-ref", default=None)
    parser.add_argument("--original-ref", default=None,
                        help="Read-only exact V2 replay from origin/main; no results")
    args = parser.parse_args()
    if args.original_ref is not None and args.original_ref != "refs/remotes/origin/main":
        raise SystemExit("only_read_only_origin_main_original_ref_allowed")
    if args.branch_ref is None:
        print(json.dumps({
            "schema": SCHEMA,
            "status": "no_fetched_remote_ref_provided",
            "candidate_first_remote_receipts_independently_verified": 0,
            "formal": False, "promotion_allowed": False,
            "production_changed": False,
        }, sort_keys=True))
    else:
        def read_original(code):
            if CODE.fullmatch(code) is None:
                raise ValueError("unsafe_original_race_code")
            try:
                return _run(Path("."), "show",
                            args.original_ref + ":four_mode_forecasts/" + code + ".json")
            except (subprocess.CalledProcessError, OSError) as exc:
                raise ValueError("original_main_git_bytes_missing") from exc
        evidence = audit_ledger(
            Path("."), args.branch_ref,
            original_read=(read_original if args.original_ref else None))
        if args.original_ref is not None and (
                evidence["candidate_original_exact_replays"] != evidence["candidate_files"]):
            raise ValueError("not_all_candidates_reproduced_from_original_main")
        print(json.dumps(evidence, sort_keys=True))

"""Operator-only, OFFLINE signed-F prospective research source preflight.

This is intentionally a dry-run: no network access, no Git writer, no
background schedule, no result/payout read, and no local candidate file
is written. A separately reviewed create-only first-add witness is still
needed before any independent 300+300 accuracy sample can be admitted.

Only invoke with SAME-RACE saved official original directories received
before race T-12 and the *exact pinned* #1698 source file.
"""
import argparse
from datetime import datetime, timedelta, timezone
import importlib.util
import json
import os
from pathlib import Path
import sys

from scenario_future_local_candidate_handoff import _git_blob_sha1
from scenario_signed_st_future_pre_t12_handoff import run_one_shot_unpublished

PINNED_1698_SHA1="0019978a4e27a1235d0b466c11f514bd7105f261"
JST=timezone(timedelta(hours=9))


def load_reviewed_1698(file_path):
    p=Path(file_path)
    if (p.is_symlink() or not p.is_file()
            or not 0<p.stat().st_size<=100_000
            or _git_blob_sha1(p.read_bytes())!=PINNED_1698_SHA1
            or "position_sensitive_conditioned_lab" in sys.modules):
        raise ValueError("signed_F_cli_requires_exact_unloaded_1698_file")
    spec=importlib.util.spec_from_file_location("position_sensitive_conditioned_lab",str(p))
    if spec is None or spec.loader is None:
        raise ValueError("signed_F_cli_external_reviewed_parser_unavailable")
    module=importlib.util.module_from_spec(spec)
    sys.modules[spec.name]=module
    spec.loader.exec_module(module)
    return module.experimental_conditional_board


def operator_dry_run(card_dir,before_dir,odds_dir,pinned_1698_path):
    # An actual operator execution uses ONLY the current machine's UTC clock
    # converted to JST. No user-overridable --generated-at / --deadline flags.
    # This still is NOT an independent GitHub time witness.
    callback=load_reviewed_1698(pinned_1698_path)
    prepared=run_one_shot_unpublished(
        card_dir,before_dir,odds_dir,callback,
        lambda:datetime.now(JST))
    return {
        "schema":"SIGNED_F_FOUR_MODE_ONE_SHOT_DRYRUN_REPORT_V1",
        "race_code":prepared["race_code"],
        "candidate_path_if_future_writer_approved":prepared["path"],
        "candidate_content_sha256":prepared["sha256"],
        "candidate_git_blob_sha1":prepared["git_blob_sha1"],
        "candidate_length_bytes":len(prepared["bytes"]),
        "offline_source_and_math_pinned":True,
        "status":prepared["status"],
        "candidate_bytes_emitted":False,
        "candidate_file_written":False,
        "github_put_attempted":False,
        "candidate_first_remote_receipt_verified":False,
        "eligible_for_future_300_plus_300":False,
        "formal":False,
        "production_changed":False,
        "warning":"Dry-run alone is NOT a saved forecast or eligible prospective accuracy sample."
    }


def main():
    parser=argparse.ArgumentParser(description="Signed-F prospective T-12 research DRY-RUN only")
    parser.add_argument("--card-dir",required=True)
    parser.add_argument("--before-dir",required=True)
    parser.add_argument("--odds-dir",required=True)
    parser.add_argument("--pinned-1698-file",required=True)
    args=parser.parse_args()
    report=operator_dry_run(args.card_dir,args.before_dir,
                            args.odds_dir,args.pinned_1698_file)
    print(json.dumps(report,sort_keys=True,ensure_ascii=False))


if __name__=="__main__":
    main()

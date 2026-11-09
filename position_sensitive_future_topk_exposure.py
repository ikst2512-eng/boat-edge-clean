"""Outcome-blind, per-race future position-sensitive paired TopK exposure.

Never reads confirmed outcomes/payouts; no hit rates or production adoption.
Compares exact independent original V2 bytes to candidate's frozen 2nd/3rd
conditional ranking for every race in the existing research-only ledger.
"""
import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import re
import subprocess

from four_mode_position_sensitive_forward import CODE, DATE_START, DATE_END, MODES, TOPS, _verify_snapshot, protocol
from position_sensitive_append_only_research import _no_duplicate_keys

SCHEMA = "POSITION_SENSITIVE_FUTURE_PAIRED_TOPK_EXPOSURE_V1"
LEDGER = "refs/remotes/origin/position-sensitive-forward-evidence-ledger"
ORIGINAL = "refs/remotes/origin/main"
PREFIX = "position_sensitive_research/"
README = PREFIX + "README.md"
SHA40 = re.compile(r"[a-f0-9]{40}\Z")
MAX_CANDIDATES = 600


def compare_ticket_sets(snapshot, original_bytes):
    if type(snapshot) is not dict or type(original_bytes) is not bytes:
        raise ValueError("invalid_future_pair")
    checked = _verify_snapshot(snapshot, original_bytes, protocol())
    by_mode = {}
    for mode, budget in MODES.items():
        before = checked["baseline"][mode]
        after = checked["candidate"][mode]
        if len(before) != budget or len(after) != budget:
            raise ValueError("mode_budget_changed")
        topn = {}
        for k in TOPS:
            if k > budget:
                topn[str(k)] = {
                    "applicable": False,
                    "mode_ticket_budget": budget,
                    "reason": "ticket_budget_below_requested_topn",
                }
                continue
            b, a = before[:k], after[:k]
            retained = len(set(b) & set(a))
            dropped = k - retained
            topn[str(k)] = {
                "applicable": True,
                "ordered_rank_changed": b != a,
                "ticket_membership_changed": dropped > 0,
                "retained_old_tickets": retained,
                "replaced_ticket_slots": dropped,
                "original_top1_retained": before[0] in a,
                "candidate_top1_in_original_topk": after[0] in b,
            }
        by_mode[mode] = {
            "baseline_top1": before[0],
            "candidate_top1": after[0],
            "top1_changed": before[0] != after[0],
            "top1_first_boat_changed": before[0][0] != after[0][0],
            "top1_second_boat_changed": before[0][2] != after[0][2],
            "top1_third_boat_changed": before[0][4] != after[0][4],
            "topn": topn,
        }
    return {"race_code": checked["code"], "by_mode": by_mode}


def _git(*args):
    return subprocess.check_output(["git", *args], timeout=30,
                                   stderr=subprocess.DEVNULL)


def audit_future_ledger(git, ledger_ref=LEDGER, original_ref=ORIGINAL):
    if (not callable(git) or ledger_ref != LEDGER or original_ref != ORIGINAL):
        raise ValueError("unapproved_git_refs_or_io")
    tip = git("rev-parse", "--verify", ledger_ref + "^{commit}").decode().strip()
    if SHA40.fullmatch(tip) is None:
        raise ValueError("unverified_research_tip")
    roster = git("ls-tree", "-r", "--name-only", tip, "--", PREFIX).decode().splitlines()
    if (README not in roster or len(roster) != len(set(roster))):
        raise ValueError("missing_bootstrap_or_duplicate_candidate")
    names = sorted(x for x in roster if x != README)
    if len(names) > MAX_CANDIDATES:
        raise ValueError("future_candidate_roster_overflow")
    for name in names:
        if not name.startswith(PREFIX) or not name.endswith(".json"):
            raise ValueError("unknown_future_candidate_path")
        code = name[len(PREFIX):-5]
        if (CODE.fullmatch(code) is None or
                not DATE_START[:10].replace("-", "") <= code[:8] <= DATE_END[:10].replace("-", "")):
            raise ValueError("invalid_future_race_code")
    rows = []
    for name in names:
        code = name[len(PREFIX):-5]
        exact = git("show", tip + ":" + name)
        original = git("show", original_ref + ":four_mode_forecasts/" + code + ".json")
        if (type(exact) is not bytes or type(original) is not bytes
                or not 0 < len(exact) <= 30000 or not 0 < len(original) <= 30000):
            raise ValueError("unsafe_git_blob")
        frozen = json.loads(exact, object_pairs_hook=_no_duplicate_keys)
        comparison = compare_ticket_sets(frozen, original)
        comparison["candidate_sha256"] = hashlib.sha256(exact).hexdigest()
        comparison["original_sha256"] = hashlib.sha256(original).hexdigest()
        rows.append(comparison)
    summary = {}
    for mode, budget in MODES.items():
        summary[mode] = {
            "top1_changed_races": sum(r["by_mode"][mode]["top1_changed"] for r in rows),
            "top1_first_boat_changed_races": sum(
                r["by_mode"][mode]["top1_first_boat_changed"] for r in rows),
            "topk_membership_changed_races": {},
            "topk_ordered_changed_races": {},
            "topk_replaced_ticket_slots": {},
        }
        for k in TOPS:
            if k > budget:
                summary[mode]["topk_membership_changed_races"][str(k)] = None
                summary[mode]["topk_ordered_changed_races"][str(k)] = None
                summary[mode]["topk_replaced_ticket_slots"][str(k)] = None
            else:
                metric = [r["by_mode"][mode]["topn"][str(k)] for r in rows]
                summary[mode]["topk_membership_changed_races"][str(k)] = sum(
                    m["ticket_membership_changed"] for m in metric)
                summary[mode]["topk_ordered_changed_races"][str(k)] = sum(
                    m["ordered_rank_changed"] for m in metric)
                summary[mode]["topk_replaced_ticket_slots"][str(k)] = sum(
                    m["replaced_ticket_slots"] for m in metric)
    return {
        "schema": SCHEMA,
        "status": "future_research_candidate_outcome_blind_exposure_only",
        "fetched_ledger_tip": tip,
        "candidate_files": len(names),
        "same_race_pairs_validated": len(rows),
        "rows": rows,
        "by_mode": summary,
        "outcome_files_read": 0,
        "actual_hit_rates_calculated": False,
        "candidate_first_remote_receipts_independently_verified": 0,
        "formal": False,
        "model_improvement_proven": False,
        "promotion_allowed": False,
        "production_changed": False,
        "warning": (
            "Paired ticket rank and membership changes are NOT correctness "
            "or hit-rate improvement. Candidate first remote receipt, official "
            "six/120 and complete run inventory remain separate gates; "
            "never infer from source SHA or one current branch tip."
        ),
    }


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--ledger-ref", default=None)
    p.add_argument("--original-ref", default=None)
    p.add_argument("--output", type=Path)
    args=p.parse_args()
    if args.ledger_ref is None and args.original_ref is None:
        report = {
            "schema": SCHEMA, "status": "no_future_git_roster_provided",
            "candidate_files": 0, "formal": False,
            "promotion_allowed": False, "production_changed": False,
        }
    else:
        report = audit_future_ledger(_git, args.ledger_ref, args.original_ref)
    payload = json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    if args.output:
        if args.output.is_symlink() or args.output.exists():
            raise ValueError("output_must_be_new_non_symlink")
        args.output.write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")


if __name__ == "__main__":
    main()

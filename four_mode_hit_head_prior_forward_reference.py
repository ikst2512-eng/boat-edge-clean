"""HIT winner-head prior: reference-only prospective paired scorer.

A report with local timestamps is NEVER proof of independent first remote
receipt. Validate *all* supplied frozen candidate batches before any result
read. No discovery-period outcomes, no backfilled candidate slots, no writes
to production, and no automatic promotion.
"""
import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

from four_mode_all_mode_same_job_shadow import SIZES, VERSION, at_jst
from four_mode_top1_head_prior_shadow import RULE, choose
from four_mode_top1_forward_reference import _safe_result

POLICY_PATH = Path(__file__).resolve().parent / (
    "research/four_mode_hit_head_prior_forward_protocol_20261108.json")
START = "2026-11-09T00:00:00+09:00"
END = "2026-12-31T23:59:59+09:00"
PILOT = 300
CONFIRM = 300
TOPS = (1, 3, 5, 10)
BATCH_SCHEMA = "HIT_HEAD_PRIOR_LOCAL_FROZEN_REFERENCE_BATCH_V1"


def git_blob(raw):
    return hashlib.sha1(
        b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw
    ).hexdigest()


def policy():
    """Verify the unchanged result-blind selector and all frozen dependencies."""
    obj = json.loads(POLICY_PATH.read_bytes())
    if (type(obj) is not dict
            or obj.get("schema") !=
                "FOUR_MODE_HIT_WINNER_HEAD_PRIOR_FORWARD_PREREGISTRATION_V1"
            or obj.get("policy_id") != RULE
            or obj.get("registered_jst_date") != "2026-11-08"
            or obj.get("selector_file") != "four_mode_top1_head_prior_shadow.py"
            or obj.get("eligible_deadline_start_jst") != START
            or obj.get("eligible_deadline_end_jst") != END
            or obj.get("selection_order") !=
                "deadline_jst_then_race_code_no_outcome_backfill"
            or obj.get("primary_metric") !=
                "paired_HIT_Top1_exact_trifecta_original_versus_head_prior_shadow"
            or obj.get("pilot_races") != PILOT
            or obj.get("confirmation_races") != CONFIRM
            or obj.get("formal_count") != 0
            or obj.get("model_improvement_proven") is not False
            or obj.get("promotion_allowed") is not False
            or obj.get("authorization_required_for_live_collection") is not True):
        raise ValueError("head_prior_forward_policy_drift")
    deps = obj.get("pinned_dependency_git_blob_sha1")
    expected = {"research_model.py", "clean_four_modes.py",
                "four_mode_all_mode_same_job_shadow.py"}
    if not isinstance(deps, dict) or set(deps) != expected:
        raise ValueError("missing_head_prior_dependencies")
    root = POLICY_PATH.parent.parent
    for file, pin in {
            obj["selector_file"]: obj.get("pinned_selector_git_blob_sha1"),
            **deps}.items():
        source = root / file
        if source.is_symlink() or git_blob(source.read_bytes()) != pin:
            raise ValueError("head_prior_selector_or_dependency_drift:" + file)
    return obj


def canonical(obj):
    return json.dumps(obj, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":")).encode("utf-8")


def validate_before_results(batches, root):
    """Only supplied inventory is checked, NEVER completeness of actual runs."""
    proto = policy()
    if type(batches) is not list:
        raise ValueError("invalid_batch_inventory")
    root = Path(root)
    selected = []
    seen = set()
    ineligible = []
    for batch in batches:
        if (type(batch) is not dict or batch.get("schema") != BATCH_SCHEMA
                or batch.get("selector_git_blob_sha1") !=
                    proto["pinned_selector_git_blob_sha1"]
                or batch.get("candidate_first_remote_receipt_verified") is not False
                or batch.get("formal") is not False
                or batch.get("status") != "local_candidate_frozen_reference_only"
                or type(batch.get("records")) is not list):
            raise ValueError("invalid_or_forged_head_prior_batch")
        for row in batch["records"]:
            if type(row) is not dict:
                raise ValueError("invalid_head_prior_record")
            code = row.get("race_code")
            if (type(code) is not str or len(code) != 12 or not code.isdigit()
                    or not 1 <= int(code[8:10]) <= 24
                    or not 1 <= int(code[10:]) <= 12 or code in seen):
                raise ValueError("duplicate_or_invalid_head_prior_race")
            seen.add(code)
            # Discovery dates are never admitted even if candidate and outcome
            # can be reconstructed with newly invented local timestamps.
            if code[:8] < "20261109":
                raise ValueError("pre_registered_discovery_date_not_eligible")
            if row.get("status") != "frozen_local_before_T_minus_12_research_only":
                ineligible.append(code)
                continue
            path = root / "four_mode_forecasts" / (code + ".json")
            if path.is_symlink() or not path.is_file() or path.stat().st_size > 30000:
                raise ValueError("missing_or_unsafe_frozen_original")
            data = path.read_bytes()
            if hashlib.sha256(data).hexdigest() != row.get("original_sha256"):
                raise ValueError("original_archived_blob_mismatch")
            raw = json.loads(data)
            if (raw.get("race_code") != code or raw.get("model_version") != VERSION):
                raise ValueError("wrong_original_race_or_model_version")
            deadline = at_jst(raw["deadline_jst"])
            generated = at_jst(raw["generated_at_jst"])
            freeze = at_jst(row["candidate_frozen_at_jst"])
            received = [at_jst(raw[k]) for k in
                        ("source_title_received_jst", "source_cards_received_jst")]
            if (not at_jst(START) <= deadline <= at_jst(END)
                    or deadline.strftime("%Y%m%d") != code[:8]
                    or any(t > generated for t in received)
                    or not generated < freeze
                    or not freeze < deadline -
                        __import__("datetime").timedelta(minutes=12)
                    or row.get("deadline_jst") != raw["deadline_jst"]
                    or row.get("original_generated_at_jst") !=
                        raw["generated_at_jst"]):
                raise ValueError("head_prior_original_candidate_chronology")
            proposal = choose(raw)  # Exact saved V2 replay; NO result lookup
            if (row.get("candidate") != proposal
                    or hashlib.sha256(canonical(proposal)).hexdigest()
                       != row.get("candidate_sha256")
                    or proposal["candidate_first_remote_receipt_verified"] is not False):
                raise ValueError("head_prior_saved_candidate_not_reproducible")
            old, new = proposal["original"], proposal["candidate"]
            if (set(old) != set(SIZES) or set(new) != set(SIZES)
                    or any(old[mode] != new[mode] for mode in SIZES if mode != "hit")
                    or len(new["hit"]) != SIZES["hit"]
                    or len(set(new["hit"])) != SIZES["hit"]):
                raise ValueError("head_prior_mode_or_count_drift")
            selected.append({"code": code, "deadline": deadline,
                             "original": old["hit"], "candidate": new["hit"]})
    if ineligible:
        # If a missing/late candidate is ignored, selecting a later successful
        # candidate is outcome-independent but still survivor bias.
        raise ValueError("incomplete_head_prior_cohort_no_backfill")
    return sorted(selected, key=lambda x: (x["deadline"], x["code"]))


def blank():
    return {f"top{n}": {"original": 0, "candidate": 0, "gained": 0,
                        "lost": 0, "denominator": 0,
                        "original_pct": None, "candidate_pct": None}
            for n in TOPS}


def compare(batches, root):
    frozen = validate_before_results(batches, root)
    cohort = frozen[:PILOT + CONFIRM]
    phases = {"pilot": blank(), "confirmation": blank()}
    statuses = {"pilot": Counter(), "confirmation": Counter()}
    pending, invalid = [], []
    first_head = {"pilot": {"original": Counter(), "candidate": Counter()},
                  "confirmation": {"original": Counter(), "candidate": Counter()}}
    # RESULT READS FIRST BEGIN HERE, after ALL supplied candidates are replayed
    for i, row in enumerate(cohort):
        phase = "pilot" if i < PILOT else "confirmation"
        status, winning = _safe_result(Path(root), row["code"], row["deadline"])
        statuses[phase][status] += 1
        if status == "pending":
            pending.append(row["code"])
            continue
        if status == "invalid":
            invalid.append(row["code"])
            continue
        old, new = row["original"], row["candidate"]
        first_head[phase]["original"][old[0][0]] += int(winning[0] == old[0][0])
        first_head[phase]["candidate"][new[0][0]] += int(winning[0] == new[0][0])
        for n in TOPS:
            a, b = winning in old[:n], winning in new[:n]
            stat = phases[phase][f"top{n}"]
            stat["original"] += int(a)
            stat["candidate"] += int(b)
            stat["gained"] += int(b and not a)
            stat["lost"] += int(a and not b)
    for phase, metrics in phases.items():
        count = statuses[phase]["confirmed"]
        for stat in metrics.values():
            stat["denominator"] = count
            stat["original_pct"] = round(100 * stat["original"] / count, 2) if count else None
            stat["candidate_pct"] = round(100 * stat["candidate"] / count, 2) if count else None
            if stat["candidate"]-stat["original"] != stat["gained"]-stat["lost"]:
                raise ValueError("head_prior_pair_arithmetic_mismatch")
    return {
        "schema": "HIT_HEAD_PRIOR_FORWARD_REFERENCE_V1",
        "status": "local_paired_reference_only_not_first_remote_receipt",
        "policy": RULE,
        "eligible_start_jst": START,
        "eligible_end_jst": END,
        "candidate_first_remote_receipt_verified": False,
        "complete_capture_run_inventory_verified": False,
        "official_T_minus_12_six_and_odds_verified": False,
        "formal": False,
        "model_improvement_proven": False,
        "model_promotion_allowed": False,
        "candidate_batches_supplied": len(batches),
        "frozen_eligible_candidates_supplied": len(frozen),
        "first_600_reference_slots_reserved": len(cohort),
        "pilot_slots_reserved": min(len(cohort), PILOT),
        "confirmation_slots_reserved": max(0, len(cohort)-PILOT),
        "result_status_by_phase": {k: dict(v) for k, v in statuses.items()},
        "pending_result_codes": pending,
        "invalid_result_codes": invalid,
        "hit_topn_by_phase": phases,
        "winner_head_hit_count_by_phase":
            {k: {label: dict(v) for label, v in rows.items()}
             for k, rows in first_head.items()},
        "warning": "Local timestamp/replay does not prove first remote receipt, "
                   "all scheduled candidate attempts, official beforeinfo/120 odds, "
                   "or prospective accuracy. No formal eligibility or promotion.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--batch", type=Path, action="append", default=[])
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    batches = [json.loads(x.read_bytes()) for x in args.batch]
    result = compare(batches, args.root)
    raw = json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    if args.output:
        args.output.write_text(raw, encoding="utf-8")
    else:
        print(raw, end="")


if __name__ == "__main__":
    main()

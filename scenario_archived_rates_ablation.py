"""Read-only archived national-rate vs neutral-rate ablation for real #1710 pair sources.

Never produce a forecast or score a finish. Immutable V2 blobs are old,
nonofficial national-rate inputs, not verified official racelist originals.
The two original source ZIPs remain the existing #1710 fixtures. New forecasts,
future cohort records, official evidence and production files are untouched.
"""
import argparse
from datetime import datetime, timedelta
import hashlib
import importlib
import json
import math
from pathlib import Path

from scenario_actual_pair_four_mode_replay import (
    REGRESSION_CODES, NEUTRAL_RATES, hypotheses, weights,
)
from scenario_official_pair_research_input import official_partial_from_zip
from scenario_mode_specific_exhibition_end_to_end import (
    MODES, BUDGETS, evaluate_exhibition_mode_lenses,
)

MAIN_PIN = "1e8b6b86e4c700bcf10b5dfcb4cdaa981799bb78"
ARCHIVED_BLOBS = {
    "202611091110": "492f9d732df9fe46d6cba4f52135f4ee0c148592",
    "202611091710": "75252b292d1aa2bbd97d222e9c249d158edaad34",
    "202611101202": "d7801a878c4f2d1fd296f2d21c38906e92df0efb",
    "202611102211": "f6f20088220f2c42d785f4b4eada20eef5d930cd",
}
VERSION = "CLEAN_FOUR_MODES_V2_PROVISIONAL_UNCALIBRATED"
STUDY = "EXPLORATORY_ONLY_ARCHIVED_RATES_REAL_PAIR_V1"
RESULT_FIELDS = {"finish_order", "result", "payout", "winning_ticket",
                 "confirmed_at_jst", "outcome", "winner"}


def git_blob_sha(raw):
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def validate_original_rates(raw, code):
    if code not in ARCHIVED_BLOBS or not isinstance(raw, (bytes, bytearray)):
        raise ValueError("unregistered_original_blob")
    if len(raw) > 30000 or not raw:
        raise ValueError("archived_original_size_invalid")
    try:
        record = json.loads(raw)
    except (ValueError, UnicodeError) as exc:
        raise ValueError("archived_original_not_json") from exc
    if (type(record) is not dict or RESULT_FIELDS.intersection(record)
            or record.get("race_code") != code
            or record.get("model_version") != VERSION
            or record.get("schema") != "CLEAN_FOUR_MODES_PREDEADLINE_V1"
            or record.get("validated") is not False
            or record.get("target_rates_not_proven") is not True
            or record.get("beforeinfo") != "optional_not_in_snapshot"):
        raise ValueError("archived_original_wrong_contract")
    rates = record.get("input_national_win_rates")
    if (type(rates) is not list or len(rates) != 6
            or any(type(v) not in (int, float) or not math.isfinite(v)
                   or not 0 < v < 20 for v in rates)):
        raise ValueError("archived_original_six_rates_invalid")
    provenance = record.get("source_sha256")
    if (type(provenance) is not dict or set(provenance) != {"race_cards", "title"}
            or any(type(s) is not str or len(s) != 64
                   or any(c not in "0123456789abcdef" for c in s)
                   for s in provenance.values())):
        raise ValueError("archived_original_source_digests_invalid")
    try:
        created = datetime.fromisoformat(record["generated_at_jst"])
        deadline = datetime.fromisoformat(record["deadline_jst"])
    except (TypeError, ValueError, KeyError) as exc:
        raise ValueError("archived_original_clock_invalid") from exc
    jst = timedelta(hours=9)
    if (created.utcoffset() != jst or deadline.utcoffset() != jst
            or created >= deadline - timedelta(minutes=12)):
        raise ValueError("archived_original_not_pre_T12_self_reported")
    return rates, created


def load_original_rates(code, directory):
    if code not in ARCHIVED_BLOBS:
        raise ValueError("not_on_pinned_original_roster")
    path = Path(directory) / (code + ".json")
    if path.is_symlink() or not path.is_file():
        raise ValueError("missing_pinned_original")
    raw = path.read_bytes()
    if git_blob_sha(raw) != ARCHIVED_BLOBS[code]:
        raise ValueError("immutable_original_git_blob_mismatch")
    rates, generated_at = validate_original_rates(raw, code)
    return rates, generated_at



def read_archived_mode_tickets(raw, code):
    """Inspect only immutable prior V2 tickets. No outcome or current model re-rank."""
    validate_original_rates(raw, code)
    record = json.loads(raw)
    modes = record.get("modes")
    if type(modes) is not dict or set(modes) != set(BUDGETS):
        raise ValueError("archived_four_mode_budget_contract_invalid")
    from itertools import permutations
    valid = {"-".join(map(str, x)) for x in permutations(range(1, 7), 3)}
    answer = {}
    for mode, count in BUDGETS.items():
        row = modes.get(mode)
        tickets = row.get("tickets") if type(row) is dict else None
        if type(tickets) is not list or len(tickets) != count:
            raise ValueError("archived_mode_ticket_count_invalid")
        combos = []
        for item in tickets:
            if (type(item) is not dict or type(item.get("combo")) is not str
                    or item["combo"] not in valid
                    or type(item.get("p")) not in (int, float)
                    or not math.isfinite(item["p"])
                    or not 0 <= item["p"] <= 100):
                raise ValueError("archived_ticket_invalid")
            combos.append(item["combo"])
        if len(set(combos)) != count:
            raise ValueError("archived_mode_duplicate_ticket")
        answer[mode] = combos
    return answer


def compare_original_to_experiment(original, experimental):
    """Same-race input-only ticket exposure, NOT achieved Top-N accuracy."""
    if (type(original) is not list or type(experimental) is not dict
            or type(experimental.get("tickets")) is not list
            or type(experimental.get("top1")) is not str
            or not original):
        raise ValueError("invalid_archived_vs_experimental_comparison")
    research = [x.get("combo") if type(x) is dict else None
                for x in experimental["tickets"]]
    if (len(research) != len(original) or len(set(research)) != len(research)
            or not all(type(x) is str for x in research)
            or research[0] != experimental["top1"]):
        raise ValueError("changed_mode_budget_or_order")
    from itertools import permutations
    valid = {"-".join(map(str, x)) for x in permutations(range(1, 7), 3)}
    if not (set(research) <= valid and set(original) <= valid):
        raise ValueError("illegal_ticket_in_comparison")
    top = {}
    for k in (1, 3, 5, 10):
        key = f"top{k}"
        if k > len(original):
            top[key] = {"applicable": False, "reason": "mode_budget_below_topn"}
        else:
            a, b = set(original[:k]), set(research[:k])
            top[key] = {
                "applicable": True,
                "membership_changed": a != b,
                "shared_ticket_count": len(a & b),
                "candidate_only_not_actual_new_hits": len(b - a),
                "original_only_not_actual_lost_hits": len(a - b),
            }
    return {
        "original_top1": original[0],
        "hypothetical_top1": research[0],
        "top1_exact_ticket_changed": original[0] != research[0],
        "top1_first_boat_changed": original[0][0] != research[0][0],
        "by_topn": top,
        "confirmed_result_read": False,
        "gain_or_loss_in_actual_hit_rate_computed": False,
    }


def run_ablation(nov9_zip, nov10_zip, originals_dir, conditional_callback):
    if not callable(conditional_callback):
        raise ValueError("pinned_1698_callback_required")
    zip_by_day = {"20261109": Path(nov9_zip), "20261110": Path(nov10_zip)}
    rows = []
    for code in REGRESSION_CODES:
        rates, generated = load_original_rates(code, originals_dir)
        # load_original_rates verified this file's exact immutable Git blob.
        original_tickets = read_archived_mode_tickets(
            (Path(originals_dir) / (code + ".json")).read_bytes(), code)
        try:
            projection, witness = official_partial_from_zip(zip_by_day[code[:8]], code)
        except ValueError as exc:
            if str(exc) != "six_exhibition_st_not_yet_available":
                raise
            rows.append({"race_code": code, "status": "EXHIBITION_MISSING_REJECTED",
                         "original_v2_blob": ARCHIVED_BLOBS[code],
                         "formal": False, "results_read": False})
            continue
        source_clock = [datetime.fromisoformat(x) for x in
                        witness["original_receipt_jst_self_reported"]]
        if not source_clock or any(generated >= x for x in source_clock):
            raise ValueError("original_self_reported_generation_not_before_official_pair")
        def evaluate(rate_input, scenario_input=None):
            out = evaluate_exhibition_mode_lenses(
                projection, list(rate_input),
                hypotheses() if scenario_input is None else scenario_input,
                weights(), conditional_callback, study_id=STUDY)
            if (out["formal"] or out["forecast_usable"] or out["promotion_allowed"]
                    or out["first_candidate_remote_receipt_verified"]
                    or out["outcomes_read_by_adapter"]):
                raise ValueError("unapproved_provenance_or_promotion")
            return out
        neutral, archived = evaluate(NEUTRAL_RATES), evaluate(rates)
        # Strictly controlled negative hypothesis: remove every head log-shift
        # while preserving actual archived rates, exhibition ST/time/entry,
        # position coefficients, all scenario weights and ticket budgets.
        # This is sensitivity to uncalibrated scenario assumptions, NOT
        # identification of the causal effect or improvement in hit rate.
        no_head = hypotheses()
        for scenario in no_head.values():
            scenario["head_log_shifts"] = [0.0] * 6
        without_head = evaluate(rates, no_head)
        per_mode = {}
        head_effect = {}
        archived_vs_scenario = {}
        for mode in MODES:
            a = neutral["four_mode_research_tickets"][mode]
            b = archived["four_mode_research_tickets"][mode]
            at = {x["combo"] for x in a["tickets"]}
            bt = {x["combo"] for x in b["tickets"]}
            if len(at) != BUDGETS[mode] or len(bt) != BUDGETS[mode]:
                raise ValueError("mode_budget_changed")
            changed = a["distinct_120_mixture_digest"] != b["distinct_120_mixture_digest"]
            if not changed:
                raise ValueError("saved_national_rates_did_not_enter_math")
            per_mode[mode] = {
                "entire_120_probability_digest_changed": changed,
                "top1_changed": a["top1"] != b["top1"],
                "ticket_membership_changed": at != bt,
                "shared_ticket_count": len(at & bt),
                "ticket_count": BUDGETS[mode],
            }
            h = without_head["four_mode_research_tickets"][mode]
            ht = {x["combo"] for x in h["tickets"]}
            archived_vs_scenario[mode] = {
                "with_uncalibrated_head_shift": compare_original_to_experiment(
                    original_tickets[mode], b),
                "without_uncalibrated_head_shift": compare_original_to_experiment(
                    original_tickets[mode], h),
            }
            head_effect[mode] = {
                "uncalibrated_head_shift_changes_120_board":
                    b["distinct_120_mixture_digest"] != h["distinct_120_mixture_digest"],
                "uncalibrated_head_shift_changes_top1": b["top1"] != h["top1"],
                "uncalibrated_head_shift_changes_ticket_membership": bt != ht,
                "shared_ticket_count_without_head_shift": len(bt & ht),
                "ticket_count": BUDGETS[mode],
            }
        rows.append({
            "race_code": code,
            "status": "ARCHIVED_SIX_RATES_PLUS_REAL_EXHIBITION_RESEARCH_ONLY",
            "original_v2_blob": ARCHIVED_BLOBS[code],
            "official_beforeinfo_source_sha256": witness["beforeinfo_sha256"],
            "official_odds_html_source_sha256": witness["odds_original_html_sha256"],
            "original_generation_before_source_self_reported": True,
            "source_to_new_forecast_chronology_proven": False,
            "archived_rates_are_official_racelist_attested": False,
            "estimated_probabilities_are_calibrated": False,
            "hypothetical_scenario_coefficients_are_calibrated": False,
            "model_uses_actual_final_entry": False,
            "mode_input_ablation": per_mode,
            "mode_uncalibrated_head_shift_ablation": head_effect,
            "archived_V2_vs_research_topn_exposure_result_blind": archived_vs_scenario,
            # Full ranked lists are only exported as an OUTCOME-FREE bridge.
            # The historical confirmed result is NEVER loaded by this model
            # computation. A separate final CI step may read results AFTER
            # these candidate lists and digests are already written.
            "unregistered_retrospective_ranked_lists_before_result_read": {
                mode: {
                    "archived_V2": original_tickets[mode],
                    "scenario_head35": [
                        x["combo"] for x in archived["four_mode_research_tickets"][mode]["tickets"]],
                    "scenario_head0_control": [
                        x["combo"] for x in without_head["four_mode_research_tickets"][mode]["tickets"]],
                } for mode in MODES
            },
            "future_candidate_first_remote_receipt_verified": False,
            "admitted_to_1693_registered_cohort": False,
            "head_shift_ablation_kept_real_rates_exhibition_and_position_features": True,
            "head_shift_assumptions_validated_against_results": False,
            "formal": False, "results_read": False,
        })
    if len(rows) != 4 or sum(x["status"].startswith("ARCHIVED_SIX") for x in rows) != 3:
        raise ValueError("fixed_pair_input_census_changed")
    return {
        "study_id": STUDY, "baseline_original_main_commit": MAIN_PIN,
        "original_blobs": ARCHIVED_BLOBS,
        "classification": "retrospective_input_consumption_only_not_accuracies",
        "races": rows,
        "complete_exhibition_and_saved_rates": 3,
        "exhibition_missing_rejected": 1,
        "formal": False, "accuracy_improvement_proven": False,
        "original_forecasts_modified": False,
        "new_forecasts_published": False,
        "results_read": False, "production_changed": False,
        "warning": "Rates are archived V2 CSV-derived inputs, NOT a verified official racelist; explicit scenarios are uncalibrated. Not prospective prediction or hit-rate evidence.",
    }


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--nov9-zip", required=True, type=Path)
    p.add_argument("--nov10-zip", required=True, type=Path)
    p.add_argument("--original-dir", required=True, type=Path)
    p.add_argument("--out", required=True, type=Path)
    args = p.parse_args()
    cb = importlib.import_module("position_sensitive_conditioned_lab").experimental_conditional_board
    result = run_ablation(args.nov9_zip, args.nov10_zip, args.original_dir, cb)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"computed": result["complete_exhibition_and_saved_rates"],
                      "missing": result["exhibition_missing_rejected"],
                      "formal": False, "accuracy_improvement_proven": False},
                     ensure_ascii=False))

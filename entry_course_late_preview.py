"""A separate T-2 research experiment using common available information.

This is NOT a T-12 rerun. All three rankings here are frozen at the same
late cutoff and use the SAME observed entry. The original saved T-12 baseline
is preserved for traceability but not included as a comparable arm.
No result input is read.
"""
from datetime import timedelta
from research_model import probabilities
from entry_course_candidate import challenger_rank
from entry_course_history import compile_asof_course_history
from entry_course_prospective_capture import _when, _entry_from_preview
from entry_course_timing_audit import classify_course_timing
import re

VALID_CODE=re.compile(r"20[0-9]{10}\Z")


def prepare_late_preview_study(base, card, history_batch, *,
                               frozen_at, min_starts=10, margin_minutes=2):
    if not all(isinstance(x,dict) for x in (base,card,history_batch)):
        raise ValueError("late_study_missing_inputs")
    code=base.get("race_code")
    if type(code) is not str or not VALID_CODE.fullmatch(code):
        raise ValueError("late_study_invalid_race")
    if card.get("race_key")!=f"{code[:8]}-{code[8:10]}-{code[10:]}":
        raise ValueError("late_study_race_mismatch")
    if card.get("meta",{}).get("phase")!="PRE_RESULT" or card.get("meta",{}).get("results_seen") is not False:
        raise ValueError("late_study_not_pre_result")
    target_cutoff=_when(base.get("cutoff_jst"))
    deadline=_when(base.get("source_deadline_jst"))
    base_time=_when(base.get("generated_at"))
    now=_when(frozen_at)
    if (not target_cutoff or not deadline or not base_time or not now
            or not base_time <= target_cutoff < deadline
            or type(margin_minutes) not in (int,float) or not 1 <= margin_minutes <= 5):
        raise ValueError("late_study_invalid_timing")
    later_cutoff=deadline-timedelta(minutes=margin_minutes)
    if not target_cutoff<now<later_cutoff:
        raise ValueError("late_study_not_frozen_in_late_window")
    # The race card is independently fetched. Require its own exact race
    # deadline and a local receipt that predates this study's freeze.
    from entry_course_prospective_capture import HEX64
    meta=card.get("meta",{})
    day=meta.get("date")
    deadline_clock=meta.get("deadline")
    if (not isinstance(day,str) or not isinstance(deadline_clock,str)
            or not re.fullmatch(r"20\\d{2}-\\d{2}-\\d{2}",day)
            or not re.fullmatch(r"(?:[01]\\d|2[0-3]):[0-5]\\d",deadline_clock)
            or _when(day+"T"+deadline_clock+":00+09:00")!=deadline):
        raise ValueError("late_study_card_deadline_mismatch")
    card_audit=card.get("source_audit",{}).get("race_card",{})
    card_receipt=_when(card_audit.get("fetched_at"))
    if (card_audit.get("status")!="ok"
            or card_audit.get("predeadline_verified") is not True
            or not HEX64.fullmatch(str(card_audit.get("sha256") or ""))
            or not card_receipt or card_receipt>now or card_receipt>=deadline):
        raise ValueError("late_study_card_provenance_missing_or_after_freeze")
    timing=classify_course_timing(base,card.get("source_audit",{}).get("beforeinfo"),
                                   late_margin_minutes=margin_minutes)
    if not timing.get("late_experiment_possible"):
        raise ValueError("late_preview_missing_before_late_cutoff")
    if history_batch.get("target_day")!=code[:8] or _when(history_batch.get("cutoff_at"))!=later_cutoff:
        raise ValueError("late_study_history_cutoff_mismatch")
    if history_batch.get("research_only") is not True or not isinstance(history_batch.get("history"),list):
        raise ValueError("late_study_history_unavailable")
    if base.get("status")!="research" or base.get("validated") is not False:
        raise ValueError("late_study_baseline_invalid")
    rates=base.get("national_win_rates")
    base_tickets=base.get("predictions")
    if type(rates) is not list or type(base_tickets) is not list or len(base_tickets)!=10:
        raise ValueError("late_study_baseline_data_missing")
    historical_t12=["-".join(map(str,t)) for t,p in probabilities(rates)]
    if historical_t12[:10]!=base_tickets:
        raise ValueError("late_study_t12_baseline_drift")
    entry,receipts=_entry_from_preview(card,later_cutoff)
    receipts.append({"received_at":card_receipt.isoformat(),"sha256":card_audit["sha256"],
                     "source":"third_party_race_card_local_receipt"})
    # Independently timestamped source data must already exist when this
    # candidate is frozen, not merely be earlier than the future cutoff.
    if any(_when(r["received_at"]) > now for r in receipts):
        raise ValueError("late_preview_not_observed_at_freeze")
    history=compile_asof_course_history(card,history_batch["history"],
                         cutoff_at=later_cutoff.isoformat(),entry=entry,min_starts=min_starts)
    if not history["history_sufficient"]:
        raise ValueError("late_study_insufficient_course_samples")
    for item in history["receipts"]:
        for typ in ("card","result"):
            receipts.append({"received_at":item[typ+"_receipt_at"],
                             "sha256":item[typ+"_sha256"],
                             "source":"third_party_historical_"+typ})
    if any(_when(r["received_at"]) > now for r in receipts):
        raise ValueError("late_history_not_observed_at_freeze")
    candidate=challenger_rank(rates,entry,history["boats"],
                    cutoff_at=later_cutoff.isoformat(),include_st=True,min_starts=min_starts)
    # The published T-12 ten tickets are explicitly not used for model comparison.
    return {"schema":"entry-course-late-preview-study-v1",
            "experiment":"T_MINUS_2_INFORMATION_MATCHED_RESEARCH",
            "race_code":code,
            "cutoff_at":later_cutoff.isoformat(),
            "reference_baseline_cutoff_at":target_cutoff.isoformat(),
            "frozen_at":now.isoformat(),
            "reference_t12_top10":base_tickets[:],
            "entry":entry,"entry_source":"third_party_timestamped_preview",
            "source_receipts":receipts,
            "baseline":[s for s,p in candidate["baseline"]],
            "course":[s for s,p in candidate["course"]],
            "course_plus_st":[s for s,p in candidate["course_plus_st"]],
            "research_only":True,"formal":False,
            "not_equivalent_to_t12":True,
            "independent_remote_first_seen_verified":False,
            "experimental_parameters":{"min_starts":min_starts,
                                     "eligible_historical_races":history["eligible_races"],
                                     "preview_timing_status":timing["status"]}}

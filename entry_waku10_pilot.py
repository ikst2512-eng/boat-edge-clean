"""Exploratory Waku10 T−2 challenger, separately sourced from full course history.

Frame's last-ten actual entry/finish evidence is used for course-dependent
rank adjustments, while frame-average ST is an explicitly labelled PROXY.
No race result is read, no official four-mode forecasts are changed.
Coefficients are fixed hypotheses, NOT calibrated empirical probabilities.
"""
from datetime import timedelta
from itertools import permutations
from math import exp, log, isfinite
from research_model import probabilities
from entry_course_prospective_capture import _entry_from_preview, _when, HEX64
from entry_course_timing_audit import classify_course_timing
from entry_waku10_source import extract_waku10_course_evidence
import re

PROTOCOL="WAKU10_FRAME10_COURSE_FILTER_BETA035_STPROXY050_RESEARCH_V1"
EXPECTED={"-".join(map(str,t)) for t in permutations(range(1,7),3)}
ROLES=("courseWinRate","courseTop2Rate","courseTop3Rate")
PRIORS=(1/6,2/6,3/6)


def prepare_waku10_pilot(base, card, evidence, *, frozen_at, min_course_starts=8):
    if not all(isinstance(x,dict) for x in (base,card,evidence)):
        raise ValueError("waku10_pilot_missing_sources")
    code=base.get("race_code")
    if (type(code) is not str or not re.fullmatch("20[0-9]{10}",code)
            or card.get("race_key")!=f"{code[:8]}-{code[8:10]}-{code[10:]}"):
        raise ValueError("waku10_pilot_race_mismatch")
    now=_when(frozen_at)
    t12=_when(base.get("cutoff_jst"))
    original=_when(base.get("generated_at"))
    deadline=_when(base.get("source_deadline_jst"))
    if not now or not t12 or not original or not deadline or not original<=t12<deadline:
        raise ValueError("waku10_pilot_invalid_baseline_clock")
    late=deadline-timedelta(minutes=2)
    if not t12<now<late:
        raise ValueError("waku10_pilot_after_cutoff")
    if card.get("meta",{}).get("phase")!="PRE_RESULT" or card.get("meta",{}).get("results_seen") is not False:
        raise ValueError("waku10_pilot_not_preresult")
    meta=card.get("meta",{})
    if (meta.get("date")!=code[:4]+"-"+code[4:6]+"-"+code[6:8]
            or _when(meta.get("date","")+"T"+str(meta.get("deadline") or "")+":00+09:00")!=deadline):
        raise ValueError("waku10_pilot_deadline_mismatch")
    card_receipt=card.get("source_audit",{}).get("race_card",{})
    card_at=_when(card_receipt.get("fetched_at"))
    if (card_receipt.get("status")!="ok" or card_receipt.get("predeadline_verified") is not True
            or not HEX64.fullmatch(str(card_receipt.get("sha256") or ""))
            or not card_at or card_at>now):
        raise ValueError("waku10_pilot_card_receipt_invalid")
    if not classify_course_timing(base,card.get("source_audit",{}).get("beforeinfo")).get("late_experiment_possible"):
        raise ValueError("waku10_pilot_preview_unavailable")
    if base.get("status")!="research" or base.get("validated") is not False:
        raise ValueError("waku10_pilot_reference_invalid")
    rates=base.get("national_win_rates")
    if (type(rates) is not list or len(rates)!=6 or
            ["-".join(map(str,t)) for t,p in probabilities(rates)[:10]]!=base.get("predictions")):
        raise ValueError("waku10_pilot_reference_model_drift")
    entry,receipts=_entry_from_preview(card,late)
    if any(_when(r["received_at"])>now for r in receipts):
        raise ValueError("waku10_pilot_preview_after_freeze")
    source=extract_waku10_course_evidence(card,evidence,entry,
                           frozen_at=frozen_at,min_course_starts=min_course_starts)
    if not source["all_course_samples_sufficient"]:
        raise ValueError("waku10_pilot_insufficient_course_specific_frame_runs")
    if any(r["frameAverageSTProxy"] is None for r in source["rows"]):
        raise ValueError("waku10_pilot_frame_st_missing")
    by_boat={r["boat"]:r for r in source["rows"]}
    base_board=probabilities([rates[b-1] for b in entry])
    baseline=[(tuple(entry[i-1] for i in ticket),p) for ticket,p in base_board]
    def ranking(st):
        results=[]
        for ticket,p in baseline:
            boost=0.0
            for pos,boat in enumerate(ticket):
                r=by_boat[boat]
                n=r["matchedCourseCompletedRuns"]
                shrink=(n*r[ROLES[pos]]+20*PRIORS[pos])/(n+20)
                boost+=0.35*log(shrink/PRIORS[pos])
                if st:
                    boost+=0.5*(0.16-r["frameAverageSTProxy"])
            results.append(("-".join(map(str,ticket)),p*exp(boost)))
        total=sum(p for _,p in results)
        if total<=0 or not isfinite(total):
            raise ValueError("waku10_pilot_nonnormalizable")
        return [t for t,p in sorted(results,key=lambda x:(-x[1],x[0]))]
    original_rank=["-".join(map(str,t)) for t,p in
                   sorted(baseline,key=lambda x:(-x[1],x[0]))]
    course=ranking(False)
    course_st=ranking(True)
    if any(len(r)!=120 or set(r)!=EXPECTED for r in (original_rank,course,course_st)):
        raise ValueError("waku10_pilot_invalid_ticket_board")
    receipts+=[{"received_at":card_at.isoformat(),"sha256":card_receipt["sha256"],
                "source":"third_party_race_card"},
               source["source_receipt"]]
    if any(_when(r["received_at"])>now for r in receipts):
        raise ValueError("waku10_pilot_late_source_receipt")
    return {"schema":"entry-waku10-late-preview-pilot-v1","protocol":PROTOCOL,
            "race_code":code,"cutoff_at":late.isoformat(),
            "reference_baseline_cutoff_at":t12.isoformat(),"frozen_at":now.isoformat(),
            "reference_t12_top10":base["predictions"][:],
            "entry":entry,"source_receipts":receipts,
            "baseline":original_rank,"waku10_course":course,
            "waku10_course_plus_frame_st_proxy":course_st,
            "sample_counts":{str(r["boat"]):r["matchedCourseCompletedRuns"] for r in source["rows"]},
            "min_course_starts":min_course_starts,
            "frame_st_is_not_course_st":True,
            "historical_result_joins_in_this_pilot":False,
            "research_only":True,"forecast_record":True,
            "formal":False,"calibrated":False,
            "independent_remote_first_seen_verified":False,
            "not_equivalent_to_t12":True}

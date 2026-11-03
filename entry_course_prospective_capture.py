"""Prepare a genuine pre-cutoff, read-only course challenger capture.

No result endpoint, no model promotion, and no post-result reconstruction.
Use independently saved baseline, CLEAN racecard and actually acquired older
source rows. Calling this function alone does NOT persist a capture.
"""
from datetime import datetime
from itertools import permutations
from research_model import probabilities
from entry_course_candidate import challenger_rank
from entry_course_history import compile_asof_course_history
import re

HEX64=re.compile(r"^[a-f0-9]{64}$")


def _when(s):
    try:
        t=datetime.fromisoformat(s)
        return t if t.utcoffset() is not None else None
    except (ValueError,TypeError):
        return None


def _entry_from_preview(card, cutoff):
    audit=card.get("source_audit",{}).get("beforeinfo",{})
    before=card.get("beforeinfo",{})
    starts=before.get("start_exhibition") if isinstance(before,dict) else None
    if audit.get("status")!="ok" or not isinstance(starts,list) or len(starts)!=6:
        raise ValueError("preview_six_boats_unavailable")
    ids=[x.get("lane") for x in starts if isinstance(x,dict)]
    courses=[x.get("course") for x in starts if isinstance(x,dict)]
    if (len(ids)!=6 or len(courses)!=6 or
            any(type(n) not in (int,float) or n not in range(1,7) for n in ids+courses) or
            set(ids)!=set(range(1,7)) or set(courses)!=set(range(1,7))):
        raise ValueError("preview_course_permutation_invalid")
    receipts=[]
    for kind in ("stt","tkz"):
        r=audit.get("sources",{}).get(kind)
        timestamp=_when(r.get("observed_at")) if isinstance(r,dict) else None
        if (timestamp is None or timestamp>=cutoff or
                not HEX64.fullmatch(str(r.get("sha256") or ""))):
            raise ValueError("preview_"+kind+"_receipt_missing_or_late")
        receipts.append({"received_at":timestamp.isoformat(),"sha256":r["sha256"],
                         "source":"third_party_preview_"+kind})
    return [int(x["lane"]) for x in sorted(starts,key=lambda r:r["course"])],receipts


def prepare_prospective_capture(base,card,history_batch,*,frozen_at,min_starts=10):
    """Build candidate ranking only if ALL evidence existed before baseline cutoff.

    This requires the exact frozen baseline top ten and racecard's same race.
    Historical BoatraceCSV source fields are NOT authenticated official records.
    """
    if not all(isinstance(x,dict) for x in (base,card,history_batch)):
        raise ValueError("missing_capture_inputs")
    code=base.get("race_code")
    if (not isinstance(code,str) or not re.fullmatch(r"20\d{10}",code)
            or card.get("race_key")!=f"{code[:8]}-{code[8:10]}-{code[10:]}"):
        raise ValueError("race_key_mismatch")
    cutoff=_when(base.get("cutoff_jst"))
    now=_when(frozen_at)
    generated=_when(base.get("generated_at"))
    if (not cutoff or not now or not generated or
            not generated<=cutoff or now>cutoff):
        raise ValueError("capture_not_pre_cutoff")
    if base.get("status")!="research" or base.get("validated") is not False:
        raise ValueError("baseline_not_frozen_research")
    if (card.get("meta",{}).get("phase")!="PRE_RESULT"
            or card.get("meta",{}).get("results_seen") is not False):
        raise ValueError("racecard_not_pre_result")
    if (history_batch.get("target_day")!=code[:8]
            or _when(history_batch.get("cutoff_at"))!=cutoff
            or history_batch.get("research_only") is not True):
        raise ValueError("history_window_mismatch")
    if not isinstance(history_batch.get("history"),list):
        raise ValueError("historical_source_rows_missing")
    rates=base.get("national_win_rates")
    if (not isinstance(rates,list) or len(rates)!=6
            or len(base.get("predictions",[]))!=10
            or len(set(base["predictions"]))!=10):
        raise ValueError("baseline_rates_or_top10_missing")
    original=probabilities(rates)
    original_names=["-".join(map(str,t)) for t,p in original]
    if original_names[:10]!=base["predictions"]:
        raise ValueError("baseline_rank_drift")
    entry,receipts=_entry_from_preview(card,cutoff)
    history=compile_asof_course_history(card,history_batch["history"],
                                        cutoff_at=base["cutoff_jst"],entry=entry,
                                        min_starts=min_starts)
    if not history["history_sufficient"]:
        raise ValueError("insufficient_course_by_registration_samples")
    historical_receipts={}
    for receipt in history["receipts"]:
        for kind in ("card","result"):
            key=(receipt[kind+"_sha256"],receipt[kind+"_receipt_at"])
            historical_receipts[key]={"received_at":receipt[kind+"_receipt_at"],
                                      "sha256":receipt[kind+"_sha256"],
                                      "source":"third_party_historical_"+kind}
    receipts+=list(historical_receipts.values())
    candidate=challenger_rank(rates,entry,history["boats"],
                               cutoff_at=base["cutoff_jst"],include_st=True,
                               min_starts=min_starts)
    return {"schema":"entry-course-prospective-capture-v1",
            "race_code":code,"cutoff_at":cutoff.isoformat(),
            "frozen_at":now.isoformat(),"research_only":True,
            "entry_source":"third_party_timestamped_preview",
            "entry":entry,"source_receipts":receipts,
            "baseline":original_names,
            "course":[ticket for ticket,p in candidate["course"]],
            "course_plus_st":[ticket for ticket,p in candidate["course_plus_st"]],
            "calibration":"unverified_research_only",
            "model_metadata":{"eligible_historical_races":history["eligible_races"],
                              "course_sample_minimum":min_starts,
                              "source_failures":history_batch.get("failed_sources",[])}}

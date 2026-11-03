"""Prospective-only verification before comparing course challengers.

A historical 10-ticket snapshot is a valid frozen baseline, but it is NOT
evidence that course/ST challengers were generated before the race. The
readiness gate refuses reconstruction after results are known.
"""
from datetime import datetime
from itertools import permutations
import re
from entry_course_candidate import evaluate_matched

VALID_TICKETS={"-".join(map(str,t)) for t in permutations(range(1,7),3)}
HEX64=re.compile(r"^[0-9a-f]{64}$")
CODE=re.compile(r"^20\d{10}$")


def _instant(v):
    if not isinstance(v,str):
        return None
    try:
        t=datetime.fromisoformat(v)
    except ValueError:
        return None
    return t if t.utcoffset() is not None else None


def audit_frozen_comparison(base, candidate, result=None):
    """Returns diagnostics without manufacturing missing historical evidence.

    base: research_snapshots/<code>.json as saved by research_model.py.
    candidate: append-only 3-way prospective capture with immutable provenance:
      race_code, frozen_at, cutoff_at, entry, source_receipts,
      baseline, course, course_plus_st.
    result: optional verified post-cutoff result receipt:
      race_code, result, received_at.  NEVER required to freeze candidates.
    """
    issues=[]
    base=base if isinstance(base,dict) else {}
    candidate=candidate if isinstance(candidate,dict) else {}
    code=base.get("race_code")
    if not isinstance(code,str) or CODE.fullmatch(code) is None:
        issues.append("baseline_race_code_missing")
    if base.get("status")!="research" or base.get("validated") is not False:
        issues.append("baseline_snapshot_invalid")
    pred=base.get("predictions")
    if (not isinstance(pred,list) or len(pred)!=10 or len(set(pred))!=10
        or any(p not in VALID_TICKETS for p in pred)):
        issues.append("baseline_frozen_top10_invalid")
    cutoff=_instant(base.get("cutoff_jst"))
    generated=_instant(base.get("generated_at"))
    deadline=_instant(base.get("source_deadline_jst"))
    if cutoff is None or generated is None or deadline is None or not generated<=cutoff<deadline:
        issues.append("baseline_not_frozen_before_cutoff")
    for field in ("source_cards_sha256","source_title_sha256","input_sha256","model_source_sha256"):
        if not HEX64.fullmatch(str(base.get(field) or "")):
            issues.append("baseline_"+field+"_invalid")
    if candidate.get("race_code")!=code or candidate.get("race_code") is None:
        issues.append("candidate_race_mismatch_or_missing")
    frozen=_instant(candidate.get("frozen_at"))
    candidate_cutoff=_instant(candidate.get("cutoff_at"))
    if not cutoff or candidate_cutoff!=cutoff or frozen is None or frozen>cutoff:
        issues.append("candidate_not_frozen_before_identical_cutoff")
    if candidate.get("research_only") is not True:
        issues.append("candidate_research_provenance_missing")
    if candidate.get("entry_source") not in ("third_party_timestamped_preview",):
        issues.append("candidate_entry_source_unverified")
    entry=candidate.get("entry")
    if (not isinstance(entry,list) or len(entry)!=6 or
        set(entry)!=set(range(1,7)) or any(type(x)!=int for x in entry)):
        issues.append("candidate_entry_invalid")
    receipts=candidate.get("source_receipts")
    if not isinstance(receipts,list) or not receipts:
        issues.append("candidate_source_receipts_missing")
    else:
        for r in receipts:
            stamp=_instant(r.get("received_at")) if isinstance(r,dict) else None
            if (not stamp or not cutoff or stamp>cutoff or
                    not HEX64.fullmatch(str(r.get("sha256") or ""))):
                issues.append("candidate_source_receipt_invalid")
                break
    for key in ("baseline","course","course_plus_st"):
        rank=candidate.get(key)
        if (not isinstance(rank,list) or len(rank)!=120 or
                len(set(rank))!=120 or set(rank)!=VALID_TICKETS):
            issues.append(key+"_full_ranking_missing_or_invalid")
    if ("baseline_full_ranking_missing_or_invalid" not in issues
        and isinstance(pred,list) and all(p in VALID_TICKETS for p in pred)
        and candidate["baseline"][:10]!=pred):
        issues.append("baseline_ranking_differs_from_frozen_prediction")
    # Not enough to construct a backtest from a 10-ticket base alone.
    eligible=not issues
    if result is not None:
        if not isinstance(result,dict) or result.get("race_code")!=code:
            issues.append("result_race_mismatch")
        elif (result.get("result") not in VALID_TICKETS
              or (t:=_instant(result.get("received_at"))) is None or
              not cutoff or t<=cutoff):
            issues.append("result_receipt_invalid")
        eligible=not issues
    return {"race_code":code,"comparison_ready":eligible,
            "can_score":eligible and result is not None,
            "reasons":list(dict.fromkeys(issues)),
            "existing_frozen_prediction_unchanged":True,
            "research_only":True}


def evaluate_verified_prospective(rows):
    """Score only matches with both original frozen base and challenger receipts.

    Missing historic challengers are excluded, NEVER inferred from the result.
    """
    usable=[]
    excluded={}
    for row in rows:
        row=row if isinstance(row,dict) else {}
        gate=audit_frozen_comparison(row.get("base"),row.get("candidate"),row.get("result"))
        if not gate["can_score"]:
            for why in gate["reasons"]:
                excluded[why]=excluded.get(why,0)+1
            continue
        c=row["candidate"]; r=row["result"]
        usable.append({"race_code":c["race_code"],"cutoff_at":c["cutoff_at"],
            "frozen_at":c["frozen_at"],"result_received_at":r["received_at"],
            "result":r["result"],"baseline":c["baseline"],"course":c["course"],
            "course_plus_st":c["course_plus_st"]})
    audit=evaluate_matched(usable)
    audit["prospective_evidence_exclusions"]=excluded
    audit["verified_cohort_only"]=True
    audit["empirical_improvement_verified"]=False
    return audit

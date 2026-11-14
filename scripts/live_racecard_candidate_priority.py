"""Pure candidate prioritization for real predeadline T-12 sampling.

Prioritize races that still have enough time to establish the API receipt
before the T-12 limit. Candidates lacking preview data remain eligible to
diagnose missing upstream sources. Never label any candidate as T-12 proven.
"""
from datetime import datetime, timedelta
import re


def t12_window_open(deadline, now, margin_minutes=12):
    if deadline.tzinfo is None or now.tzinfo is None:
        raise ValueError("t12_clock_timezone_missing")
    return deadline > now + timedelta(minutes=margin_minutes)


def rank_candidates(candidates, preview_candidates, now):
    """Return (deadline, race_code) pairs ranked by *opportunity*, not proof."""
    def priority(candidate):
        deadline, code = candidate
        possible=t12_window_open(deadline,now)
        preview=code in preview_candidates
        # first: possible and matched preview; then possible but no preview;
        # last: too-late candidates, with matching previews first for diagnostics.
        return (not possible, not preview, deadline, code)
    return sorted(candidates,key=priority)


def live_sampling_window_open(now):
    """Fail a delayed schedule that arrives after Japanese racing hours.

    This is a diagnostic guard, not proof of the scheduled cron's actual slot.
    Normal e2e samples are planned for 09:30 through 21:30 JST.
    """
    if now.tzinfo is None:
        raise ValueError("sample_clock_timezone_missing")
    return 9 <= now.hour < 23


def preview_codes_at_receipt(rows, race_day, received_at):
    """Accept published race-matched preview rows by actual source HTTP receipt.

    Receipt is an independent live observation. A source timestamp after that
    receipt, or at/after cutoff, can never establish predeadline availability.
    """
    if received_at.tzinfo is None:
        raise ValueError("preview_receipt_timezone_missing")
    from datetime import datetime
    from zoneinfo import ZoneInfo
    result=set()
    for row in rows:
        try:
            code=row["レースコード"]
            if not isinstance(code,str) or len(code)!=12 or not code.startswith(race_day):
                continue
            observed=datetime.fromisoformat(row["取得日時"])
            cutoff=datetime.strptime(race_day+row["締切時刻"],"%Y%m%d%H:%M").replace(tzinfo=ZoneInfo("Asia/Tokyo"))
            if observed.tzinfo is not None and observed<=received_at and observed<cutoff and received_at<cutoff:
                result.add(code)
        except (TypeError,KeyError,ValueError):
            continue
    return result


def fresh_candidates_at_selection(candidates, selection_now, min_minutes=2):
    """Drop races that ceased to be safely upcoming during source HTTP calls.

    Returns (upcoming, expired) for separate diagnostics. Selection never
    relies on the earlier scan start time after network I/O has completed.
    """
    if selection_now.tzinfo is None:
        raise ValueError("candidate_selection_timezone_missing")
    eligible=[]
    expired=[]
    margin=timedelta(minutes=min_minutes)
    for deadline,code in candidates:
        if deadline.tzinfo is None:
            raise ValueError("candidate_deadline_timezone_missing")
        if deadline>selection_now+margin:
            eligible.append((deadline,code))
        else:
            expired.append((deadline,code))
    return eligible,expired


def verified_csv_pair_receipts(before_audit, deadline, api_received_at):
    """Classify a genuine tkz+stt pair without confusing an official fallback.

    A complete official beforeinfo response may prove six exhibition readings,
    but its single 'official' receipt is not two independent CSV observations.
    Return (times, problems) so the caller can keep exhibition verification
    separate from the strict T-12 two-source eligibility check.
    """
    if deadline.tzinfo is None or api_received_at.tzinfo is None:
        raise ValueError("csv_pair_clock_timezone_missing")
    sources=before_audit.get("sources") if isinstance(before_audit,dict) else None
    if not isinstance(sources,dict):
        sources={}
    observed_times={}
    problems=[]
    for kind in ("tkz","stt"):
        receipt=sources.get(kind)
        if not isinstance(receipt,dict):
            problems.append(kind+":source_receipt_missing")
            continue
        raw=receipt.get("observed_at")
        if not isinstance(raw,str) or not raw.strip():
            problems.append(kind+":observed_at_missing")
            continue
        try:
            observed=datetime.fromisoformat(raw)
        except ValueError:
            problems.append(kind+":observed_at_invalid")
            continue
        if observed.tzinfo is None or observed>api_received_at or observed>=deadline:
            problems.append(kind+":observed_at_not_predeadline")
            continue
        sha=receipt.get("sha256")
        if not isinstance(sha,str) or re.fullmatch(r"[a-fA-F0-9]{64}",sha) is None:
            problems.append(kind+":sha256_missing_or_invalid")
            continue
        observed_times[kind]=observed
    return observed_times,problems

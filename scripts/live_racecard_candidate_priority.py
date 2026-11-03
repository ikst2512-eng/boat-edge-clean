"""Pure candidate prioritization for real predeadline T-12 sampling.

Prioritize races that still have enough time to establish the API receipt
before the T-12 limit. Candidates lacking preview data remain eligible to
diagnose missing upstream sources. Never label any candidate as T-12 proven.
"""
from datetime import timedelta


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

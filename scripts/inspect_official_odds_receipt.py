"""Research-only time/coverage gate for official 3T odds observations.

120 odds are not proof of pre-T12 availability, nor of forecast usability.
"""
from datetime import datetime, timedelta
import math


def inspect_odds_receipt(odds, *, race_code, received_at_jst, deadline_jst):
    if not isinstance(race_code, str) or len(race_code) != 12 or not race_code.isdigit():
        raise ValueError("invalid race code")
    received = datetime.fromisoformat(received_at_jst)
    deadline = datetime.fromisoformat(deadline_jst)
    if received.utcoffset() != timedelta(hours=9) or deadline.utcoffset() != timedelta(hours=9):
        raise ValueError("both timestamps must be JST")
    if received.date() != deadline.date() or race_code[:8] != deadline.strftime("%Y%m%d"):
        raise ValueError("race date and clock disagree")
    if not isinstance(odds, dict):
        raise ValueError("odds must be a dictionary")
    expected = {
        f"{a}-{b}-{c}"
        for a in range(1, 7) for b in range(1, 7) for c in range(1, 7)
        if len({a, b, c}) == 3
    }
    def positive_number(v):
        if isinstance(v, bool) or not isinstance(v, (int, float, str)):
            return False
        try:
            number = float(v)
        except (ValueError, OverflowError):
            return False
        return math.isfinite(number) and number > 0
    complete = set(odds) == expected and all(positive_number(x) for x in odds.values())
    return {
        "race_code": race_code,
        "observed_at_jst": received.isoformat(),
        "deadline_at_jst": deadline.isoformat(),
        "odds_entries": len(odds),
        "valid_120_combinations": complete,
        "observed_before_t12": received <= deadline - timedelta(minutes=12),
        "complete_odds_observed_before_t12": complete and received <= deadline - timedelta(minutes=12),
        "source_immutability_verified": False,
        "forecast_usable": False,
        "t12_eligible": False,
    }

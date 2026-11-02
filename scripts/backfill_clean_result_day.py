"""Manual, bounded historical confirmed-result recovery; never generates forecasts."""
import json
import re
import sys
from datetime import datetime, timedelta
from collect_clean_results import JST, collect

def validate_day(day, now=None):
    now = now or datetime.now(JST)
    if not isinstance(day, str) or re.fullmatch(r"[0-9]{8}", day) is None:
        raise ValueError("invalid_backfill_day")
    try:
        target = datetime.strptime(day, "%Y%m%d").date()
    except ValueError as exc:
        raise ValueError("invalid_backfill_day") from exc
    age = (now.astimezone(JST).date() - target).days
    if not 1 <= age <= 30:
        raise ValueError("backfill_day_outside_1_to_30_days")
    return day

def run(day, now=None, collector=collect):
    date = validate_day(day, now)
    result = collector(date)
    return {"mode": "manual_historical_backfill", "day": date, "result": result,
            "forecast_modified": False, "formal_accuracy_proven": False}

if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: python -m scripts.backfill_clean_result_day YYYYMMDD")
    print(json.dumps(run(sys.argv[1]), ensure_ascii=False, sort_keys=True))

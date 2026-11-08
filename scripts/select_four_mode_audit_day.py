"""Choose an audit day that has had time for its first V2 capture slot.

A delayed 22:20 JST GitHub schedule can execute after JST midnight. Before
08:00 JST, the new day's first 07:07-07:52 slots may still be arriving.
Audit the previous day instead of declaring a not-yet-started day failed.
This selector only changes read-only audit scope, never collection or saves.
"""
import os
from datetime import datetime, time, timedelta, timezone

JST = timezone(timedelta(hours=9))
NEW_DAY_READY_JST = time(8, 0)


def select_audit_day(now):
    if not isinstance(now, datetime) or now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("timezone-aware audit timestamp required")
    local = now.astimezone(JST)
    day = local.date()
    if local.time() < NEW_DAY_READY_JST:
        day -= timedelta(days=1)
    return day.strftime("%Y%m%d")


def main():
    day = select_audit_day(datetime.now(timezone.utc))
    env_file = os.environ.get("GITHUB_ENV")
    if not env_file:
        raise SystemExit("GITHUB_ENV is required for a consistent audit day")
    with open(env_file, "a", encoding="utf-8") as handle:
        handle.write(f"FOUR_MODE_AUDIT_DAY_JST={day}\n")
    print(f"FOUR_MODE_AUDIT_DAY_SELECTED={day} (read-only, not publication proof)")


if __name__ == "__main__":
    main()

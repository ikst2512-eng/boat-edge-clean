"""Choose one actual upcoming race for unattended research snapshot capture.

Selection never creates a forecast, never uses result data and never bypasses cutoff.
"""
from datetime import datetime, timedelta
from pathlib import Path
from research_model import JST, BASE, read_rows


def choose(now=None, root=None):
    now = now or datetime.now(JST)
    root = root or Path(__file__).resolve().parents[1]
    day = now.strftime("%Y%m%d")
    rows, received, _ = read_rows(BASE + f"title/{day[:4]}/{day[4:6]}/{day[6:8]}.csv")
    possible = []
    for row in rows:
        code = row.get("レースコード", "")
        if len(code) != 12 or not code.isascii() or not code.isdigit() or not code.startswith(day):
            continue
        venue, race = int(code[8:10]), int(code[10:12])
        if not (1 <= venue <= 24 and 1 <= race <= 12):
            continue
        try:
            deadline = datetime.strptime(day + row["電話投票締切予定"], "%Y%m%d%H:%M").replace(tzinfo=JST)
        except (ValueError, KeyError):
            continue
        cutoff = deadline - timedelta(minutes=12)
        if min((cutoff - now).total_seconds(), (cutoff - received).total_seconds()) < 1800:
            continue
        if (root / "research_snapshots" / (code + ".json")).exists():
            continue
        possible.append((deadline, code, day, venue, race))
    if not possible:
        return None
    return min(possible)[2:]


if __name__ == "__main__":
    choice = choose()
    if choice is None:
        print("NO_PREDEADLINE_RACE")
    else:
        print(" ".join(map(str, choice)))

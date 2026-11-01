"""Immutable historical four-mode forecast reader; never generates post-race picks."""
import json
import re
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MODES = ("hit", "balance", "hole", "narrow")
LABELS = {"hit": "本命", "balance": "バランス", "hole": "穴", "narrow": "絞り"}


def valid_ticket(ticket):
    if not isinstance(ticket, str) or not re.fullmatch(r"[1-6]-[1-6]-[1-6]", ticket):
        return False
    return len(set(ticket.split("-"))) == 3


def archived_four_modes(code, root=ROOT):
    if not isinstance(code, str) or not re.fullmatch(r"20\d{6}(?:0[1-9]|1\d|2[0-4])(?:0[1-9]|1[0-2])", code):
        return 422, {"status": "invalid_race_code"}
    path = Path(root) / "four_mode_forecasts" / (code + ".json")
    if path.is_symlink() or not path.is_file():
        return 404, {"status": "not_archived", "race_code": code}
    if path.stat().st_size > 30000:
        return 422, {"status": "invalid_archive"}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("schema") != "CLEAN_FOUR_MODES_PREDEADLINE_V1" or data.get("race_code") != code:
            raise ValueError("invalid_schema")
        created = datetime.fromisoformat(data["generated_at_jst"])
        cutoff = datetime.fromisoformat(data["deadline_jst"])
        if created.utcoffset() is None or cutoff.utcoffset() is None or created >= cutoff:
            raise ValueError("invalid_time")
        modes = data["modes"]
        if not isinstance(modes, dict) or set(modes) != set(MODES):
            raise ValueError("invalid_modes")
        output = {}
        for name in MODES:
            record = modes[name]
            rows = record["tickets"]
            if not isinstance(rows, list) or not rows or len(rows) > 120:
                raise ValueError("invalid_tickets")
            picks = []
            for row in rows:
                ticket = row["combo"]
                if not valid_ticket(ticket) or not isinstance(row.get("p"), (int, float)):
                    raise ValueError("invalid_ticket")
                picks.append({"combo": ticket, "p": row["p"]})
            if len(set(x["combo"] for x in picks)) != len(picks):
                raise ValueError("duplicate_tickets")
            output[name] = {"label": LABELS[name], "tickets": picks,
                            "target_hit_rate_pct": record.get("target_hit_rate_pct"),
                            "actual_hit_rate_pct": None}
        return 200, {
            "status": "historical_research_only", "race_code": code,
            "generated_at_jst": data["generated_at_jst"],
            "deadline_jst": data["deadline_jst"],
            "verified_first_git_add": False,
            "production_forecast": False,
            "disclaimer": "締切前のファイル内時刻のみ確認。Git初回追加証拠・正式予想は未検証。",
            "modes": output,
        }
    except (ValueError, KeyError, TypeError, OSError, OverflowError):
        return 422, {"status": "invalid_archive", "race_code": code}

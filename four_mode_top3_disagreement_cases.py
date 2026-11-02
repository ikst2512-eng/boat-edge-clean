"""Historical case inventory for hit/balance Top3 disagreements; no model edits."""
import json
import re
from pathlib import Path
from four_mode_frozen_diagnostic import compare_race

ROOT = Path(__file__).resolve().parent

def cases(root=ROOT):
    root = Path(root)
    output = []
    excluded = 0
    for path in sorted((root / "four_mode_forecasts").glob("*.json")):
        code = path.stem
        if not re.fullmatch(r"20[0-9]{10}", code):
            continue
        row = compare_race(code, root)
        if row.get("status") != "historical_comparison_only":
            excluded += 1
            continue
        a, b = row["modes"]["hit"], row["modes"]["balance"]
        if type(a.get("top3")) is not bool or type(b.get("top3")) is not bool:
            raise ValueError("invalid_top3_flags")
        if a["top3"] == b["top3"]:
            continue
        if path.is_symlink() or path.stat().st_size > 30000:
            raise ValueError("unsafe_archive")
        archive = json.loads(path.read_text(encoding="utf-8"))
        if archive.get("race_code") != code:
            raise ValueError("identity_mismatch")
        rates = archive.get("input_national_win_rates")
        if (type(rates) is not list or len(rates) != 6
                or any(type(v) not in (int, float) or not 0 <= v <= 10 for v in rates)):
            raise ValueError("missing_or_invalid_input")
        def top(mode):
            return [x["combo"] for x in archive["modes"][mode]["tickets"][:3]]
        output.append({"race_code": code, "model_version": archive["model_version"],
                       "winning_ticket": row["winning_ticket"],
                       "national_win_rates": rates,
                       "hit_rank": a["winning_rank"], "balance_rank": b["winning_rank"],
                       "hit_top3": top("hit"), "balance_top3": top("balance"),
                       "winner": "hit" if a["top3"] else "balance"})
    by_day = {}
    for row in output:
        d = by_day.setdefault(row["race_code"][:8], {"hit": 0, "balance": 0})
        d[row["winner"]] += 1
    return {"status": "historical_exploratory_only", "formal": False,
            "independent_holdout": False, "prospective_proven": False,
            "unavailable_races": excluded, "disagreement_cases": output, "by_day": by_day}

if __name__ == "__main__":
    print("TOP3_DISAGREEMENTS=" + json.dumps(cases(), ensure_ascii=False, sort_keys=True))

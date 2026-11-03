"""Exploratory result-blind V2 national-rate top-two head inclusion shadow.

The protocol is research-only and designed after looking at 2026-11-03
matched outcomes. Consequently all comparisons on that date are discovery
statistics, never independent holdout evidence or production recommendations.
"""
import json
import re
from pathlib import Path

from clean_four_modes import rank_modes
from four_mode_archive_api import archived_four_modes
from four_mode_frozen_diagnostic import compare_race
from research_model import probabilities

ROOT = Path(__file__).resolve().parent
VERSION = "CLEAN_FOUR_MODES_V2_PROVISIONAL_UNCALIBRATED"
PROTOCOL = "V2_NATIONAL_TOP2_HEAD_INSERT_RANK3_SHADOW_EXPLORATORY_V1"
MODES = ("narrow", "hit", "balance", "hole")
TOPS = (3, 5, 10)


def candidate(baseline, rates, board):
    """Insert the highest-model-probability ticket of an unrepresented
    top-two national-rate head at rank 3 (max two), drop last ticket(s).

    All inputs must be frozen pre-outcome values, never finish order.
    """
    if (type(rates) is not list or len(rates) != 6 or
            any(type(v) not in (float, int) or not 0 < v < 20 for v in rates)):
        raise ValueError("invalid_six_rates")
    if (type(baseline) is not list or len(baseline) != 10 or
            any(type(x) is not str or not re.fullmatch(r"[1-6]-[1-6]-[1-6]", x)
                or len(set(x.split("-"))) != 3 for x in baseline) or
            len(set(baseline)) != 10):
        raise ValueError("invalid_baseline")
    if (len(board) != 120 or
            len({tuple(boats) for boats, _ in board}) != 120):
        raise ValueError("invalid_board")
    priorities = sorted(range(1, 7), key=lambda head: (-rates[head - 1], head))[:2]
    ordered = list(baseline)
    inserted = []
    for head in priorities:
        if any(int(ticket[0]) == head for ticket in ordered):
            continue
        elig = sorted(
            [("-".join(map(str, boats)), p) for boats, p in board
             if boats[0] == head and "-".join(map(str, boats)) not in ordered],
            key=lambda v: (-v[1], v[0]))
        if not elig:
            raise ValueError("missing_candidate")
        pick = elig[0][0]
        ordered.insert(2 + len(inserted), pick)
        ordered.pop()
        inserted.append(pick)
    if len(ordered) != 10 or len(set(ordered)) != 10:
        raise ValueError("candidate_membership_corrupt")
    return ordered, priorities, inserted


def audit(root=ROOT):
    root = Path(root)
    out = {
        "status": "exploratory_national_top2_head_shadow",
        "protocol": PROTOCOL,
        "formal": False,
        "independent_first_publication_verified": False,
        "independent_holdout_verified": False,
        "retrospective_rule_development": True,
        "valid_forecasts": 0,
        "reproduced_forecasts": 0,
        "candidate_changed_forecasts": 0,
        "paired_results": 0,
        "changed_paired": 0,
        "missing_results": 0,
        "invalid": 0,
        "nonreproduced": 0,
        "topn": {f"top{n}": {"baseline": 0, "candidate": 0,
                            "gained": 0, "lost": 0}
                 for n in TOPS},
        "candidate_changed_on_unpaired_forecasts": 0,
        "candidate_inserted_ticket_total": 0,
        "by_date": {},
        "warning": "Exploratory on observed 2026-11-03 cohort; not prospective validation.",
    }
    directory = root / "four_mode_forecasts"
    if not directory.is_dir():
        out["status"] = "no_forecast_directory"
        return out
    for file in sorted(directory.glob("*.json")):
        code = file.stem
        if not re.fullmatch(r"20[0-9]{10}", code):
            continue
        if file.is_symlink() or file.stat().st_size > 30000:
            out["invalid"] += 1
            continue
        try:
            raw = json.loads(file.read_text(encoding="utf-8"))
            if type(raw) is not dict:
                raise ValueError("bad_json")
        except (OSError, ValueError, TypeError):
            out["invalid"] += 1
            continue
        if raw.get("model_version") != VERSION:
            continue
        out["valid_forecasts"] += 1
        status, archive = archived_four_modes(code, root)
        if status != 200 or archive.get("model_version") != VERSION:
            out["invalid"] += 1
            continue
        try:
            rates = raw["input_national_win_rates"]
            board = probabilities(rates)
            expected = rank_modes(board)
            if any(
                [(ticket["combo"], ticket["p"]) for ticket in archive["modes"][mode]["tickets"]]
                != [(ticket["combo"], ticket["p"]) for ticket in expected[mode]["tickets"]]
                for mode in MODES):
                out["nonreproduced"] += 1
                continue
            baseline = [ticket["combo"] for ticket in archive["modes"]["hit"]["tickets"]]
            test, _, inserted = candidate(baseline, rates, board)
        except (KeyError, TypeError, ValueError, OverflowError, AssertionError):
            out["invalid"] += 1
            continue
        out["reproduced_forecasts"] += 1
        changed = test != baseline
        out["candidate_changed_forecasts"] += int(changed)
        out["candidate_inserted_ticket_total"] += len(inserted)
        result = compare_race(code, root)
        if result.get("status") == "result_unavailable":
            out["missing_results"] += 1
            out["candidate_changed_on_unpaired_forecasts"] += int(changed)
            continue
        if result.get("status") != "historical_comparison_only":
            out["invalid"] += 1
            continue
        winning = result.get("winning_ticket")
        if (type(winning) is not str or
                not re.fullmatch(r"[1-6]-[1-6]-[1-6]", winning) or
                len(set(winning.split("-"))) != 3):
            out["invalid"] += 1
            continue
        out["paired_results"] += 1
        out["changed_paired"] += int(changed)
        date = code[:8]
        if date not in out["by_date"]:
            out["by_date"][date] = {
                "paired": 0, "changed_paired": 0,
                "topn": {f"top{n}": {"baseline": 0, "candidate": 0,
                                    "gained": 0, "lost": 0} for n in TOPS}}
        group = out["by_date"][date]
        group["paired"] += 1
        group["changed_paired"] += int(changed)
        for n in TOPS:
            key = f"top{n}"
            base_hit = winning in baseline[:n]
            candidate_hit = winning in test[:n]
            for item in (out["topn"][key], group["topn"][key]):
                item["baseline"] += int(base_hit)
                item["candidate"] += int(candidate_hit)
                item["gained"] += int(candidate_hit and not base_hit)
                item["lost"] += int(base_hit and not candidate_hit)
    if sum(v["paired"] for v in out["by_date"].values()) != out["paired_results"]:
        raise ValueError("date_partition_mismatch")
    for n in TOPS:
        key = f"top{n}"
        info = out["topn"][key]
        if info["candidate"] - info["baseline"] != info["gained"] - info["lost"]:
            raise ValueError("paired_gain_loss_mismatch")
    out["by_date"] = dict(sorted(out["by_date"].items()))
    return out


if __name__ == "__main__":
    print("V2_NATIONAL_TOP2_HEAD_SHADOW=" + json.dumps(audit(), sort_keys=True))

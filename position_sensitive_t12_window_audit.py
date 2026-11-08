"""Original V2 generation-to-T-12 theoretical window, outcome-blind.

A positive window is only a scheduling opportunity. It is NOT proof a
position-sensitive candidate was ever remotely published in that window.
"""
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path
import argparse
import json
import re

from clean_four_modes import rank_modes
from research_model import probabilities
from four_mode_position_sensitive_shadow import ROOT, BASELINE_VERSION, MODES

SCHEMA = "FOUR_MODE_POSITION_SENSITIVE_T12_FEASIBILITY_INPUT_ONLY_V1"
BUFFER_SECONDS = 90
RACE_DAY = re.compile(r"20[0-9]{6}\Z")


def audit_window(day, root=ROOT):
    if type(day) is not str or not RACE_DAY.fullmatch(day):
        raise ValueError("invalid_day")
    root = Path(root)
    directory = root / "four_mode_forecasts"
    paths = sorted(directory.glob(day+"[0-9][0-9][0-9][0-9].json")) if directory.is_dir() else []
    windows = []
    invalid = Counter()
    late = 0
    under_buffer = 0
    for path in paths:
        try:
            if path.is_symlink() or path.stat().st_size > 30000:
                raise ValueError("unsafe_original_file")
            record = json.loads(path.read_bytes())
            if (type(record) is not dict
                    or record.get("race_code") != path.stem
                    or record.get("schema") != "CLEAN_FOUR_MODES_PREDEADLINE_V1"
                    or record.get("model_version") != BASELINE_VERSION
                    or record.get("validated") is not False
                    or record.get("target_rates_not_proven") is not True):
                raise ValueError("original_identity_invalid")
            deadline = datetime.fromisoformat(record["deadline_jst"])
            generated = datetime.fromisoformat(record["generated_at_jst"])
            received = [datetime.fromisoformat(record[k]) for k in (
                "source_title_received_jst", "source_cards_received_jst")]
            if (any(x.utcoffset() != timedelta(hours=9)
                    for x in (deadline, generated, *received))
                    or max(received) > generated
                    or deadline.strftime("%Y%m%d") != day):
                raise ValueError("source_clock_or_race_day_invalid")
            original = rank_modes(probabilities(record["input_national_win_rates"]))
            for mode in MODES:
                expected = original[mode]["tickets"]
                actual = record["modes"][mode]["tickets"]
                if [(x["combo"], x["p"]) for x in expected] != [
                        (x["combo"], x["p"]) for x in actual]:
                    raise ValueError("original_board_drift")
            # The original's LOCAL generation is not remotely attested.
            seconds = (deadline - timedelta(minutes=12) - generated).total_seconds()
        except (KeyError, TypeError, ValueError, OSError, OverflowError, AssertionError) as exc:
            invalid[str(exc)[:80] or type(exc).__name__] += 1
            continue
        windows.append(seconds)
        late += int(seconds <= 0)
        under_buffer += int(seconds <= BUFFER_SECONDS)
    ordered = sorted(windows)
    def quantile(q):
        if not ordered:
            return None
        return round(ordered[int((len(ordered)-1)*q)], 1)
    return {
        "schema": SCHEMA,
        "status": "historical_theoretical_local_window_only",
        "day_jst": day,
        "archived_files": len(paths),
        "compared": len(windows),
        "excluded": sum(invalid.values()),
        "exclusions": dict(invalid),
        "original_generated_at_or_after_T12": late,
        "less_than_or_equal_90s_local_window": under_buffer,
        "greater_than_90s_local_window": len(windows)-under_buffer,
        "theoretical_window_seconds": {
            "min": quantile(0), "p25": quantile(.25),
            "median": quantile(.5), "p75": quantile(.75),
            "max": quantile(1),
        },
        "independent_remote_original_receipts_verified": False,
        "independent_remote_candidate_receipts_verified": False,
        "actual_candidate_publications": 0,
        "all_official_T12_inputs_verified": False,
        "formal": False,
        "model_improvement_proven": False,
        "promotion_allowed": False,
        "warning": ("Time differences use only local original generated_at and the "
                    "stored deadline. They do NOT show original first Git add, "
                    "GitHub server observation, independent candidate first remote "
                    "receipt, official data authenticity, or actual latency. "
                    "A positive window is scheduling feasibility only. Never use "
                    "to retrospectively qualify Nov-08 races for Nov-09 holdout."),
    }


if __name__ == "__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--day",default="20261108")
    args=p.parse_args()
    print(json.dumps(audit_window(args.day),sort_keys=True))

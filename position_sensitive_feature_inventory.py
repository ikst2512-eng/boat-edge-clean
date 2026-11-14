"""Input-only provenance/feature inventory for frozen #1698 candidate.

This does NOT collect official inputs or try to certify missing receipts.
It inspects the archived original V2 *top-level schema* and enumerates which
race-specific feature fields are actually recorded there, without reading
results. A field's presence is NOT proof it is correct, official, or timely.
"""
from collections import Counter
from datetime import datetime
import json
from pathlib import Path
import re

from clean_four_modes import rank_modes
from research_model import probabilities
from four_mode_position_sensitive_shadow import ROOT, BASELINE_VERSION, MODES

SHA = re.compile(r"[a-f0-9]{64}\Z")
DAY = re.compile(r"20[0-9]{6}\Z")
FIELDS = {
    "national_win_rates_six": "input_national_win_rates",
    "beforeinfo_structured": "beforeinfo",
    "exhibition_six_structured": "exhibition_six",
    "actual_entry_six_structured": "actual_entry_six",
    "motor_six_structured": "motor_six",
    "exhibition_ST_six_structured": "exhibition_ST_six",
    "wind_structured": "wind",
    "wave_height": "wave_height",
    "odds_120_structured": "odds_120",
}


def feature_presence(record):
    """Recorded top-level fields only; no verification or external inference."""
    out = {}
    for label, key in FIELDS.items():
        value = record.get(key)
        if label == "national_win_rates_six":
            out[label] = (type(value) is list and len(value) == 6 and
                          all(type(x) in (float, int) for x in value))
        elif label in ("exhibition_six_structured", "actual_entry_six_structured",
                       "motor_six_structured", "exhibition_ST_six_structured"):
            out[label] = type(value) is list and len(value) == 6
        elif label == "odds_120_structured":
            out[label] = type(value) is dict and len(value) == 120
        elif label == "wind_structured":
            out[label] = type(value) is dict and bool(value)
        elif label == "wave_height":
            out[label] = type(value) in (int, float)
        elif label == "beforeinfo_structured":
            out[label] = type(value) is dict and bool(value)
    sha = record.get("source_sha256")
    out["public_title_card_digests_recorded"] = (
        type(sha) is dict
        and all(isinstance(sha.get(key), str) and SHA.fullmatch(sha[key])
                for key in ("title", "race_cards"))
    )
    # A candidate's independent *first remote receipt* CANNOT be established
    # from a statement in the original V2 file. It needs external Git/Actions
    # provenance with immutable first-add records.
    return out


def audit_feature_day(day="20261108", root=ROOT):
    if type(day) is not str or not DAY.fullmatch(day):
        raise ValueError("invalid_day")
    root = Path(root)
    directory = root / "four_mode_forecasts"
    paths = sorted(directory.glob(day + "[0-9][0-9][0-9][0-9].json")) if directory.is_dir() else []
    tally = Counter()
    fields = Counter()
    reasons = Counter()
    for path in paths:
        try:
            if path.is_symlink() or path.stat().st_size > 30000:
                raise ValueError("untrusted_original_path")
            original = json.loads(path.read_bytes())
            if (type(original) is not dict or original.get("race_code") != path.stem
                    or original.get("schema") != "CLEAN_FOUR_MODES_PREDEADLINE_V1"
                    or original.get("model_version") != BASELINE_VERSION
                    or original.get("target_rates_not_proven") is not True
                    or original.get("validated") is not False):
                raise ValueError("invalid_original_record")
            created = datetime.fromisoformat(original["generated_at_jst"])
            deadline = datetime.fromisoformat(original["deadline_jst"])
            if (created.utcoffset() is None or deadline.utcoffset() is None
                    or not created < deadline):
                raise ValueError("invalid_original_clock")
            rates = original["input_national_win_rates"]
            board = rank_modes(probabilities(rates))
            for mode in MODES:
                old = original["modes"][mode]["tickets"]
                if ([(x["combo"], x["p"]) for x in old] !=
                        [(x["combo"], x["p"]) for x in board[mode]["tickets"]]):
                    raise ValueError("original_board_replay_failed")
            recorded = feature_presence(original)
            if not recorded["national_win_rates_six"]:
                raise ValueError("missing_six_rates")
        except (KeyError, ValueError, TypeError, OSError, OverflowError, AssertionError) as ex:
            tally["excluded"] += 1
            reasons[str(ex)[:80] or type(ex).__name__] += 1
            continue
        tally["compared"] += 1
        for key, present in recorded.items():
            fields[key] += int(present)
    return {
        "schema": "FOUR_MODE_POSITION_SENSITIVE_ARCHIVE_FEATURE_INVENTORY_V1",
        "status": "historical_recorded_fields_only_not_official_certification",
        "day_jst": day,
        "archived_files": len(paths),
        "compared": tally["compared"],
        "excluded": tally["excluded"],
        "exclusion_reasons": dict(reasons),
        "recorded_top_level_feature_counts": {
            key: fields.get(key, 0)
            for key in tuple(FIELDS) + ("public_title_card_digests_recorded",)
        },
        "model_consumed_features": ["input_national_win_rates"],
        "actual_entry_exhibition_ST_motor_wind_applied_by_frozen_selector": False,
        "formal_official_beforeinfo_six_odds120_verified": False,
        "independent_candidate_first_remote_receipt_verified": False,
        "production_changed": False,
        "formal": False,
        "model_improvement_proven": False,
        "warning": (
            "Archive schema-only inventory, no official source authenticity "
            "check and no external receipt lookup. Even structured fields would "
            "not prove official identity or T-12 timing. No confirmed finish or "
            "payout was opened. This cannot certify a future forward cohort."
        ),
    }


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--day", default="20261108")
    args = p.parse_args()
    print(json.dumps(audit_feature_day(args.day), sort_keys=True))

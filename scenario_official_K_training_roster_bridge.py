"""Offline #1692 original-K replay -> #1710 future exhibition-roster research.

The actual K bytes and 92-day parser are supplied independently. This code
DOES NOT copy the #1692 parser, does NOT treat postrace actual entry as future
entry, and does NOT use K race outcomes from October as training inputs.
Any result is research-only; the future triple may itself be a synthetic
fixture and has no first-remote forecast receipt.
"""
from collections import Counter
from datetime import date, timedelta
import hashlib
import math
from pathlib import Path
import re

from scenario_escape_prior_first_head_sensitivity import (
    HISTORY_SCHEMA, K92_ZIP_SHA256,
)
from scenario_exhibition_course_head_research import (
    prepare_course_holder_head_study,
)

TRAIN_FIRST = date(2026, 8, 1)
TRAIN_LAST = date(2026, 9, 30)
HIST_LAST = date(2026, 10, 31)
DAY_COUNT = 92
FULL_N = 13815
TRAIN_N = 9241
TEST_N = 4574
VENUE_SMOOTH = 40
REPLAY_SCHEMA = "OFFLINE_ORIGINAL_K_EXHIBITION_HOLDER_JOIN_RESEARCH_V1"
_SHA = re.compile(r"[0-9a-f]{64}\Z")
_REG = re.compile(r"[0-9]{4}\Z")


def _training_history(eligible_rows, daily_sha, race_code, projection):
    """Validate original-K parser output then construct unpromoted K summary.

    Called only AFTER the outer wrapper has independently SHA-checked the
    original ZIP and invoked the existing #1692 raw-byte parser.
    """
    if (type(race_code) is not str
            or re.fullmatch(r"20[0-9]{10}", race_code) is None
            or race_code[:8] <= "20261031"
            or type(eligible_rows) is not list or len(eligible_rows) != FULL_N
            or type(daily_sha) is not list or len(daily_sha) != DAY_COUNT
            or type(projection) is not dict
            or projection.get("race_code") != race_code):
        raise ValueError("K_replay_target_or_full_cohort_invalid")
    days = [TRAIN_FIRST + timedelta(days=i) for i in range(DAY_COUNT)]
    if (type(x) is not dict or x.get("day") != d.strftime("%Y%m%d")
            or not all(type(x.get(k)) is str and _SHA.fullmatch(x[k])
                       for k in ("official_raw_lzh_sha256",
                                 "decoded_text_sha256"))
            for x, d in zip(daily_sha, days)):
        raise ValueError("K_replay_original_day_SHA_incomplete")
    train = []
    holdout_count = 0
    for r in eligible_rows:
        if type(r) is not dict or set(r) != {
                "day", "month", "venue", "c1_registration",
                "c2_registration", "boat1_registration",
                "boat2_registration", "boat1_actual_course",
                "boat2_actual_course", "c1_escape", "c2_sashi"}:
            raise ValueError("K_replay_eligible_row_shape_mismatch")
        day = r["day"]
        if (type(day) is not str
                or re.fullmatch(r"2026(?:08|09|10)[0-9]{2}", day) is None):
            raise ValueError("K_replay_row_day_outside_frozen_period")
        try:
            d = date.fromisoformat(day[:4]+"-"+day[4:6]+"-"+day[6:8])
        except ValueError as exc:
            raise ValueError("K_replay_row_day_invalid") from exc
        if (d < TRAIN_FIRST or d > HIST_LAST
                or r["month"] != day[4:6]
                or type(r["venue"]) is not str
                or re.fullmatch(r"0[1-9]|1[0-9]|2[0-4]", r["venue"]) is None
                or any(type(r[key]) is not str
                       or _REG.fullmatch(r[key]) is None
                       for key in ("c1_registration", "c2_registration",
                                   "boat1_registration", "boat2_registration"))
                or type(r["c1_escape"]) is not int
                or r["c1_escape"] not in (0, 1)
                or type(r["c2_sashi"]) is not int
                or r["c2_sashi"] not in (0, 1)
                or type(r["boat1_actual_course"]) is not int
                or type(r["boat2_actual_course"]) is not int
                or r["boat1_actual_course"] not in range(1, 7)
                or r["boat2_actual_course"] not in range(1, 7)):
            raise ValueError("K_replay_row_original_semantics_invalid")
        if d <= TRAIN_LAST:
            train.append(r)
        else:
            holdout_count += 1
    if len(train) != TRAIN_N or holdout_count != TEST_N:
        raise ValueError("K_replay_frozen_train_holdout_size_changed")

    venue = race_code[8:10]
    rows = projection.get("exhibition_features_by_boat")
    if type(rows) is not list or len(rows) != 6:
        raise ValueError("K_replay_future_exhibition_six_missing")
    one = [r for r in rows
           if type(r) is dict and r.get("exhibition_course_only") == 1]
    if len(one) != 1 or type(one[0].get("registration_id")) is not str:
        raise ValueError("K_replay_future_course_holder_missing")
    holder = one[0]["registration_id"]
    if _REG.fullmatch(holder) is None:
        raise ValueError("K_replay_future_course_holder_registration_invalid")
    roster = [{
        "boat": r["boat"], "registration": r["registration_id"],
        "exhibition_course": r["exhibition_course_only"]
    } for r in rows]
    if ([r["boat"] for r in roster] != list(range(1, 7))
            or {r["exhibition_course"] for r in roster} != set(range(1, 7))
            or len({r["registration"] for r in roster}) != 6):
        raise ValueError("K_replay_future_exhibition_roster_invalid")

    # Exactly #1692's published historical model definition:
    # 8-9 train global rate -> venue 40 pseudo-count prior ->
    # per-athlete C1 venue-centered residual, shrunk by (n+40).
    global_wins = sum(r["c1_escape"] for r in train)
    by_venue = Counter(r["venue"] for r in train)
    venue_wins = Counter()
    for r in train:
        venue_wins[r["venue"]] += r["c1_escape"]
    if len(by_venue) != 24 or any(by_venue[f"{v:02d}"] == 0
                                 for v in range(1, 25)):
        raise ValueError("K_replay_24_venues_missing")
    global_p = global_wins / TRAIN_N
    def prior(v):
        return ((venue_wins[v] + VENUE_SMOOTH * global_p)
                / (by_venue[v] + VENUE_SMOOTH))
    # Crucial: in the historical TRAIN set, C1 identity is the already
    # confirmed ACTUAL course-one holder. For the FUTURE target, identity
    # comes only from its independently parsed PRE-RACE exhibition roster.
    athlete_train = [r for r in train
                     if r["c1_registration"] == holder]
    residual = math.fsum(
        r["c1_escape"] - prior(r["venue"]) for r in athlete_train)
    return {
        "schema": HISTORY_SCHEMA,
        "race_code": race_code,
        "historic_training_end_date_jst": "2026-09-30",
        "official_K_replay_zip_sha256_claim": K92_ZIP_SHA256,
        "venue_code": venue,
        "national_training_race_count": TRAIN_N,
        "national_training_C1_escape_count": global_wins,
        "venue_training_race_count": by_venue[venue],
        "venue_training_C1_escape_count": venue_wins[venue],
        "C1_athlete_registration": holder,
        "C1_athlete_training_race_count": len(athlete_train),
        "C1_athlete_venue_centered_residual_sum": residual,
        "exhibition_entry_roster_by_boat": roster,
        "training_used_outcomes_after_target": False,
        "official_source_receipt_independently_authenticated": False,
        "exhibition_is_final_race_entry": False,
        "outcomes_from_target_race_read": False,
    }


def replay_K_and_join_future_exhibition(
        zip_path, official_rows_callback, audit, source_bundle,
        candidate, projection):
    """Locally check 92-day source K, then join only the pre-race C1 holder.

    Caller-supplied #1692 official_rows is identity-pinned outside this
    function by the CI workflow. Function input cannot attest that the
    caller's alleged future HTTP sources were independently first received.
    """
    path = Path(zip_path)
    if (path.is_symlink() or not path.is_file()
            or path.stat().st_size != 3398466
            or not callable(official_rows_callback)):
        raise ValueError("K_original_zip_or_parser_unavailable")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != K92_ZIP_SHA256:
        raise ValueError("K_original_ZIP_SHA256_mismatch")
    originals = official_rows_callback(path)
    if (type(originals) is not tuple or len(originals) != 3
            or originals[1] != digest):
        raise ValueError("K_parser_digest_or_originals_invalid")
    rows, _, daily_sha = originals
    history = _training_history(
        rows, daily_sha, projection.get("race_code"), projection)
    prepared = prepare_course_holder_head_study(
        audit, source_bundle, candidate, projection, history)
    if (prepared["history_source_join"]["history_claimed_input_sha256"]
            != _digest_history(history)):
        raise ValueError("K_derived_history_handoff_mismatch")
    return {
        "schema": REPLAY_SCHEMA,
        "target_race_code": prepared["race_code"],
        "original_K_ZIP_SHA256": digest,
        "original_K_local_SHA_verified": True,
        "original_K_92_daily_bytes_checked_by_external_parser": True,
        "training_eligible_races": TRAIN_N,
        "historical_holdout_races_not_used_to_train": TEST_N,
        "exhibition_course1_holder_registration": history[
            "C1_athlete_registration"],
        "training_holder_C1_start_count": history[
            "C1_athlete_training_race_count"],
        "training_holder_C1_residual": history[
            "C1_athlete_venue_centered_residual_sum"],
        "history_claimed_input_sha256": _digest_history(history),
        "source_handoff_sha256": prepared["handoff_digest_sha256"],
        "history": history,
        "prepared_study": prepared,
        "numeric_history_injected_into_four_mode_head": False,
        "future_official_HTTP_first_received_independently_verified": False,
        "future_first_remote_forecast_save_verified": False,
        "actual_future_race_entry_verified": False,
        "formal": False, "production_changed": False,
        "accuracy_improvement_proven": False,
    }


def _digest_history(history):
    import json
    return hashlib.sha256(json.dumps(
        history, sort_keys=True, ensure_ascii=False, allow_nan=False,
        separators=(",", ":")).encode("utf-8")).hexdigest()

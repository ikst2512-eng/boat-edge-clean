#!/usr/bin/env python3
"""Join a pinned four-mode forecast to same-race BEFOREINFO and odds API bytes.

Research only. Each original's SHA, race identity and UTC/JST receipt timing
are checked. This is NOT independent official odds-source certification,
does NOT establish a racecard original, and never backfills a forecast with
observations received after that forecast was generated.
"""
from __future__ import annotations

import argparse
import base64
import datetime as dt
import hashlib
import itertools
import json
import math
import re
import subprocess
from pathlib import Path

if __package__:
    from .research_official_beforeinfo_wind_receipt_gate import verify as verify_beforeinfo
else:
    from research_official_beforeinfo_wind_receipt_gate import verify as verify_beforeinfo

EXPECTED_CODE = "202611040111"
MAIN_COMMIT_RE = re.compile(r"^[a-f0-9]{40}$")
COMBOS = {"-".join(t) for t in itertools.permutations("123456", 3)}
JST = dt.timezone(dt.timedelta(hours=9))


def checked_jst(raw: object, field: str) -> dt.datetime:
    if not isinstance(raw, str):
        raise ValueError("missing_timestamp:" + field)
    try:
        parsed = dt.datetime.fromisoformat(raw)
    except ValueError as exc:
        raise ValueError("invalid_timestamp:" + field) from exc
    if parsed.utcoffset() != dt.timedelta(hours=9):
        raise ValueError("timestamp_not_jst:" + field)
    return parsed


def checked_utc(raw: object, field: str) -> dt.datetime:
    if not isinstance(raw, str):
        raise ValueError("missing_timestamp:" + field)
    try:
        parsed = dt.datetime.fromisoformat(raw)
    except ValueError as exc:
        raise ValueError("invalid_timestamp:" + field) from exc
    if parsed.utcoffset() != dt.timedelta():
        raise ValueError("timestamp_not_utc:" + field)
    return parsed


def read_git_forecast(commit: str, code: str) -> bytes:
    if not MAIN_COMMIT_RE.fullmatch(commit):
        raise ValueError("invalid_pinned_git_commit")
    if code != EXPECTED_CODE:
        raise ValueError("not_the_frozen_race")
    check = subprocess.run(["git", "cat-file", "-t", commit], check=False,
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=25)
    if check.returncode != 0 or check.stdout.strip() != b"commit":
        raise ValueError("pinned_forecast_commit_unavailable")
    path = "four_mode_forecasts/" + code + ".json"
    proc = subprocess.run(["git", "show", commit + ":" + path], check=False,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=25)
    if proc.returncode != 0:
        raise ValueError("pinned_forecast_missing")
    return proc.stdout


def verify_odds_replay(replay: dict, race_code: str, official_cutoff: dt.datetime) -> dict:
    """Checks transport bytes and combinations, NOT an original BOAT RACE odds origin."""
    if (replay.get("date") != race_code[:8]
            or replay.get("formal") is not False
            or replay.get("formal_t12_certified") is not False
            or replay.get("trigger", {}).get("event") != "local_manual"):
        raise ValueError("odds_replay_origin_or_formal_state_mismatch")
    matches = [x for x in replay.get("samples", [])
               if x.get("race_code") == race_code]
    if len(matches) != 1:
        raise ValueError("odds_replay_race_not_unique")
    sample = matches[0]
    if (sample.get("final_state") != "valid_200"
            or len(sample.get("attempts", [])) != 1):
        raise ValueError("odds_replay_not_one_valid_receipt")
    start = sample["attempts"][0]
    if start.get("http") != 200 or start.get("state") != "valid_200":
        raise ValueError("odds_http_not_verified_200")
    started = checked_utc(start.get("started_at_utc"), "odds_started")
    finished = checked_utc(start.get("finished_at_utc"), "odds_finished")
    if finished < started:
        raise ValueError("odds_http_clock_reversed")
    try:
        original = base64.b64decode(start["response_base64"], validate=True)
    except (ValueError, TypeError) as exc:
        raise ValueError("odds_response_base64_invalid") from exc
    if not 0 < len(original) < 100_000:
        raise ValueError("odds_http_bytes_size_invalid")
    sha = hashlib.sha256(original).hexdigest()
    if start.get("response_sha256") != sha:
        raise ValueError("odds_response_SHA_mismatch")
    response = json.loads(original)
    if (response.get("ok") is not True
            or str(response.get("hd")) != race_code[:8]
            or f"{int(response.get('jcd')):02d}" != race_code[8:10]
            or f"{int(response.get('rno')):02d}" != race_code[10:12]):
        raise ValueError("odds_response_race_identity_mismatch")
    odds = response.get("odds")
    if (not isinstance(odds, dict) or set(odds) != COMBOS or
            any(type(v) not in (int, float) or not math.isfinite(v) or v <= 0
                for v in odds.values())):
        raise ValueError("odds_120_tri_combinations_invalid")
    fetched = checked_utc(response.get("fetched_at"), "odds_upstream_fetched_at")
    if fetched > finished or fetched < started:
        raise ValueError("odds_response_fetched_at_outside_http_interval")
    deadline = checked_jst(sample.get("source_deadline_jst"), "odds_public_deadline")
    if deadline - dt.timedelta(minutes=12) != official_cutoff:
        raise ValueError("odds_public_deadline_disagrees_with_official")
    # HTTP transport is an API replay, NOT a raw official odds original.
    return {
        "original_http_response_sha256": sha,
        "raw_http_response_bytes": len(original),
        "http_started_jst": started.astimezone(JST).isoformat(),
        "http_received_jst": finished.astimezone(JST).isoformat(),
        "source_fetched_jst": fetched.astimezone(JST).isoformat(),
        "120_trifecta_combos_in_api_response_verified": True,
        "received_before_t12": finished <= official_cutoff,
        "source_classification": "public_API_replay_not_independent_official_odds_original",
        "official_odds_source_raw_verified": False,
        "source_received_datetime": finished.astimezone(JST),
    }


def join(race_code: str, forecast_raw: bytes, before_raw: bytes,
         before_manifest: dict, replay: dict) -> dict:
    if race_code != EXPECTED_CODE:
        raise ValueError("research_race_code_not_frozen")
    weather = verify_beforeinfo(before_raw, before_manifest, race_code)
    cutoff = checked_jst(weather["t12_cutoff_jst"], "official_cutoff")
    forecast = json.loads(forecast_raw)
    if (forecast.get("race_code") != race_code
            or forecast.get("schema") != "CLEAN_FOUR_MODES_PREDEADLINE_V1"
            or forecast.get("status") != "provisional"
            or forecast.get("validated") is not False):
        raise ValueError("saved_forecast_identity_or_provenance_invalid")
    forecast_deadline = checked_jst(forecast.get("deadline_jst"), "forecast_deadline")
    if forecast_deadline - dt.timedelta(minutes=12) != cutoff:
        raise ValueError("forecast_deadline_disagrees_with_official")
    created = checked_jst(forecast.get("generated_at_jst"), "forecast_created")
    cards = checked_jst(forecast.get("source_cards_received_jst"), "forecast_cards_received")
    title = checked_jst(forecast.get("source_title_received_jst"), "forecast_title_received")
    if title > created or cards > created:
        raise ValueError("forecast_generated_before_own_input_receipts")
    odds = verify_odds_replay(replay, race_code, cutoff)
    odds_received = odds.pop("source_received_datetime")
    weather_received = checked_jst(weather["http_received_at_jst"], "weather_received")
    if weather["received_at_or_before_t12"] != (weather_received <= cutoff):
        raise ValueError("official_weather_gate_disagrees_with_time")
    forecast_and_two_http_receipts_t12 = (created <= cutoff and
                                weather_received <= cutoff and odds_received <= cutoff)
    two_http_receipts_by_forecast = (weather_received <= created and odds_received <= created)
    return {
        "schema": "BOAT_EDGE_SAME_RACE_T12_TEMPORAL_JOIN_RESEARCH_V1",
        "classification": "same_race_three_receipts_not_official_three_originals_or_forecast_certification",
        "race_code": race_code,
        "forecast_raw_sha256": hashlib.sha256(forecast_raw).hexdigest(),
        "forecast_created_at_jst": created.isoformat(),
        "forecast_cards_received_at_jst": cards.isoformat(),
        "forecast_title_received_at_jst": title.isoformat(),
        "source_cutoff_t12_jst": cutoff.isoformat(),
        "source_official_deadline_jst": forecast_deadline.isoformat(),
        "forecast_generated_by_t12": created <= cutoff,
        "official_beforeinfo_received_by_t12": weather_received <= cutoff,
        "api_odds_received_by_t12": odds_received <= cutoff,
        "forecast_and_two_http_receipts_before_t12": forecast_and_two_http_receipts_t12,
        "official_beforeinfo_received_before_forecast_generation": weather_received <= created,
        "api_odds_received_before_forecast_generation": odds_received <= created,
        "two_http_receipts_received_by_forecast_generation": two_http_receipts_by_forecast,
        "weather_receipt_seconds_after_forecast_generation": round((weather_received-created).total_seconds(), 3),
        "odds_receipt_seconds_after_forecast_generation": round((odds_received-created).total_seconds(), 3),
        "official_beforeinfo": {
            k: weather[k] for k in ("source_sha256", "source_bytes",
                "http_received_at_jst", "wind_speed_raw", "wave_height_raw",
                "measurement_label_raw", "exact_weather_measurement_timestamp_verified",
                "absolute_wind_compass_verified")
        },
        "public_odds_api_replay": odds,
        "cards_original_SHA_receipt_independently_verified": False,
        "official_odds_original_SHA_receipt_independently_verified": False,
        "independent_three_official_originals_matched": False,
        "race_entry_final_verified": False,
        "formal_T12_forecast_eligible": False,
        "wind_feature_impact_on_forecast_proven": False,
        "production_adoption_authorized": False,
        "limitations": [
            "Same race and same official deadline does not imply observations were used in earlier forecast.",
            "Beforeinfo records weather label '10R時点', not 11R same-time measurement.",
            "API odds replay is not an independent official odds HTTP original or audited upstream chain.",
            "Forecast title/cards SHA fields are not independently rechecked original bytes.",
            "No official pre-race source is inferred from postrace K archives.",
        ],
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source-main-sha", required=True)
    ap.add_argument("--beforeinfo-json", type=Path, required=True)
    ap.add_argument("--beforeinfo-manifest", type=Path, required=True)
    ap.add_argument("--odds-api-replay", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    result = join(
        EXPECTED_CODE, read_git_forecast(args.source_main_sha, EXPECTED_CODE),
        args.beforeinfo_json.read_bytes(),
        json.loads(args.beforeinfo_manifest.read_text(encoding="utf-8")),
        json.loads(args.odds_api_replay.read_text(encoding="utf-8"))
    )
    result["pinned_main_commit_sha"] = args.source_main_sha
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True)+"\n",
                        encoding="utf-8")
    print(json.dumps({
        "race_code": result["race_code"],
        "forecast_and_two_http_receipts_before_t12": result["forecast_and_two_http_receipts_before_t12"],
        "weather_before_forecast_generation": result["official_beforeinfo_received_before_forecast_generation"],
        "api_odds_before_forecast_generation": result["api_odds_received_before_forecast_generation"],
        "formal_T12_forecast_eligible": False,
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()

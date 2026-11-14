#!/usr/bin/env python3
"""Verify one immutable official beforeinfo raw weather receipt, research-only.

This checks observed HTTP bytes before T-12, NOT a first-add formal four-mode
forecast or its independent entry/odds originals. The published 'measuretime'
may refer to an earlier race (e.g. '10R時点') and must not be given a fabricated
observation clock or mapped to an absolute compass bearing without evidence.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
from pathlib import Path

JST = dt.timezone(dt.timedelta(hours=9))


def jst_timestamp(v: object) -> dt.datetime:
    if not isinstance(v, str):
        raise ValueError("missing_receipt_timestamp")
    value = dt.datetime.fromisoformat(v)
    if value.utcoffset() != dt.timedelta(hours=9):
        raise ValueError("receipt_timestamp_must_be_JST")
    return value


def verify(original: bytes, manifest: dict, expected_code: str) -> dict:
    if (not isinstance(expected_code, str) or
            not re.fullmatch(r"20[0-9]{10}", expected_code)):
        raise ValueError("invalid_expected_race_code")
    if manifest.get("race_code") != expected_code:
        raise ValueError("source_receipt_race_code_mismatch")
    if not (isinstance(manifest.get("sha256"), str) and
            manifest["sha256"] == hashlib.sha256(original).hexdigest() and
            manifest.get("bytes") == len(original)):
        raise ValueError("original_beforeinfo_sha_or_bytes_mismatch")
    if (not isinstance(manifest.get("url"), str) or
            not manifest["url"].startswith("https://www.boatrace.jp/owsp/sp/spdata?type=beforeinfo&")):
        raise ValueError("untrusted_official_beforeinfo_source_url")
    started = jst_timestamp(manifest.get("request_started_at_jst"))
    received = jst_timestamp(manifest.get("received_at_jst"))
    if started > received or started.date().strftime("%Y%m%d") != expected_code[:8]:
        raise ValueError("invalid_source_acquisition_chronology")
    payload = json.loads(original)
    main = payload["maindata"]
    if (str(main.get("hd")) != expected_code[:8] or
            f"{int(main.get('jcd')):02d}" != expected_code[8:10] or
            f"{int(main.get('rno')):02d}" != expected_code[10:12]):
        raise ValueError("original_beforeinfo_identity_mismatch")
    deadline = main.get("deadline")
    if not isinstance(deadline, str) or not re.fullmatch(r"[0-2][0-9]:[0-5][0-9]", deadline):
        raise ValueError("invalid_original_deadline")
    hour, minute = map(int, deadline.split(":"))
    if hour > 23:
        raise ValueError("invalid_original_hour")
    deadline_at = dt.datetime.combine(received.date(), dt.time(hour, minute), JST)
    cutoff = deadline_at - dt.timedelta(minutes=12)
    boats = main.get("teiinfolist")
    starts = main.get("sttenjiinfolist")
    if (not isinstance(boats, list) or len(boats) != 6 or
            {str(x.get("teino")) for x in boats} != set("123456") or
            not isinstance(starts, list) or len(starts) != 6 or
            {str(x.get("teino")) for x in starts} != set("123456")):
        raise ValueError("six_boat_original_beforeinfo_unverified")
    weather = main.get("weatherinfo")
    if not isinstance(weather, dict):
        raise ValueError("official_weatherinfo_missing")
    wind = weather.get("wind")
    wave = weather.get("wave")
    if (not isinstance(wind, str) or not re.fullmatch(r"(?:0|[1-9][0-9]?)m", wind)
            or not isinstance(wave, str) or
            not re.fullmatch(r"(?:0|[1-9][0-9]?)cm", wave)):
        raise ValueError("official_weather_units_invalid")
    raw_measuretime = weather.get("measuretime")
    if not isinstance(raw_measuretime, str) or not raw_measuretime.strip():
        raise ValueError("missing_weather_measurement_label")
    before_cutoff = received <= cutoff
    return {
        "schema": "BOAT_EDGE_OFFICIAL_BEFOREINFO_WIND_RECEIPT_V1",
        "classification": "raw_official_predeadline_weather_observation_not_forecast_certification",
        "race_code": expected_code,
        "source_sha256": manifest["sha256"],
        "source_bytes": len(original),
        "http_request_started_at_jst": started.isoformat(),
        "http_received_at_jst": received.isoformat(),
        "deadline_from_original_jst": deadline_at.isoformat(),
        "t12_cutoff_jst": cutoff.isoformat(),
        "received_at_or_before_t12": before_cutoff,
        "wind_speed_raw": wind,
        "wave_height_raw": wave,
        "raw_wind_direction_code": weather.get("winddirec"),
        "raw_north_direction_code": weather.get("northdirec"),
        "measurement_label_raw": raw_measuretime,
        "absolute_wind_compass_verified": False,
        "exact_weather_measurement_timestamp_verified": False,
        "six_boat_ids_and_start_rows_observed": True,
        "independent_3_origins_complete": False,
        "T12_forecast_certified": False,
        "can_join_20261106_08_forecast_cohort": False,
        "production_wind_feature_authorized": False,
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--beforeinfo", required=True, type=Path)
    p.add_argument("--manifest", required=True, type=Path)
    p.add_argument("--race-code", default="202611040111")
    p.add_argument("--out", required=True, type=Path)
    a = p.parse_args()
    report = verify(a.beforeinfo.read_bytes(),
                    json.loads(a.manifest.read_text(encoding="utf-8")),
                    a.race_code)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True)+"\n", encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("race_code", "received_at_or_before_t12",
          "wind_speed_raw", "measurement_label_raw", "T12_forecast_certified")}, ensure_ascii=False))
    if not report["received_at_or_before_t12"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

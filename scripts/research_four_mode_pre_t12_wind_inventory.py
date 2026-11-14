#!/usr/bin/env python3
"""Immutable Git forecast inventory for pre-T12 weather provenance gaps.

A forecast record and pre-deadline source-cards timestamp do not prove that
official weather or six-boat exhibition was received before the T-12 cutoff.
Research-only; refuses to mark any forecast as T-12 wind-eligible from metadata
alone. Never loads postrace official K results as input or edits forecasts.
"""
from __future__ import annotations

import argparse
import collections
import datetime as dt
import hashlib
import json
import re
import subprocess
from pathlib import Path

JST = dt.timezone(dt.timedelta(hours=9))
KEYS_WEATHER = {"wind", "windspeed", "wind_speed", "winddirection",
                "wind_direction", "weather", "風速", "風向", "気象"}
VALID_FORECAST = re.compile(r"^four_mode_forecasts/(20[0-9]{10})\.json$")
COMMIT_SHA = re.compile(r"^[a-f0-9]{40}$")


def timestamp(value: object) -> dt.datetime:
    if not isinstance(value, str):
        raise ValueError("missing_timestamp")
    try:
        result = dt.datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("unparseable_timestamp") from exc
    if result.utcoffset() != dt.timedelta(hours=9):
        raise ValueError("timestamp_not_explicit_JST")
    return result


def has_weather_field(node: object) -> bool:
    if isinstance(node, dict):
        if any(re.sub(r"[^a-z_]", "", str(k).lower()) in KEYS_WEATHER or
               str(k) in KEYS_WEATHER for k in node):
            return True
        return any(has_weather_field(x) for x in node.values())
    if isinstance(node, list):
        return any(has_weather_field(x) for x in node)
    return False


def analyze_records(records: list[tuple[str, dict, str]], start: dt.date,
                    end: dt.date) -> dict:
    if not dt.date(2026, 11, 6) <= start <= end <= dt.date(2026, 11, 8):
        raise ValueError("outside_frozen_study_cohort")
    rows, by_day = [], collections.defaultdict(lambda: collections.Counter())
    observed_codes = set()
    digests = []
    for path, record, raw_sha256 in sorted(records):
        m = VALID_FORECAST.fullmatch(path)
        if not m:
            raise ValueError("unexpected_forecast_path:" + path)
        race_code = m.group(1)
        date = dt.date.fromisoformat(race_code[:4]+"-"+race_code[4:6]+"-"+race_code[6:8])
        if date < start or date > end or race_code in observed_codes:
            raise ValueError("duplicate_or_out_of_period_forecast:" + race_code)
        observed_codes.add(race_code)
        if record.get("race_code") != race_code:
            raise ValueError("forecast_identity_mismatch:" + race_code)
        if record.get("schema") != "CLEAN_FOUR_MODES_PREDEADLINE_V1":
            raise ValueError("unrecognized_forecast_schema:" + race_code)
        deadline = timestamp(record.get("deadline_jst"))
        created = timestamp(record.get("generated_at_jst"))
        title = timestamp(record.get("source_title_received_jst"))
        cards = timestamp(record.get("source_cards_received_jst"))
        if deadline.date() != date:
            raise ValueError("deadline_day_disagrees_with_race_code:" + race_code)
        cutoff = deadline - dt.timedelta(minutes=12)
        source_in_time = title <= cutoff and cards <= cutoff
        generated_in_time = source_in_time and max(title, cards) <= created <= cutoff
        has_wind = has_weather_field(record)
        beforeinfo = record.get("beforeinfo")
        has_beforeinfo_payload = isinstance(beforeinfo, dict)
        # This is a metadata-only snapshot: it does not carry independently
        # received raw official wind bytes, source SHA, and intake receipt.
        # Never infer a confirmed wind observation from generic source_sha256.
        kind = (beforeinfo if isinstance(beforeinfo, str) else
                "structured_unverified" if has_beforeinfo_payload else "missing")
        d = by_day[date.isoformat()]
        d["records"] += 1
        d["title_and_cards_before_T12"] += int(source_in_time)
        d["forecast_and_sources_before_T12"] += int(generated_in_time)
        d["weather_field_key_present"] += int(has_wind)
        d["beforeinfo_structured_payload_present"] += int(has_beforeinfo_payload)
        d["beforeinfo_absent_or_placeholder"] += int(not has_beforeinfo_payload)
        d["validated_true"] += int(record.get("validated") is True)
        d["provisional_status"] += int(record.get("status") == "provisional")
        d["official_wind_original_bytes_SHA_receipt_verified"] += 0
        d["formal_T12_wind_prediction_eligible"] += 0
        digests.append(path + ":" + raw_sha256)
        rows.append({
            "race_code": race_code, "deadline_jst": deadline.isoformat(),
            "cutoff_T12_jst": cutoff.isoformat(),
            "title_and_cards_before_T12": source_in_time,
            "forecast_and_sources_before_T12": generated_in_time,
            "beforeinfo_field_type": kind,
            "weather_field_key_present": has_wind,
            "official_wind_raw_receipt_verified": False,
            "T12_wind_eligible": False,
            "raw_forecast_sha256": raw_sha256,
        })
    if not rows:
        raise ValueError("empty_frozen_prospective_cohort")
    by_day_out = {day: dict(by_day.get(day, {}))
                  for day in [(start+dt.timedelta(days=i)).isoformat()
                              for i in range((end-start).days+1)]}
    n = len(rows)
    totals = collections.Counter()
    for counts in by_day.values():
        totals.update(counts)
    return {
        "schema": "BOAT_EDGE_FOUR_MODE_FROZEN_WIND_RECEIPT_INVENTORY_V1",
        "classification": "metadata_gap_audit_not_official_weather_reconstruction",
        "source_period": f"{start}/{end}",
        "forecast_records": n,
        "title_cards_received_before_T12": totals["title_and_cards_before_T12"],
        "forecast_and_title_cards_before_T12": totals["forecast_and_sources_before_T12"],
        "weather_field_key_present": totals["weather_field_key_present"],
        "beforeinfo_structured_payload_present": totals["beforeinfo_structured_payload_present"],
        "beforeinfo_absent_or_placeholder": totals["beforeinfo_absent_or_placeholder"],
        "forecast_validated_true": totals["validated_true"],
        "source_original_official_wind_bytes_verified": 0,
        "official_weather_T12_eligible_races": 0,
        "result_wind_is_not_prerace_wind": True,
        "no_automatic_main_or_model_changes": True,
        "missing_metadata_does_not_prove_external_source_absence": True,
        "by_day": by_day_out,
        "source_record_set_sha256": hashlib.sha256("\n".join(digests).encode()).hexdigest(),
        "records": rows,
    }


def git_output(*args: str) -> bytes:
    proc = subprocess.run(["git", *args], stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, check=False, timeout=40)
    if proc.returncode:
        raise ValueError("immutable_source_git_read_failed:" + " ".join(args[:2]))
    return proc.stdout


def read_git_snapshot(commit: str, start: dt.date, end: dt.date):
    if not COMMIT_SHA.fullmatch(commit):
        raise ValueError("expected_pinned_40char_git_commit")
    kind = git_output("cat-file", "-t", commit).strip()
    if kind != b"commit":
        raise ValueError("pinned_ref_not_a_commit")
    paths = git_output("ls-tree", "-r", "--name-only", commit, "--",
                       "four_mode_forecasts/").decode().splitlines()
    records = []
    for path in paths:
        m = VALID_FORECAST.fullmatch(path)
        if not m:
            continue
        code = m.group(1)
        date = dt.date.fromisoformat(code[:4]+"-"+code[4:6]+"-"+code[6:8])
        if not start <= date <= end:
            continue
        raw = git_output("show", commit+":"+path)
        try:
            forecast = json.loads(raw)
        except (UnicodeError, json.JSONDecodeError) as exc:
            raise ValueError("malformed_saved_forecast:" + path) from exc
        if not isinstance(forecast, dict):
            raise ValueError("forecast_document_not_object:" + path)
        records.append((path, forecast, hashlib.sha256(raw).hexdigest()))
    return records


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source-commit", required=True)
    ap.add_argument("--start", type=dt.date.fromisoformat, default=dt.date(2026, 11, 6))
    ap.add_argument("--end", type=dt.date.fromisoformat, default=dt.date(2026, 11, 8))
    ap.add_argument("--out", required=True, type=Path)
    args = ap.parse_args()
    report = analyze_records(read_git_snapshot(args.source_commit, args.start, args.end),
                             args.start, args.end)
    report["source_repo_commit_sha"] = args.source_commit
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)+"\n",
                        encoding="utf-8")
    print(json.dumps({
        "source_commit": args.source_commit, "records": report["forecast_records"],
        "title_cards_before_T12": report["title_cards_received_before_T12"],
        "records_with_weather_key": report["weather_field_key_present"],
        "T12_weather_verified": report["official_weather_T12_eligible_races"],
        "research_only": True,
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()

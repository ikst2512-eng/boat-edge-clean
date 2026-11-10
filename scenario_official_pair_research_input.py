"""Research-only: real Nov9/10 official beforeinfo + odds original -> 4-mode input.

This is a *two-source* bridge to #1710's existing #1698 conditional math.
Missing racelist source is NEVER fabricated and official T-12 is NEVER
certified. Wind/wave are observed provenance only (no calibrated effect).
Avoids collecting or modifying any new original, prediction, main, UI, cron.
"""
from datetime import datetime, timedelta
import hashlib
import json
import math
from pathlib import Path
import re
from zipfile import ZipFile

SOURCE = {
    "20261109": {
        "artifact_id": 13652131213, "run": 42567310743,
        "zip_sha": "99f02ff306307dd945f27c225e18ff8341be2832232b7dd0f2751e1d8935f451",
        "size": 28063, "codes": ("202611091110", "202611091710"),
    },
    "20261110": {
        "artifact_id": 13740574410, "run": 42769768447,
        "zip_sha": "cdfdeae53222a5b7852ba5cf5b6b44080247ec074c8d3dbaf53c4a32fe9706dd",
        "size": 32936, "codes": ("202611101202", "202611102211"),
    },
}
PARTIAL_SCHEMA = "SCENARIO_OBSERVED_BEFOREINFO_ODDS_PAIR_RESEARCH_V1"
PRESENT = frozenset({
    "actual_entry_course", "motor_2ren_pct", "wind_speed_mps",
    "wind_from_true_deg", "start_heading_true_deg", "wave_height_cm",
    "tide_station", "tide_height_cm", "tide_phase",
    "two_course_escape_assist_rate", "two_course_wall_rate",
})
RACE_CODE = re.compile(r"20[0-9]{10}\Z")
ST = re.compile(r"\.(\d{2})\Z")
MEASURE = re.compile(r"([0-9]{1,2})R時点\Z")


def sha_bytes(x):
    return hashlib.sha256(x).hexdigest()


def official_partial_from_zip(path: Path, race_code: str):
    """Return a valid study projection and a separate non-scored source witness."""
    if type(race_code) is not str or not RACE_CODE.fullmatch(race_code):
        raise ValueError("invalid_official_race_code")
    day = race_code[:8]
    if day not in SOURCE or race_code not in SOURCE[day]["codes"]:
        raise ValueError("historical_race_not_on_immutable_primary_manifest")
    frozen = SOURCE[day]
    if path.is_symlink() or not path.is_file():
        raise ValueError("source_original_zip_missing_or_symlink")
    raw = path.read_bytes()
    if len(raw) != frozen["size"] or sha_bytes(raw) != frozen["zip_sha"]:
        raise ValueError("primary_source_zip_sha_or_size_changed")
    with ZipFile(path) as z:
        if z.testzip() is not None or len(set(z.namelist())) != len(z.namelist()):
            raise ValueError("primary_source_zip_crc_or_duplicate")
        prefix = "official_joint_evidence/observations/"
        bbase = f"{prefix}before_run{frozen['run']}/{day}/{race_code}"
        obase = f"{prefix}odds_run{frozen['run']}/{day}/{race_code}"
        required = (
            f"{bbase}/beforeinfo.json", f"{bbase}/manifest.json",
            f"{obase}/original.html", f"{obase}/manifest.json",
        )
        if not set(required).issubset(z.namelist()):
            raise ValueError("primary_pair_original_files_missing")
        before, bmeta = z.read(required[0]), json.loads(z.read(required[1]))
        odds, ometa = z.read(required[2]), json.loads(z.read(required[3]))
    for payload, meta in ((before,bmeta),(odds,ometa)):
        if (meta.get("race_code") != race_code
                or meta.get("sha256") != sha_bytes(payload)
                or meta.get("bytes") != len(payload)):
            raise ValueError("primary_pair_manifest_sha_or_race_mismatch")
    # Existing source auditor independently checks 120 unique HTML odds.
    # The separate field below is only the original manifest's own claim.
    if (ometa.get("odds_entries") != 120
            or ometa.get("valid_120_combinations") is not True):
        raise ValueError("odds_source_manifest_not_120")
    record = json.loads(before).get("maindata")
    if (type(record) is not dict or str(record.get("hd")) != day
            or str(record.get("jcd")) != race_code[8:10]
            or int(record.get("rno") or -1) != int(race_code[10:12])):
        raise ValueError("beforeinfo_target_race_key_mismatch")
    deadline = datetime.fromisoformat(
        day[:4] + "-" + day[4:6] + "-" + day[6:8]
        + "T" + record["deadline"] + ":00+09:00")
    cutoff = deadline-timedelta(minutes=12)
    receipt_times = []
    for meta in (bmeta,ometa):
        received=datetime.fromisoformat(meta.get("received_at_jst", ""))
        if (received.utcoffset() != timedelta(hours=9)
                or not received < cutoff):
            raise ValueError("first_party_receipt_claim_not_before_T12")
        receipt_times.append(received.isoformat())
    original_roster = record.get("teiinfolist")
    original_exhibition = record.get("sttenjiinfolist")
    if type(original_roster) is not list or len(original_roster) != 6:
        raise ValueError("six_racer_beforeinfo_missing")
    if (type(original_exhibition) is not list or len(original_exhibition) != 6
            or bmeta.get("start_exhibition_six_valid_rows") is not True):
        raise ValueError("six_exhibition_st_not_yet_available")
    racers = {}
    for item in original_roster:
        boat = int(item["teino"])
        if (boat not in range(1,7) or boat in racers
                or not re.fullmatch(r"[0-9]{4,6}", str(item["racerno"]))
                or int(item.get("absentflag",0)) != 0):
            raise ValueError("official_athlete_or_absence_invalid")
        v = float(item["extime"])
        tilt=float(item["tilt"])
        if not (math.isfinite(v) and 5 <= v <= 10
                and math.isfinite(tilt) and -5 <= tilt <= 5):
            raise ValueError("official_exhibition_time_or_tilt_invalid")
        racers[boat]={
            "boat":boat, "registration_id":str(item["racerno"]),
            "exhibition_time_s":v, "exhibition_tilt":tilt,
        }
    if len(racers)!=6 or len({x["registration_id"] for x in racers.values()})!=6:
        raise ValueError("incomplete_distinct_official_roster")
    by_course=set()
    for item in original_exhibition:
        course=int(item["cs"])
        boat=int(item["teino"])
        m=ST.fullmatch(str(item.get("st","")))
        if (course not in range(1,7) or course in by_course
                or boat not in racers or "exhibition_st_s" in racers[boat]
                or m is None):
            raise ValueError("official_exhibition_course_or_ST_invalid")
        racers[boat]["exhibition_course_only"]=course
        racers[boat]["exhibition_st_s"]=int(m.group(1))/100
        by_course.add(course)
    if (len(by_course)!=6 or
            any("exhibition_course_only" not in x for x in racers.values())):
        raise ValueError("exhibition_entry_permutation_incomplete")
    boats=[racers[i] for i in range(1,7)]
    source_sha={"beforeinfo":sha_bytes(before),"odds120":sha_bytes(odds)}
    normalized={"race_code":race_code, "source_sha256":source_sha, "exhibition_features_by_boat":boats}
    encoded=lambda x:json.dumps(x,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()
    weather=record.get("weatherinfo",{})
    label=weather.get("measuretime")
    match=MEASURE.fullmatch(str(label))
    number=int(match.group(1)) if match else None
    if number is None or not 1 <= number < int(race_code[-2:]):
        raise ValueError("source_weather_measurement_label_missing_or_not_earlier")
    def quantity(field,unit):
        m=re.fullmatch(r"([0-9]+)" + re.escape(unit),str(weather.get(field)))
        return int(m.group(1)) if m else None
    source_witness={
        "race_code":race_code, "source_archive_sha256":frozen["zip_sha"],
        "original_artifact_id":frozen["artifact_id"],
        "beforeinfo_sha256":source_sha["beforeinfo"],
        "odds_original_html_sha256":source_sha["odds120"],
        "original_receipt_jst_self_reported":receipt_times,
        "same_race_racelist_original":False,
        "odds120_original_html_manifest_claim_not_independent_reparse":True,
        "weather_mps_observed_prior_race_label_only":quantity("wind","m"),
        "wave_cm_observed_prior_race_label_only":quantity("wave","cm"),
        "weather_source_race_label":label,
        "weather_source_race_gap":int(race_code[-2:])-number,
        "weather_measurement_clock_verified":False,
        "wind_direction_FROM_TO_verified":False,
        "actual_final_entry_observed":False,
        "source_to_new_forecast_first_git_receipt_verified":False,
        "usable_for_T12_formal_prediction":False,
    }
    projection={
        "schema":PARTIAL_SCHEMA,
        "race_code":race_code,
        "source_sha256":source_sha,
        "normalized_source_sha256":sha_bytes(encoded(normalized)),
        "exhibition_features_by_boat":boats,
        "exhibition_features_sha256":sha_bytes(encoded(boats)),
        "structural_source_to_candidate_order":False,
        "structural_raw_semantic_replay_reported":False,
        "missing_research_features":sorted(PRESENT),
        "feature_values_imputed":False,
        "exhibition_is_actual_final_entry":False,
        "raw_http_origin_independently_attested":False,
        "replay_callback_authenticity_independently_proven":False,
        "candidate_first_remote_receipt_verified":False,
        "model_consumed_these_features_verified":False,
        "all_scenario_effect_coefficients_calibrated":False,
        "formal":False,
        "accuracy_effect_proven":False,
        "promotion_allowed":False,
        "production_changed":False,
        "source_original_zip_sha256":frozen["zip_sha"],
        "racelist_original_missing":True,
        "source_pair_only_no_new_forecast_receipt":True,
        "weather_observation_clock_unverified":True,
    }
    return projection, source_witness

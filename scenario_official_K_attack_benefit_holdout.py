"""Retrospective official-K association study: attacking winner and other boats.

This reads FINISHED historical races only. It does NOT observe an unsuccessful
3C/4C attack, wall defense, 4/5's causal beneficiary role, or predicted odds.
Outputs must NEVER be passed to pre-deadline forecast generation.
The source replay requires the EXACT frozen #1692 parsers and 92-day source ZIP,
verified separately by SHA-256 on both ZIP and each day's raw/decoded bytes.
"""
from collections import Counter, defaultdict
from datetime import date, timedelta
from hashlib import sha256
import json
from pathlib import Path
from zipfile import ZipFile
import math

STUDY_ID = "RETROSPECTIVE_ONLY_K92_ATTACK_WINNER_COMPANIONS_V1"
METHODS = ("逃げ", "差し", "まくり", "まくり差し", "抜き", "恵まれ")
GROUPS = (
    "one_escape", "three_makuri", "three_makuri_sashi", "three_other_win",
    "four_makuri", "four_makuri_sashi", "four_other_win",
    "five_makuri_sashi", "five_other_win", "all_other",
)
STAT_KEYS = tuple(
    f"course{course}_{position}"
    for course in (2, 3, 4, 5, 6)
    for position in ("second", "third", "top3")
) + ("four_and_five_both_top3",)
DAY_COUNT = 92
EXPECTED_RAW = 14249
EXPECTED_BASIC_ELIGIBLE = 13815


def _group(first_course, method):
    if first_course == 1 and method == "逃げ":
        return "one_escape"
    if first_course == 3:
        return {"まくり": "three_makuri",
                "まくり差し": "three_makuri_sashi"}.get(method, "three_other_win")
    if first_course == 4:
        return {"まくり": "four_makuri",
                "まくり差し": "four_makuri_sashi"}.get(method, "four_other_win")
    if first_course == 5:
        return "five_makuri_sashi" if method == "まくり差し" else "five_other_win"
    return "all_other"


def _record(r):
    """Convert a single settled FULL six-finisher result by actual course.

    No finish-index course inferred from boat number. Return None for races
    with any non-finisher, F, disqualification or incomplete actual entry.
    """
    if type(r) is not dict or r.get("unsettled") is not False:
        return None
    method = r.get("method")
    if method not in METHODS:
        return None
    entries = r.get("entries")
    if type(entries) is not list or len(entries) != 6:
        return None
    if ({e.get("boat") for e in entries if type(e) is dict} != set(range(1, 7))
            or {e.get("course") for e in entries if type(e) is dict} != set(range(1, 7))
            or {e.get("status") for e in entries if type(e) is dict}
            != {f"{i:02d}" for i in range(1, 7)}):
        return None
    finish = sorted(entries, key=lambda e: int(e["status"]))
    courses = tuple(e["course"] for e in finish)
    first = courses[0]
    if (first == 1 and method not in ("逃げ", "抜き", "恵まれ")
            or first == 2 and method == "逃げ"
            or first in (3, 4, 5, 6) and method == "逃げ"):
        return None
    return {
        "group": _group(first, method),
        "actual_course_finish": courses,
        "first_course": first,
        "method": method,
        "no_causal_attack_observed": True,
    }


def _wilson(count, n):
    if n == 0:
        return {"count": count, "denominator": 0, "percent": None, "wilson_95_pct": None}
    z = 1.959963984540054
    p = count / n
    d = 1 + z * z / n
    mid = (p + z * z / (2 * n)) / d
    rad = z * math.sqrt(p * (1-p) / n + z*z/(4*n*n)) / d
    return {"count": count, "denominator": n, "percent": round(100*p, 3),
            "wilson_95_pct": [round(100*(mid-rad), 3), round(100*(mid+rad), 3)]}


def summarize(records):
    """Descriptive group fractions. No trained coefficient or causal uplift."""
    accum = {name: Counter() for name in GROUPS}
    for record in records:
        if type(record) is not dict or record.get("no_causal_attack_observed") is not True:
            raise ValueError("retrospective_course_record_required")
        key = record["group"]
        if key not in accum:
            raise ValueError("unregistered_winning_group")
        courses = record["actual_course_finish"]
        if type(courses) is not tuple or len(courses) != 6 or set(courses) != set(range(1, 7)):
            raise ValueError("invalid_actual_course_finish")
        a = accum[key]
        a["n"] += 1
        for c in (2, 3, 4, 5, 6):
            a[f"course{c}_second"] += int(courses[1] == c)
            a[f"course{c}_third"] += int(courses[2] == c)
            a[f"course{c}_top3"] += int(c in courses[:3])
        a["four_and_five_both_top3"] += int(4 in courses[:3] and 5 in courses[:3])
    out = {}
    for group in GROUPS:
        n = accum[group]["n"]
        out[group] = {"races": n, "rates": {
            key: _wilson(accum[group][key], n) for key in STAT_KEYS
        }}
    return out


def analyze_official_K_92day(path):
    """Inspect pinned historical postrace results, NEVER a prospective predictor.

    The exact frozen #1692 module paths are made available by existing PR CI;
    import is deferred to avoid modifying their preregistered code.
    """
    from research_official_k_c2_escape_conditional_92day import (
        verify_original_zip, race_outcome,
    )
    from research_official_k_one_day_compare import RACE, parse_k, unpack_lha
    path = Path(path)
    original_zip = verify_original_zip(path)
    total_raw = basic_eligible = clean = 0
    daily_sha = []
    kept = {"train_aug_sep": [], "historical_holdout_oct": []}
    excluded = Counter()
    dates = [(date(2026, 8, 1) + timedelta(days=i)).strftime("%Y%m%d")
             for i in range(DAY_COUNT)]
    with ZipFile(path) as archive:
        if archive.testzip() is not None:
            raise ValueError("K_archive_bad_crc")
        members = archive.namelist()
        if len(members) != len(set(members)):
            raise ValueError("K_archive_duplicate_member")
        manifest = json.loads(archive.read("official_k_full_92day_reconciliation.json"))
        if manifest.get("study_period") != "2026-08-01/2026-10-31":
            raise ValueError("K_archive_wrong_period")
        entries = manifest.get("results")
        if type(entries) is not list or len(entries) != DAY_COUNT:
            raise ValueError("K_archive_incomplete_day_manifest")
        by_date = {row.get("day"): row for row in entries}
        if len(by_date) != DAY_COUNT or set(by_date) != set(dates):
            raise ValueError("K_archive_day_universe_changed")
        for day in dates:
            entry = by_date[day]
            source = archive.read("official_k_full_92_raw/k" + day[2:] + ".lzh")
            original_sha = sha256(source).hexdigest()
            if original_sha != entry.get("official_K_sha256"):
                raise ValueError("K_day_original_SHA_mismatch")
            decoded = unpack_lha(source, day=day)
            decoded_sha = sha256(decoded).hexdigest()
            if decoded_sha != entry.get("decoded_sha256"):
                raise ValueError("K_day_decoded_SHA_mismatch")
            raw_text = decoded.decode("cp932")
            race_count = sum(bool(RACE.match(line)) for line in raw_text.splitlines())
            races = parse_k(raw_text, day=day, expected_races=race_count,
                            allow_unsettled=True)
            if len(races) != entry.get("official_K_races"):
                raise ValueError("K_day_race_count_mismatch")
            daily_sha.append((day, original_sha, decoded_sha))
            cohort = "train_aug_sep" if day[4:6] in ("08", "09") else "historical_holdout_oct"
            total_raw += len(races)
            for race in races.values():
                if race_outcome(race) is None:
                    excluded["basic_course_or_result_eligibility"] += 1
                    continue
                basic_eligible += 1
                record = _record(race)
                if record is None:
                    excluded["not_all_six_finishers_or_unknown_method"] += 1
                    continue
                clean += 1
                kept[cohort].append(record)
    if (total_raw, basic_eligible) != (EXPECTED_RAW, EXPECTED_BASIC_ELIGIBLE):
        raise ValueError("K_frozen_92day_cohort_changed")
    if sum(len(v) for v in kept.values()) != clean or clean <= 0:
        raise ValueError("K_clean_cohort_empty_or_mismatch")
    groups = {key: summarize(val) for key, val in kept.items()}
    contrast = {}
    for group in ("three_makuri", "three_makuri_sashi", "four_makuri"):
        rows = groups["historical_holdout_oct"][group]
        contrast[group] = {
            "october_n": rows["races"],
            "four_course_second": rows["rates"]["course4_second"],
            "five_course_second": rows["rates"]["course5_second"],
            "five_course_third": rows["rates"]["course5_third"],
            "six_course_top3": rows["rates"]["course6_top3"],
            "insufficient_for_stable_point_estimate": rows["races"] < 30,
        }
    return {
        "study_id": STUDY_ID,
        "source_zip_sha256": original_zip,
        "official_K_days_verified": len(daily_sha),
        "official_K_day_fingerprint_sha256": sha256(
            json.dumps(daily_sha, separators=(",", ":")).encode()).hexdigest(),
        "source_kind": "official_K_postrace_historical_only",
        "original_raw_races": total_raw,
        "basic_eligible_races": basic_eligible,
        "clean_six_finishers": clean,
        "exclusions": dict(excluded),
        "train_n": len(kept["train_aug_sep"]),
        "historical_october_n": len(kept["historical_holdout_oct"]),
        "october_focus": contrast,
        "by_period": groups,
        "limitations": {
            "only_winning_decisive_method_observed": True,
            "failed_attack_attempt_not_observed": True,
            "beneficiary_causality_not_observed": True,
            "all_entry_courses_are_historical_postrace": True,
            "historical_october_is_not_prospective_validation": True,
            "motor_meeting_form_and_comments_not_in_source": True,
            "not_predeadline_model_input": True,
            "forecast_probabilities_generated": False,
            "model_coefficients_modified": False,
            "source_licenses_or_secondary_crawl_changed": False,
            "production_changed": False,
            "promotion_allowed": False,
        },
    }

"""Independently reparse caller-supplied official raw bytes before candidate lineage.

Unlike the structural-only preflight, compare each normalized source feature
against the repository's already-tested original-source parsers. This
confirms that the claimed features are actually present in the supplied bytes,
NOT that the bytes originated from authenticated HTTP or were first remotely
received before T-12. Do not use to authorize production, scoring or merge.

No external fetch, result lookup, candidate generation, selector or file write.
"""
import argparse
import base64
import json
import re
from pathlib import Path
from urllib.parse import urlencode

from four_mode_official_future_lineage_preflight import (
    BLOCKED, KINDS, _load_local_json, preflight,
)
from scripts.inspect_official_beforeinfo_json import inspect
from scripts.inspect_official_racelist_registrations import inspect_six_registrations
from server import parse_official_odds_table


def _beforeinfo_features(raw, race_code):
    try:
        main = json.loads(raw)["maindata"]
    except (ValueError, UnicodeError, KeyError, TypeError) as exc:
        raise ValueError("official_beforeinfo_raw_invalid") from exc
    if not isinstance(main, dict):
        raise ValueError("official_beforeinfo_raw_invalid")
    day, venue, rno = race_code[:8], race_code[8:10], int(race_code[10:])
    if (str(main.get("hd")) != day
            or str(main.get("jcd")).zfill(2) != venue
            or str(main.get("rno")) != str(rno)):
        raise ValueError("official_beforeinfo_raw_race_mismatch")
    check = inspect({"maindata":main})
    if (check.get("six_unique_boats") is not True
            or check.get("exhibition_time_nonempty_six") is not True
            or check.get("tilt_observed_boats") != 6
            or check.get("start_exhibition_six_valid_rows") is not True):
        raise ValueError("official_beforeinfo_raw_exhibition_incomplete")
    racers = main["teiinfolist"]
    by_boat = {}
    for item in racers:
        if type(item) is not dict:
            raise ValueError("official_beforeinfo_raw_racer_invalid")
        boat = str(item.get("teino"))
        registration = str(item.get("racerno"))
        if (boat not in "123456" or len(boat) != 1
                or registration is None
                or re.fullmatch(r"[0-9]{4}", registration) is None
                or boat in by_boat):
            raise ValueError("official_beforeinfo_raw_registration_invalid")
        try:
            extime = float(item["extime"])
            tilt = float(item["tilt"])
        except (TypeError, ValueError, KeyError, OverflowError) as exc:
            raise ValueError("official_beforeinfo_raw_numeric_invalid") from exc
        by_boat[boat] = {"registration":registration,
                         "extime":extime, "tilt":tilt}
    if set(by_boat) != set("123456"):
        raise ValueError("official_beforeinfo_raw_six_missing")
    starts = {}
    for item in main["sttenjiinfolist"]:
        if type(item) is not dict:
            raise ValueError("official_start_raw_row_invalid")
        boat = str(item.get("teino"))
        course = str(item.get("cs"))
        raw_st = item.get("st")
        if (boat not in "123456" or len(boat) != 1 or boat in starts
                or course not in "123456" or len(course) != 1
                or type(raw_st) is not str):
            raise ValueError("official_start_raw_identity_invalid")
        # Fail closed rather than silently reclassifying F/L start flags
        # as positive ST. A future flagged-ST policy needs separate review.
        if not re.fullmatch(r"(?:\.\d{1,2}|\d?\.\d{1,2})", raw_st.strip()):
            raise ValueError("official_start_flagged_or_ambiguous_st")
        starts[boat] = {"course":int(course), "st":float(raw_st)}
    if set(starts) != set("123456") or set(x["course"] for x in starts.values()) != set(range(1,7)):
        raise ValueError("official_start_raw_six_missing_or_duplicate")
    if type(main.get("deadline")) is not str:
        raise ValueError("official_beforeinfo_raw_deadline_missing")
    return {
        "beforeinfo_registration_ids":[by_boat[str(i)]["registration"] for i in range(1,7)],
        "exhibition_courses":[starts[str(i)]["course"] for i in range(1,7)],
        "exhibition_times":[by_boat[str(i)]["extime"] for i in range(1,7)],
        "exhibition_st":[starts[str(i)]["st"] for i in range(1,7)],
        "exhibition_tilts":[by_boat[str(i)]["tilt"] for i in range(1,7)],
        "deadline_display": main["deadline"],
    }


def replay(source_bundle, candidate, *, odds_parser=parse_official_odds_table):
    """Perform structural preflight first, then real source BYTE reparsing."""
    check = preflight(source_bundle, candidate)
    code = source_bundle["race_code"]
    normalized = source_bundle["normalized_source_claim"]
    if (type(normalized) is not dict or BLOCKED.intersection(normalized)
            or set(normalized) != {
                "race_code", "source_sha256", "racelist_registration_ids",
                "beforeinfo_registration_ids", "exhibition_courses",
                "exhibition_times", "exhibition_st", "exhibition_tilts", "odds_3t"
            }):
        raise ValueError("unrecognized_normalized_source_claim_field")
    day, venue, number = code[:8], code[8:10], str(int(code[10:]))
    if not (1 <= int(venue) <= 24 and 1 <= int(number) <= 12):
        raise ValueError("invalid_official_race_id")
    expected_urls = {
        "racelist": "https://www.boatrace.jp/owpc/pc/race/racelist?" +
                    urlencode({"hd": day, "jcd": venue, "rno": number}),
        "beforeinfo": "https://www.boatrace.jp/owsp/sp/spdata?" +
                      urlencode({"type": "beforeinfo", "hd": day,
                                 "jcd": venue, "rno": number}),
        "odds120": "https://www.boatrace.jp/owpc/pc/race/odds3t?" +
                   urlencode({"hd": day, "jcd": venue, "rno": number}),
    }
    originals = source_bundle["originals"]
    for kind in KINDS:
        if originals[kind]["source_url"] != expected_urls[kind]:
            raise ValueError("not_the_exact_official_race_source_url")
    card_bytes = base64.b64decode(originals["racelist"]["raw_base64"], validate=True)
    before_bytes = base64.b64decode(originals["beforeinfo"]["raw_base64"], validate=True)
    odds_bytes = base64.b64decode(originals["odds120"]["raw_base64"], validate=True)
    card = inspect_six_registrations(card_bytes)
    if card.get("six_racers_verified") is not True:
        raise ValueError("original_racelist_six_racers_missing")
    derived = _beforeinfo_features(before_bytes, code)
    declared_deadline = source_bundle["deadline_jst"][11:16]
    if derived.pop("deadline_display") != declared_deadline:
        raise ValueError("original_official_deadline_mismatch")
    derived["racelist_registration_ids"] = [
        card["registrations_by_lane"][str(i)] for i in range(1,7)
    ]
    actual_odds = odds_parser(odds_bytes.decode("utf-8", errors="replace"))
    if not isinstance(actual_odds, dict):
        raise ValueError("invalid_reparsed_odds")
    derived["odds_3t"] = {combo:float(value) for combo,value in actual_odds.items()}
    if (set(derived["odds_3t"]) != set(normalized["odds_3t"])
            or any(derived["odds_3t"][k] != normalized["odds_3t"][k]
                   for k in derived["odds_3t"])):
        raise ValueError("odds_claim_does_not_match_raw_official_table")
    for field, actual in derived.items():
        if field == "odds_3t":
            continue
        if actual != normalized[field]:
            raise ValueError("normalized_" + field + "_does_not_match_official_raw")
    return {
        "schema":"FOUR_MODE_OFFICIAL_RAW_SEMANTIC_REPLAY_V1",
        "race_code":code,
        "status":"raw_bytes_semantically_reparsed_and_declared_features_match_RESEARCH_ONLY",
        "verified_stages":[
            "preflight_raw_byte_sha_and_clock_structure",
            "official_racelist_six_registration_parser",
            "official_beforeinfo_six_exhibition_start_parser",
            "official_120_odds_html_parser",
            "declared_normalized_features_match_raw_reparse"
        ],
        "preflight_still_nonformal": check["formal"] is False,
        "raw_official_provenance_independently_attested":False,
        "actual_model_output_independently_replayed":False,
        "first_remote_candidate_acceptance_independently_verified":False,
        "final_entry_verified":False,
        "formal":False, "prospective_candidate_admitted":False,
        "model_improvement_proven":False, "model_promotion_allowed":False,
        "warning":"Replaying supplied bytes is not independently attested HTTP origin,"
                  " official source publication time, candidate method execution,"
                  " first remote acceptance, or final six-boat entry.",
    }


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source-bundle", required=True)
    ap.add_argument("--candidate", required=True)
    ap.add_argument("--output", type=Path)
    args=ap.parse_args()
    result=replay(_load_local_json(args.source_bundle),
                  _load_local_json(args.candidate))
    data=json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2)+"\n"
    if args.output:
        if args.output.is_symlink():
            raise ValueError("report_output_symlink")
        args.output.write_text(data, encoding="utf-8")
    print("OFFICIAL_RAW_SEMANTIC_REPLAY_RESEARCH_ONLY="+json.dumps(result, sort_keys=True))


if __name__=="__main__":
    main()

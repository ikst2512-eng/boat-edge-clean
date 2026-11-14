"""Read-only, outcome-blind (for target) prior-day meeting form from original racelist.

The official racelist contains earlier, already-settled meeting races in FOUR
rows per racer: race number (color is the boat drawn), actual course, ST,
and placing with an official result link. This module only uses PRIOR DAYS,
not same-day or target race results. It is not an official HTTP receiver,
a T-12 certification, a decider-method classifier or a fitted model.

Source replay must be paired with the existing #1746 three-original verifier
before interpreting its six-racer output as source-backed research.
"""
from collections import Counter
from datetime import date
from hashlib import sha256
from html import unescape
from html.parser import HTMLParser
import json
import math
import re
from urllib.parse import parse_qs, urlsplit

from scripts.inspect_official_racelist_registrations import ROW
from scenario_official_racelist_rates import extract_six_official_racelist_rates

_HISTORY_COLUMNS = 14
_CELL_COUNT = 9 + _HISTORY_COLUMNS + 1
_TRAILING = re.compile(r"\s*<tr\b[^>]*>.*?</tr>", re.S)
_CODE = re.compile(r"20\d{10}\Z")
_REG = re.compile(r"\d{4}\Z")
_ST = re.compile(r"(?:0?\.\d{1,2})\Z")
_FINISH = re.compile(r"[1-6]\Z")
_RNO = re.compile(r"(?:[1-9]|1[0-2])\Z")
_HREF = "/owpc/pc/race/raceresult"


class _TD(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.cells = []
        self.active = None

    def handle_starttag(self, tag, attrs):
        if tag == "td":
            if self.active is not None:
                raise ValueError("nested_meeting_td")
            self.active = {"attrs": dict(attrs), "text": [], "hrefs": []}
        elif tag == "a" and self.active is not None:
            self.active["hrefs"].append(dict(attrs).get("href", ""))
        elif tag == "br" and self.active is not None:
            self.active["text"].append(" ")

    def handle_data(self, data):
        if self.active is not None:
            self.active["text"].append(data)

    def handle_endtag(self, tag):
        if tag == "td":
            if self.active is None:
                raise ValueError("meeting_td_unmatched")
            self.active["text"] = " ".join("".join(self.active["text"]).split())
            self.cells.append(self.active)
            self.active = None


def _parse_cells(fragment):
    parser = _TD()
    parser.feed(fragment)
    parser.close()
    if parser.active is not None:
        raise ValueError("incomplete_meeting_td")
    return parser.cells


def _history_from_raw(raw, expected_registrations):
    frozen = extract_six_official_racelist_rates(raw)
    ids = [row["registration_id"] for row in frozen["boats"]]
    if ids != expected_registrations:
        raise ValueError("six_registration_identity_mismatch")
    html = unescape(raw.decode("utf-8", "replace"))
    found = list(ROW.finditer(html))
    if len(found) != 6 or [int(match.group(1)) for match in found] != list(range(1, 7)):
        raise ValueError("six_main_racer_rows_not_unique")
    bundles = []
    for match in found:
        boat = int(match.group(1))
        main = _parse_cells(match.group(0))
        if len(main) != _CELL_COUNT:
            raise ValueError("official_meeting_first_row_shape_drift")
        suffix = html[match.end():]
        rows = []
        offset = 0
        for _ in range(3):
            tail = _TRAILING.match(suffix, offset)
            if tail is None:
                raise ValueError("official_meeting_four_row_shape_drift")
            row = _parse_cells(tail.group(0))
            if len(row) != _HISTORY_COLUMNS:
                raise ValueError("official_meeting_subrow_shape_drift")
            rows.append(row)
            offset = tail.end()
        bundles.append((boat, main[9:9 + _HISTORY_COLUMNS], *rows))
    return bundles


def extract_prior_day_meeting_form(raw, race_code, expected_registrations):
    """Evidence-constrained sample count from pre-race original HTML.

    Does not use final course for target race. Missing/invalid history remains
    unobserved; percentages are supported only by parsed settled prior-day
    start/finish pairs. No winning-method or motor attribution is fabricated.
    """
    if (type(raw) is not bytes or type(race_code) is not str
            or not _CODE.fullmatch(race_code)
            or type(expected_registrations) is not list
            or len(expected_registrations) != 6
            or any(type(reg) is not str or not _REG.fullmatch(reg)
                   for reg in expected_registrations)
            or len(set(expected_registrations)) != 6):
        raise ValueError("meeting_original_race_and_roster_required")
    try:
        target_day = date.fromisoformat(
            race_code[:4] + "-" + race_code[4:6] + "-" + race_code[6:8])
    except ValueError as exc:
        raise ValueError("meeting_target_day_invalid") from exc
    target_venue = race_code[8:10]
    target_rno = int(race_code[10:])
    entries = []
    for boat, race_cells, course_cells, st_cells, finish_cells in _history_from_raw(
            raw, expected_registrations):
        history = []
        excluded = Counter()
        seen = set()
        for idx, (ncell, coursecell, stcell, fcell) in enumerate(zip(
                race_cells, course_cells, st_cells, finish_cells)):
            if not any(cell["text"] for cell in (ncell, coursecell, stcell, fcell)):
                continue
            links = fcell["hrefs"]
            if len(links) != 1:
                excluded["no_unique_result_link"] += 1
                continue
            uri = urlsplit(links[0])
            qs = parse_qs(uri.query)
            if (uri.path != _HREF or uri.netloc or uri.scheme
                    or set(qs) != {"hd", "jcd", "rno"}
                    or any(len(value) != 1 for value in qs.values())
                    or not re.fullmatch(r"20\d{6}", qs["hd"][0])
                    or not _RNO.fullmatch(qs["rno"][0])):
                raise ValueError("untrusted_meeting_result_link")
            if qs["jcd"][0] != target_venue:
                raise ValueError("cross_venue_meeting_history")
            day = qs["hd"][0]
            try:
                race_day = date.fromisoformat(day[:4] + "-" + day[4:6] + "-" + day[6:8])
            except ValueError as exc:
                raise ValueError("meeting_result_date_invalid") from exc
            rno = int(qs["rno"][0])
            key = (day, rno)
            if key in seen:
                raise ValueError("duplicate_meeting_result")
            seen.add(key)
            if race_day > target_day or (race_day == target_day and rno >= target_rno):
                raise ValueError("target_or_future_meeting_result_leak")
            if race_day == target_day:
                excluded["same_day_not_independently_time_verified"] += 1
                continue
            if ncell["text"] != str(rno):
                raise ValueError("meeting_race_number_column_mismatch")
            color = re.search(r"\bis-boatColor([1-6])\b",
                              ncell["attrs"].get("class", ""))
            if color is None:
                raise ValueError("meeting_drawn_boat_color_missing")
            course = coursecell["text"]
            st = stcell["text"]
            finish = fcell["text"].translate(str.maketrans("１２３４５６", "123456"))
            if not (re.fullmatch("[1-6]", course) and _ST.fullmatch(st)
                    and _FINISH.fullmatch(finish)):
                excluded["non_numeric_finish_or_start"] += 1
                continue
            st_value = float(st)
            if not 0 <= st_value < 0.5 or not math.isfinite(st_value):
                excluded["out_of_bounds_meeting_st"] += 1
                continue
            history.append({
                "race_code": day + target_venue + f"{rno:02d}",
                "drawn_boat": int(color.group(1)),
                "actual_course_historical_only": int(course),
                "start_st_s": st_value,
                "finish_position": int(finish),
                "history_slot": idx,
            })
        if len(set(row["race_code"] for row in history)) != len(history):
            raise ValueError("duplicate_counted_meeting_start")
        n = len(history)
        top2 = sum(row["finish_position"] <= 2 for row in history)
        top3 = sum(row["finish_position"] <= 3 for row in history)
        st_mean = sum(row["start_st_s"] for row in history) / n if n else None
        entries.append({
            "boat": boat,
            "registration_id": expected_registrations[boat - 1],
            "prior_day_completed_starts": n,
            "prior_day_top2_count": top2,
            "prior_day_top3_count": top3,
            "prior_day_2ren_pct": round(100 * top2 / n, 6) if n else None,
            "prior_day_3ren_pct": round(100 * top3 / n, 6) if n else None,
            "prior_day_average_st_s": round(st_mean, 6) if n else None,
            "prior_day_results": history,
            "excluded_slots": dict(excluded),
        })
    if [row["boat"] for row in entries] != list(range(1, 7)):
        raise ValueError("meeting_six_rows_incomplete")
    return {
        "schema": "OFFICIAL_RACELIST_PRIOR_DAY_MEETING_FORM_RESEARCH_V1",
        "race_code": race_code,
        "racelist_original_sha256": sha256(raw).hexdigest(),
        "rows": entries,
        "historical_actual_course_not_future_entry": True,
        "only_prior_day_settled_results": True,
        "winning_method_from_result_not_inferred": True,
        "motor_starts_or_successes_verified": False,
        "comments_source_verified": False,
        "source_receipt_independently_attested": False,
        "same_race_T12_model_consumption_verified": False,
        "formal": False,
        "production_changed": False,
        "model_coefficients_changed": False,
    }

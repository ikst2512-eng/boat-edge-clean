"""Read-only as-of course history from documented BoatraceCSV card/result rows.

This is exploratory feature extraction. Third-party historical results and local
receipts are not an official BOAT RACE verification of any live entry.
Never use target/future results, national win rates, or later downloads as
surrogates for as-of course statistics.
"""
from collections import defaultdict, Counter
from datetime import datetime
import math
import re

CODE = re.compile(r"^20\d{10}$")
SHA = re.compile(r"^[0-9a-f]{64}$")
FINAL = set("123456")
DECISIONS = {"逃げ", "差し", "まくり", "まくり差し", "抜き", "恵まれ"}


def _parse_time(value):
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value)
        return parsed if parsed.utcoffset() is not None else None
    except ValueError:
        return None


def _six(seq):
    return (isinstance(seq, (list, tuple)) and len(seq) == 6
            and set(seq) == {1, 2, 3, 4, 5, 6})


def _registration(value):
    value = str(value or "").strip()
    return value if re.fullmatch(r"\d{4}", value) else None


def _rate(n, d):
    return round(n / d, 8) if d else None


def compile_asof_course_history(target, history, *, cutoff_at, entry=None, min_starts=10):
    """Return selected-course stats and provenance, never a formal forecast.

    target: CLEAN racecard-v5 object (target registrations and race key).
    history: iterable of {race_card: source CSV row, result: result CSV row,
      card_receipt_at: ISO timestamp, result_receipt_at: ISO timestamp,
      card_sha256: SHA256, result_sha256: SHA256}.
    Per-source receipt timestamps must be BEFORE the target's research cutoff.
    Historical race day must be strictly older than target race day.
    """
    cutoff = _parse_time(cutoff_at)
    race_key = target.get("race_key") if isinstance(target, dict) else None
    code = race_key.replace("-", "") if isinstance(race_key, str) else ""
    if not CODE.fullmatch(code) or not cutoff:
        raise ValueError("invalid_target_or_cutoff")
    if not _six(entry if entry is not None else list(range(1, 7))):
        raise ValueError("invalid_selected_entry")
    entry = list(entry if entry is not None else range(1, 7))
    racers = target.get("racers")
    if not isinstance(racers, list) or len(racers) != 6:
        raise ValueError("invalid_target_racers")
    by_lane = {}
    for racer in racers:
        if not isinstance(racer, dict) or type(racer.get("lane")) is not int:
            raise ValueError("invalid_target_racers")
        lane = racer["lane"]
        if lane in by_lane:
            raise ValueError("duplicate_target_lane")
        by_lane[lane] = _registration(racer.get("registration_no"))
    if set(by_lane) != set(range(1, 7)) or None in by_lane.values() or len(set(by_lane.values())) != 6:
        raise ValueError("invalid_target_registration")

    counters = defaultdict(lambda: dict(starts=0, win=0, top2=0, top3=0,
                                        st_sum=0.0, st_n=0, decisions=Counter()))
    excluded = Counter()
    used = set()
    provenance = []
    for item in history:
        if not isinstance(item, dict):
            excluded["bad_input"] += 1
            continue
        card, result = item.get("race_card"), item.get("result")
        if not isinstance(card, dict) or not isinstance(result, dict):
            excluded["missing_rows"] += 1
            continue
        hcode = result.get("レースコード")
        if (not isinstance(hcode, str) or not CODE.fullmatch(hcode)
                or card.get("レースコード") != hcode or hcode[:8] >= code[:8]):
            excluded["wrong_race_or_future_day"] += 1
            continue
        if hcode in used:
            excluded["duplicate_race"] += 1
            continue
        card_time = _parse_time(item.get("card_receipt_at"))
        result_time = _parse_time(item.get("result_receipt_at"))
        # A result row's own publication-time stamp is another independent gate.
        published = _parse_time(result.get("取得日時"))
        if (not card_time or not result_time or not published or
                max(card_time, result_time, published) >= cutoff):
            excluded["receipt_not_asof"] += 1
            continue
        if (not SHA.fullmatch(str(item.get("card_sha256") or ""))
                or not SHA.fullmatch(str(item.get("result_sha256") or ""))):
            excluded["missing_source_digest"] += 1
            continue
        regs = [_registration(card.get(f"艇{i}_登録番号")) for i in range(1, 7)]
        if None in regs or len(set(regs)) != 6:
            excluded["invalid_registration"] += 1
            continue
        try:
            finish = [int(result[f"{i}着_艇番"]) for i in range(1, 7)]
            courses = [int(result[f"{i}コース_艇番"]) for i in range(1, 7)]
        except (ValueError, TypeError, KeyError):
            excluded["incomplete_result"] += 1
            continue
        if not _six(finish) or not _six(courses):
            excluded["incomplete_result"] += 1
            continue
        st_values = []
        for course in range(1, 7):
            value = result.get(f"{course}コース_スタートタイミング")
            try:
                st = float(value)
                if not math.isfinite(st) or st < -0.2 or st > 0.99:
                    st = None
            except (ValueError, TypeError):
                st = None
            st_values.append(st)
        decision = result.get("決まり手")
        # Published realtime CSVs include Japanese full-width spacing,
        # e.g. 2026-11-02: 「逃　げ」, which must normalize to 「逃げ」.
        # Never infer an unknown decision from the winning course.
        decision = re.sub(r"\s+", "", decision) if isinstance(decision, str) else None
        if decision not in DECISIONS:
            decision = None
        # All validation above is race-atomic. Only now can we mark it used.
        used.add(hcode)
        provenance.append(dict(race_code=hcode, card_sha256=item["card_sha256"],
            result_sha256=item["result_sha256"], card_receipt_at=card_time.isoformat(),
            result_receipt_at=result_time.isoformat()))
        for course, boat in enumerate(courses, start=1):
            registration = regs[boat - 1]
            row = counters[(registration, course)]
            position = finish.index(boat) + 1
            row["starts"] += 1
            row["win"] += position == 1
            row["top2"] += position <= 2
            row["top3"] += position <= 3
            st = st_values[course - 1]
            if st is not None and st >= 0:  # F contributes to starts, not mean normal ST.
                row["st_sum"] += st
                row["st_n"] += 1
            if position == 1 and decision:
                row["decisions"][decision] += 1
    boats = []
    for course, boat in enumerate(entry, start=1):
        registration = by_lane[boat]
        row = counters[(registration, course)]
        n = row["starts"]
        boats.append(dict(boat=boat, registration_no=registration, course=course,
                          courseStarts=n, courseWinRate=_rate(row["win"], n),
                          courseTop2Rate=_rate(row["top2"], n),
                          courseTop3Rate=_rate(row["top3"], n),
                          courseAverageST=round(row["st_sum"] / row["st_n"], 5) if row["st_n"] else None,
                          valid_st_starts=row["st_n"], first_place_decisions=dict(row["decisions"]),
                          sufficient_sample=n >= min_starts and row["st_n"] >= min_starts,
                          courseDataSource="third_party_historical_asof",
                          observedAt=max((p["result_receipt_at"] for p in provenance), default=None)))
    return dict(schema="entry-course-history-asof-v1", race_key=race_key,
                selected_entry=entry, cutoff_at=cutoff.isoformat(), boats=boats,
                eligible_races=len(used), excluded=dict(excluded), receipts=provenance,
                source="BoatraceCSV historical card + realtime result, receipt-gated",
                research_only=True, formal_forecast_approved=False,
                history_sufficient=all(b["sufficient_sample"] for b in boats))

"""Restored BOAT EDGE scenario scorer, read-only and pre-race only.

The scoring coefficients and A/B head-world split below are ported from
boat-edge/index.html computeScores/buildFallbackPrediction (V127/V133 era).
The 120-way conditional ranking is an *uncalibrated extension* for the CLEAN
four-mode comparison, NOT the original formal CURRENT or a 70% hit claim.
No outcomes, odds, network, persistence or retrospective prediction here.
"""
from datetime import datetime, timedelta, timezone
from itertools import permutations
import math
import re

from clean_four_modes import rank_modes

JST = timezone(timedelta(hours=9))
MODEL_VERSION = "LEGACY_SCENARIO_SCORE_RESTORED_FOUR_MODE_REFERENCE_V1"
BASELINE_VERSION = "CLEAN_FOUR_MODES_V2_PROVISIONAL_UNCALIBRATED"
COUNTS = {"narrow": 5, "hit": 10, "balance": 16, "hole": 22}
COURSE_ATTACK = {1: 0.5, 2: 5.4, 3: 6.2, 4: 6.8, 5: 4.0, 6: 3.0}
LANE_BASE = {1: 9.5, 2: 7.0, 3: 5.8, 4: 5.2, 5: 3.2, 6: 2.2}


def _num(value):
    if type(value) in (int, float):
        return float(value) if math.isfinite(value) else None
    if type(value) is str and re.fullmatch(r"[+-]?(?:\d+(?:\.\d+)?|\.\d+)", value.strip()):
        n = float(value)
        return n if math.isfinite(n) else None
    # Signed F.03 is a start flag, not a positive +0.03/0.00 observation.
    return None


def _field(record, *keys):
    cur = record
    for key in keys:
        if type(cur) is not dict:
            return None
        cur = cur.get(key)
    return _num(cur)


def _clock(value):
    if type(value) is not str:
        raise ValueError("missing_original_clock")
    try:
        point = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("invalid_original_clock") from exc
    if point.utcoffset() != timedelta(hours=9):
        raise ValueError("unverified_jst_original_clock")
    return point


def _softmax(scores, temperature=12.0):
    top = max(scores.values())
    raw = {lane: math.exp((value - top) / temperature) for lane, value in scores.items()}
    total = sum(raw.values())
    return {lane: value / total for lane, value in raw.items()}


def _before_by_lane(items, field, required=False):
    if not isinstance(items, list):
        if required:
            raise ValueError("verified_exhibition_missing")
        return {}
    out = {}
    for item in items:
        if not isinstance(item, dict) or type(item.get("lane")) is not int:
            raise ValueError("invalid_exhibition_lane")
        lane = item["lane"]
        if not 1 <= lane <= 6 or lane in out:
            raise ValueError("duplicate_or_out_of_range_exhibition_lane")
        out[lane] = item
    if required and set(out) != set(range(1, 7)):
        raise ValueError("incomplete_verified_exhibition")
    return out


def restored_scenario_preview(card, now=None):
    """Compute OLD score/head world and NEW four-mode 120 extension once.

    A *current* PRE_RESULT six-racer card is mandatory; a historical card
    or post-deadline request fails closed and never produces hindsight tickets.
    No saved evidence is written, so this can NEVER join the formal 300+300
    prospective accuracy cohort without an independently reviewed collector.
    """
    now = datetime.now(JST) if now is None else now
    if (not isinstance(now, datetime) or now.utcoffset() != timedelta(hours=9)
            or type(card) is not dict or card.get("schema_version") != "boat-edge-race-v5"):
        raise ValueError("invalid_current_race_evidence")
    key = card.get("race_key")
    meta = card.get("meta")
    if (type(key) is not str or re.fullmatch(r"20\d{6}-(?:0[1-9]|1\d|2[0-4])-(?:0[1-9]|1[0-2])", key) is None
            or type(meta) is not dict
            or meta.get("date") != key[:4] + "-" + key[4:6] + "-" + key[6:8]
            or str(meta.get("venue_code")) != key[9:11]
            or meta.get("race_no") != int(key[12:14])
            or meta.get("phase") != "PRE_RESULT"
            or meta.get("results_seen") is not False or meta.get("unlock") is not False
            or meta.get("scoring") is not False or meta.get("historical_reference_only") is True):
        raise ValueError("not_a_live_pre_result_race")
    deadline = _clock(meta["date"] + "T" + str(meta.get("deadline", "")) + ":00+09:00")
    if now >= deadline:
        raise ValueError("race_deadline_already_passed")
    audit = card.get("source_audit")
    source = audit.get("race_card") if type(audit) is dict else None
    if (type(source) is not dict or source.get("status") != "ok"
            or source.get("predeadline_verified") is not True
            or type(source.get("sha256")) is not str
            or re.fullmatch("[a-f0-9]{64}", source["sha256"]) is None):
        raise ValueError("racecard_original_not_predeadline_verified")
    card_received = _clock(source.get("fetched_at"))
    if not card_received <= now or not card_received < deadline:
        raise ValueError("racecard_receipt_outside_cutoff")
    racers = card.get("racers")
    if type(racers) is not list or len(racers) != 6:
        raise ValueError("six_racers_required")
    by_lane = {}
    regs = set()
    for r in racers:
        if type(r) is not dict or type(r.get("lane")) is not int:
            raise ValueError("bad_racer")
        lane = r["lane"]
        reg = r.get("registration_no")
        if (lane in by_lane or lane not in LANE_BASE or type(reg) is not str
                or re.fullmatch(r"\d{4}", reg) is None or reg in regs):
            raise ValueError("wrong_race_six_registration_roster")
        regs.add(reg)
        by_lane[lane] = r
        status = " ".join(str(r.get(k, "")) for k in
                          ("scratch_status", "race_status", "entry_status", "status"))
        if (r.get("scratched") is True or r.get("withdrawn") is True
                or r.get("cancelled") is True or re.search("欠場|出走取消|不出走|withdrawn|scratched", status, re.I)):
            raise ValueError("scratched_boat_no_prediction")
        n = _field(r, "national", "win_rate")
        if n is None or not 0 < n <= 10:
            raise ValueError("missing_or_invalid_national_rate")
    if set(by_lane) != set(LANE_BASE):
        raise ValueError("six_boat_roster_incomplete")

    before = card.get("beforeinfo")
    before_audit = audit.get("beforeinfo") if type(audit) is dict else None
    verified_before = False
    if type(before) is dict and type(before_audit) is dict and before_audit.get("status") == "ok":
        before_received = _clock(before_audit.get("fetched_at"))
        verified_before = card_received <= now and before_received <= now and before_received < deadline
        if not verified_before:
            raise ValueError("exhibition_receipt_unverified")
    before = before if verified_before else {}
    br = _before_by_lane(before.get("racers"), "racers", required=verified_before)
    bs = _before_by_lane(before.get("start_exhibition"), "start", required=verified_before)
    entry = {}
    if verified_before:
        courses = [bs[i].get("course") for i in range(1, 7)]
        if (all(type(c) is int and 1 <= c <= 6 for c in courses)
                and len(set(courses)) == 6):
            entry = {i: courses[i-1] for i in range(1, 7)}
        # Preview course is NOT confirmed actual race entry.
    ex_times = {lane: _field(r, "exhibition_time") for lane, r in br.items()}
    times = [t for t in ex_times.values() if t is not None]
    ex_norm = {}
    if times:
        lo, hi = min(times), max(times)
        ex_norm = {lane: max(0.0, 1 - (value-lo)/max(hi-lo, 0.01))
                   for lane, value in ex_times.items() if value is not None}

    # Exact historical scoring coefficient table; absent fields contribute
    # nothing and are declared unavailable, NEVER represented as measured zero.
    scores = {}
    used = set(["national_win_rate", "lane_base"])
    missing = set()
    def contribution(r, keys, coefficient, label):
        n = _field(r, *keys)
        if n is None:
            missing.add(label)
            return 0.0
        used.add(label)
        return n * coefficient

    for lane, r in sorted(by_lane.items()):
        nat = _field(r, "national", "win_rate")
        base = nat*2.8 + LANE_BASE[lane]
        for keys, coeff, label in (
            (("national", "quinella_rate"), .18, "national_2ren"),
            (("local", "win_rate"), 1.9, "local_win_rate"),
            (("local", "quinella_rate"), .12, "local_2ren"),
            (("motor", "quinella_rate"), .11, "motor_2ren"),
            (("boat", "quinella_rate"), .07, "boat_2ren"),
        ):
            base += contribution(r, keys, coeff, label)
        avg = _field(r, "avg_st")
        if avg is None:
            missing.add("average_ST")
        else:
            used.add("average_ST")
            base += max(0.0, (.24-avg)*42)
        cls = r.get("class") or ""
        if not isinstance(cls, str):
            raise ValueError("invalid_class")
        base += 2.4 if "A1" in cls else 1.4 if "A2" in cls else .5 if "B1" in cls else 0.0
        used.add("class_grade")
        if lane in ex_norm:
            base += ex_norm[lane]*8
            used.add("exhibition_time")
        else:
            missing.add("exhibition_time")
        st = _field(bs.get(lane, {}), "st")
        if st is None:
            missing.add("numeric_exhibition_ST")
        else:
            base += max(0.0, (.25-st)*28)
            used.add("numeric_exhibition_ST")
        tilt = _field(br.get(lane, {}), "tilt")
        if tilt is not None:
            base += max(-1.0, min(2.5, tilt))
            used.add("tilt")
        else:
            missing.add("tilt")
        course = entry.get(lane)
        attack = COURSE_ATTACK.get(course, 0.0)
        inside = 8 if lane == 1 else (max(0, 5-abs(course-2)) if course else 0)
        scores[lane] = {
            "base": base,
            "inside": base + inside + (6 if lane == 1 else 0),
            "attack": base + attack + (2.5 if course in (3, 4) else 0),
            "course": course,
        }

    if entry:
        used.add("exhibition_course_only")
    else:
        missing.add("exhibition_course")
    missing.update(["actual_final_entry", "verified_two_course_wall_rate",
                    "original_exhibition", "weather_wave_tide_verified_coefficients",
                    "same_day_attack_distribution"])

    one = scores[1]
    challengers = sorted((lane for lane in range(2, 7)),
                         key=lambda lane: (-scores[lane]["attack"], lane))
    leader = challengers[0]
    diff = one["inside"] - scores[leader]["attack"]
    # Original V127 A/B world split. These numbers are heuristic, NOT
    # calibrated odds or an observed 3T hit rate.
    escape = max(.35, min(.78, (55 + diff*2.2)/100))
    attack_heads = challengers[:3]   # Preserve original challenger pool.
    attack_dist = _softmax({lane: scores[lane]["attack"] for lane in attack_heads}, 9)
    head = {lane: (escape if lane == 1 else (1-escape)*attack_dist.get(lane, 0.0))
            for lane in range(1, 7)}

    board = []
    for first, second, third in permutations(range(1, 7), 3):
        others = [lane for lane in range(1, 7) if lane != first]
        # Conditional second and third extensions reuse the ORIGINAL legacy
        # base/inner preference scores, but the softmax conversion is NEW.
        s2 = {lane: scores[lane]["base"] + (1.2 if first != 1 and lane == 1 else 0)
              for lane in others}
        p2 = _softmax(s2)[second]
        lasts = [lane for lane in others if lane != second]
        s3 = {lane: scores[lane]["base"] + (.8 if first != 1 and lane == 1 else 0)
              for lane in lasts}
        p3 = _softmax(s3)[third]
        board.append(((first, second, third), head[first]*p2*p3))
    if len(board) != 120 or not math.isclose(sum(p for _, p in board), 1, abs_tol=1e-9):
        raise ValueError("scenario_board_not_normalized")

    modes = rank_modes(board)
    first_order = sorted(head, key=lambda lane: (-head[lane], lane))
    output_modes = {}
    for mode, expected in COUNTS.items():
        ticket_rows = modes[mode]["tickets"]
        if len(ticket_rows) != expected:
            raise ValueError("four_mode_budget_changed")
        output_modes[mode] = {
            "tickets": ticket_rows,
            "count": expected,
            "uncalibrated_model_mass_pct": modes[mode]["estimated_coverage_pct"],
        }
    return {
        "ok": True, "status": "live_research_preview_not_saved",
        "race_code": key.replace("-", ""), "model_version": MODEL_VERSION,
        "base_engine": "boat-edge index.html computeScores / buildFallbackPrediction head-world",
        "board_extension": "research-only conditional softmax 120, NOT original formal CURRENT",
        "baseline_model_version": BASELINE_VERSION,
        "baseline_prediction_changed": False,
        "formal": False, "calibrated": False, "accuracy_improvement_proven": False,
        "independently_saved_before_T12": False, "production_buy_approved": False,
        "created_at_jst": now.isoformat(),
        "deadline_jst": deadline.isoformat(),
        "source_racecard_sha256": source["sha256"],
        "observed_exhibition_only": bool(entry),
        "actual_final_entry_verified": False,
        "used_features": sorted(used),
        "missing_or_unverified": sorted(missing),
        "worlds": {
            "one_escape_model_pct": round(escape*100, 2),
            "one_not_escape_model_pct": round((1-escape)*100, 2),
            "leading_attack_lane": leader,
            "assumption": "legacy_heuristic_not_measured_probability",
        },
        "head_top2_model_sum_pct": round(sum(sorted(head.values(), reverse=True)[:2])*100, 2),
        "head_top2_is_not_trifecta_hit70": True,
        "modes": output_modes,
        "message": "旧展開スコアを主軸にした未校正・未保存の参考予想。V2とは別に表示。正式な買い推奨ではありません。",
    }

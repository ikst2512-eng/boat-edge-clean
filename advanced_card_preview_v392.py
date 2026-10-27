#!/usr/bin/env python3
"""V392: official racelist-only EARLY reference ranking, separate from FINAL/V235.

No results, payouts, formal predictions, odds, beforeinfo, or actual-entry read.
Only prospective official six-boat race cards are permitted. This heuristic
ranking is NOT a calibrated probability or a production CURRENT prediction.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
import hashlib
import itertools
import json
from pathlib import Path
import re
import unicodedata
from urllib.parse import urlencode, urlparse, parse_qs

JST = timezone(timedelta(hours=9))
VENUES = dict(zip(
    [f"{i:02d}" for i in range(1, 25)],
    "桐生 戸田 江戸川 平和島 多摩川 浜名湖 蒲郡 常滑 津 三国 びわこ 住之江 尼崎 鳴門 丸亀 児島 宮島 徳山 下関 若松 芦屋 福岡 唐津 大村".split(),
))
REG = re.compile(r"\b(\d{4})\s*/\s*(A1|A2|B1|B2)\b")
KEY = re.compile(r"^20\d{6}-(?:0[1-9]|1\d|2[0-4])-(?:0[1-9]|1[0-2])$")
SCRATCH = re.compile(r"欠場|出走取消|出走取り消し|不出走|scratched|withdrawn", re.I)
SCHEMA = "BOAT_EDGE_V392_CARD_ONLY_PREVIEW_V1"
MODEL = "V392-CARD-HEURISTIC-UNCALIBRATED"
BASE = "https://www.boatrace.jp/owpc/pc/race/"


def jstnow():
    return datetime.now(JST)


def normalized(value):
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", value or "")).strip()


def get_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError):
        return None


def put_json_if_changed(path, value):
    raw = (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()
    if path.is_file() and path.read_bytes() == raw:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    return True


def formal_closed(root):
    status = get_json(root / "data/formal_status.json") or {}
    guards = status.get("guards") or {}
    if not all(guards.get(k) is False for k in ("results_seen", "unlock", "scoring")):
        raise RuntimeError("V392_FORMAL_GUARDS_NOT_CLOSED")
    if guards.get("RESULT_UNLOCK_TOKEN") is not None:
        raise RuntimeError("V392_FORMAL_UNLOCK_TOKEN_SET")


def deadline(key, clock):
    if not KEY.fullmatch(str(key)) or not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", str(clock)):
        return None
    try:
        return datetime.strptime(key[:8] + clock, "%Y%m%d%H:%M").replace(tzinfo=JST)
    except ValueError:
        return None


def card_fingerprint(race):
    """Stable projection: volatile official page HTML and fetch time are excluded."""
    meta = race.get("meta") or {}
    rows = race.get("racers") or []
    projection = {
        "race_key": race.get("race_key"),
        "date": meta.get("date"), "deadline": meta.get("deadline"),
        "racers": [{
            "lane": r.get("lane"), "registration_no": r.get("registration_no"),
            "class": r.get("class"), "avg_st": r.get("avg_st"),
            "national": r.get("national"), "local": r.get("local"),
            "motor": r.get("motor"),
        } for r in rows if isinstance(r, dict)],
    }
    raw = json.dumps(projection, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def usable_card(race, now):
    if not isinstance(race, dict):
        return False
    key = race.get("race_key")
    if not isinstance(key, str) or not KEY.fullmatch(key):
        return False
    meta = race.get("meta") or {}
    if meta.get("phase") != "PRE_RESULT" or any(meta.get(k) is not False
        for k in ("results_seen", "unlock", "scoring")):
        return False
    if (meta.get("date") != f"{key[:4]}-{key[4:6]}-{key[6:8]}"
        or str(meta.get("venue_code")).zfill(2) != key[9:11]
        or meta.get("race_no") != int(key[12:14])):
        return False
    due = deadline(key, meta.get("deadline"))
    if not due or due <= now:
        return False
    source = (race.get("source_audit") or {}).get("race_card") or {}
    if (source.get("status") != "ok"
        or not re.fullmatch(r"[a-f0-9]{64}", str(source.get("sha256") or ""))):
        return False
    try:
        source_at = datetime.fromisoformat(str(source.get("fetched_at")))
        if source_at.tzinfo is None or source_at > now + timedelta(minutes=1) or source_at >= due:
            return False
    except (TypeError, ValueError):
        return False
    rows = race.get("racers")
    if not isinstance(rows, list) or len(rows) != 6:
        return False
    lanes = [r.get("lane") for r in rows if isinstance(r, dict)]
    regs = [str(r.get("registration_no") or "") for r in rows if isinstance(r, dict)]
    if sorted(lanes, key=lambda x: (not isinstance(x, int), str(x))) != [1, 2, 3, 4, 5, 6] or len(set(regs)) != 6 or any(not re.fullmatch(r"\d{4}", r) for r in regs):
        return False
    for racer in rows:
        flags = " ".join(str(racer.get(k) or "") for k in ("raw_text", "status", "entry_status", "race_status"))
        if SCRATCH.search(flags) or any(racer.get(k) is True
            for k in ("scratched", "withdrawn", "absent", "cancelled", "canceled")):
            return False
    return True


def numeric(value, minimum, maximum):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value) if minimum <= value <= maximum else None


def make_preview(race, now):
    if not usable_card(race, now):
        return None
    rows = sorted(race["racers"], key=lambda r: r["lane"])
    score = {}
    missing = set()
    for row in rows:
        lane = row["lane"]
        n = row.get("national") or {}
        local = row.get("local") or {}
        motor = row.get("motor") or {}
        win = numeric(n.get("win_rate"), 0, 12)
        local_win = numeric(local.get("win_rate"), 0.01, 12)
        motor_q = numeric(motor.get("quinella_rate"), 0, 100)
        avg_st = numeric(row.get("avg_st"), 0, 0.5)
        if win is None:
            missing.add("national.win_rate")
        if local_win is None:
            missing.add("local.win_rate")
        if motor_q is None:
            missing.add("motor.quinella_rate")
        if avg_st is None:
            missing.add("avg_st")
        # Fixed, transparent, uncalibrated card-only reference score.
        # A missing field contributes NO bonus; it is not synthesized.
        base = (win / 12 * 1.5 if win is not None else 0)
        base += (local_win / 12 * 0.25 if local_win is not None else 0)
        base += (motor_q / 100 * 0.35 if motor_q is not None else 0)
        base += ({ "A1": .23, "A2": .15, "B1": .06, "B2": 0 }.get(row.get("class"), 0))
        base += ((.22 - avg_st) * .6 if avg_st is not None else 0)
        score[lane] = base
    course_prior = {1:.65, 2:.24, 3:.08, 4:-.08, 5:-.25, 6:-.42}
    combos = []
    for a, b, c in itertools.permutations(range(1, 7), 3):
        ranking_score = (1.35 * (score[a] + course_prior[a])
                         + .85 * score[b] + .24 * course_prior[b]
                         + .57 * score[c])
        combos.append((round(ranking_score, 8), f"{a}-{b}-{c}"))
    combos.sort(key=lambda r: (-r[0], r[1]))
    meta = race["meta"]
    src = race["source_audit"]["race_card"]
    key = race["race_key"]
    return {
        "schema": SCHEMA, "model_id": MODEL,
        "prediction_kind": "EARLY_CARD_ONLY_REFERENCE_NOT_FINAL",
        "race_key": key,
        "source_date": meta["date"], "deadline": meta["deadline"],
        "produced_at": now.isoformat(),
        "source_card_sha256": src["sha256"], "source_card_fetched_at": src["fetched_at"],
        "card_fingerprint_sha256": card_fingerprint(race),
        "registrations_by_lane": [r["registration_no"] for r in rows],
        "racer_inputs_by_lane": [
            [r["lane"], r["registration_no"], r.get("class"), r.get("avg_st"),
             (r.get("national") or {}).get("win_rate"),
             (r.get("local") or {}).get("win_rate"),
             (r.get("motor") or {}).get("quinella_rate")]
            for r in rows
        ],
        "head_candidate": int(combos[0][1][0]),
        "ranked_120": [{"rank": i+1, "combo": combo, "relative_score": value}
                       for i, (value, combo) in enumerate(combos)],
        "top3": [combo for _, combo in combos[:3]],
        "top5": [combo for _, combo in combos[:5]],
        "top10": [combo for _, combo in combos[:10]],
        "missing_card_fields": sorted(missing),
        "course_assumption": "LANE_EQUALS_COURSE_UNTIL_ENTRY_PUBLISHED",
        "score_is_calibrated_probability": False,
        "odds_used": False, "stake_yen": None, "betting_enabled": False,
        "guards": {"results_seen": False, "unlock": False, "scoring": False},
        "formal_fresh_claim": False,
    }


def save_preview(root, race, now):
    preview = make_preview(race, now)
    if not preview:
        return False
    path = root / "data/site_early_previews" / (race["race_key"] + ".json")
    previous = get_json(path)
    # The public preview renderer binds a preview to the exact official card
    # source SHA *and fetch timestamp*. A new official fetch may retain the
    # same six-racer semantic fingerprint. Refresh source provenance without
    # changing the 120-way ranking; otherwise the real-site renderer must hide
    # the stale preview on every routine PRE_RESULT collector update.
    if (isinstance(previous, dict) and previous.get("schema") == SCHEMA
        and previous.get("card_fingerprint_sha256") == preview["card_fingerprint_sha256"]
        and previous.get("source_card_sha256") == preview["source_card_sha256"]
        and previous.get("source_card_fetched_at") == preview["source_card_fetched_at"]):
        return False
    return put_json_if_changed(path, preview)


def build_today(root, now):
    doc = get_json(root / "data/today.json") or {}
    if str(doc.get("date") or "").replace("-", "") != now.strftime("%Y%m%d"):
        return {"candidates": 0, "updated": 0}
    candidates = changed = 0
    for venue in doc.get("venues") or []:
        for row in venue.get("races") or []:
            key = row.get("race_key")
            if not isinstance(key, str) or not KEY.fullmatch(key) or not key.startswith(now.strftime("%Y%m%d")):
                continue
            race = get_json(root / "data/races" / (key + ".json"))
            if not usable_card(race, now):
                continue
            candidates += 1
            changed += int(save_preview(root, race, now))
    return {"candidates": candidates, "updated": changed}


def strict_official_get(session, date, venue, race=None):
    """No redirect, cross-date or result URL; bind request to exact response."""
    args = {"hd": date, "jcd": venue}
    name = "racelist" if race is not None else "index"
    if race is not None:
        args["rno"] = str(int(race))
    else:
        args = {"hd": date}
    url = BASE + name + "?" + urlencode(args)
    response = session.get(url, timeout=(4, 12), allow_redirects=False)
    if response.status_code != 200 or response.url != url:
        raise ValueError("V392_OFFICIAL_SOURCE_NOT_EXACT_200")
    response.encoding = response.apparent_encoding or response.encoding or "utf-8"
    return response


def discover_venues(session, date):
    from bs4 import BeautifulSoup
    response = strict_official_get(session, date, None)
    soup = BeautifulSoup(response.text, "lxml")
    active = set()
    for anchor in soup.find_all("a", href=True):
        u = urlparse(anchor["href"])
        if u.path not in ("/owpc/pc/race/racelist", "/owpc/pc/race/index"):
            continue
        q = parse_qs(u.query)
        code = (q.get("jcd") or [""])[0].zfill(2)
        if (q.get("hd") or [""])[0] == date and code in VENUES:
            active.add(code)
    return sorted(active)


def official_racers(html):
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "lxml")
    racer_rows = []
    seen = set()
    for tr in soup.find_all("tr"):
        text = normalized(tr.get_text(" ", strip=True))
        match = REG.search(text)
        if not match:
            continue
        reg, classification = match.groups()
        if reg in seen:
            continue
        lane_match = re.match(r"\s*([1-6])\b", text)
        if not lane_match:
            continue
        lane = int(lane_match.group(1))
        if SCRATCH.search(text):
            continue
        name = None
        for link in tr.find_all("a"):
            val = normalized(link.get_text(" ", strip=True))
            if val and not re.fullmatch(r"\d+R?", val):
                name = val
                break
        avg = re.search(r"\bF\d+\s+L\d+\s+(-|0\.\d{2})\s+(.*)$", text)
        values = []
        st = None
        if avg:
            st = None if avg.group(1) == "-" else float(avg.group(1))
            values = avg.group(2).split()
        def field(k):
            try:
                return None if values[k] == "-" else float(values[k])
            except (ValueError, IndexError):
                return None
        racer_rows.append({
            "lane": lane, "registration_no": reg, "name": name, "class": classification,
            "avg_st": st,
            "national": {"win_rate": field(0), "quinella_rate": field(1), "trio_rate": field(2)},
            "local": {"win_rate": field(3), "quinella_rate": field(4), "trio_rate": field(5)},
            "motor": {"quinella_rate": field(7), "trio_rate": field(8)},
            "raw_text": text,
        })
        seen.add(reg)
    racer_rows.sort(key=lambda r: r["lane"])
    return racer_rows if len(racer_rows) == 6 and [r["lane"] for r in racer_rows] == list(range(1, 7)) else []


def official_deadlines(html):
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "lxml")
    for tr in soup.find_all("tr"):
        t = normalized(tr.get_text(" ", strip=True))
        if "締切予定時刻" not in t:
            continue
        clocks = re.findall(r"\b(?:[01]?\d|2[0-3]):[0-5]\d\b", t)
        if len(clocks) >= 12:
            return [v.zfill(5) for v in clocks[:12]]
    return []


def collect_tomorrow(root, now, session=None):
    """Future-only separate input catalog; never change canonical data/races."""
    from bs4 import BeautifulSoup
    import requests
    date = (now + timedelta(days=1)).strftime("%Y%m%d")
    if not (16 <= now.hour <= 23):
        return {"status": "OUTSIDE_NIGHTLY_COLLECTION_WINDOW", "date": date}
    idxpath = root / "data/site_early_calendar" / (date + ".json")
    latest = get_json(idxpath) or {}
    # Limit official traffic even when the every-five-minute collector calls us.
    try:
        last = datetime.fromisoformat(latest["collected_at"])
        if last.tzinfo and 0 <= (now-last).total_seconds() < 3*3600:
            return {"status": "RECENT_EVIDENCE_REUSED", "date": date}
    except (KeyError, TypeError, ValueError):
        pass
    own = session is None
    if own:
        session = requests.Session()
        session.headers.update({"User-Agent": "Mozilla/5.0 Chrome/140 Safari/537.36",
                                "Accept-Language": "ja-JP,ja;q=0.9"})
    try:
        try:
            venues = discover_venues(session, date)
        except Exception:
            venues = []
        # A closed/empty index is not evidence that a scheduled next-day event
        # is absent. Probe only 24 racelist PRE_RESULT pages in that case.
        if not venues:
            def probe(code):
                try:
                    page = strict_official_get(session, date, code, 1)
                    return code if official_racers(page.text) else None
                except Exception:
                    return None
            with ThreadPoolExecutor(max_workers=8) as pool:
                venues = sorted(set(v for v in pool.map(probe, VENUES) if v))
        def venue_source(code):
            try:
                page = strict_official_get(session, date, code, 1)
                return code, official_deadlines(page.text)
            except Exception:
                return code, []
        with ThreadPoolExecutor(max_workers=8) as pool:
            clockmap = dict(pool.map(venue_source, venues))
        tasks = [(code, race, clockmap[code][race-1])
                 for code in venues if len(clockmap.get(code, [])) == 12
                 for race in range(1, 13)]
        def collect(task):
            code, race_no, clock = task
            key = f"{date}-{code}-{race_no:02d}"
            if deadline(key, clock) <= now:
                return None
            try:
                page = strict_official_get(session, date, code, race_no)
                racers = official_racers(page.text)
                if not racers:
                    return None
                fetched = jstnow()
                raw = page.content
                card = {
                    "schema_version": "boat-edge-early-race-v392",
                    "race_key": key,
                    "meta": {"date": f"{date[:4]}-{date[4:6]}-{date[6:8]}",
                             "venue_code": code, "venue": VENUES[code],
                             "race_no": race_no, "deadline": clock,
                             "updated_at": fetched.isoformat(),
                             "phase": "PRE_RESULT", "results_seen": False,
                             "unlock": False, "scoring": False},
                    "source_audit": {"race_card": {
                        "status": "ok",
                        "source": BASE + "racelist?" + urlencode({"hd": date, "jcd": code, "rno": str(race_no)}),
                        "fetched_at": fetched.isoformat(),
                        "sha256": hashlib.sha256(raw).hexdigest(),
                    }, "beforeinfo": {"status": "not_in_window"}},
                    "racers": racers,
                    "beforeinfo": {},
                }
                return key, card
            except Exception:
                return None
        found = []
        with ThreadPoolExecutor(max_workers=12) as pool:
            for rec in pool.map(collect, tasks):
                if rec:
                    found.append(rec)
        if not found:
            return {"status": "NO_VERIFIED_NEXT_DAY_CARDS", "date": date, "venues": len(venues)}
        saved = 0
        grouped = {}
        for key, card in found:
            saved += int(put_json_if_changed(root / "data/early_races" / (key + ".json"), card))
            # Official response may arrive minutes after the batch began.
            # Bind the reference ranking to the actual source collection time.
            fetch_at = datetime.fromisoformat(card["source_audit"]["race_card"]["fetched_at"])
            saved += int(save_preview(root, card, max(now, fetch_at)))
            code = key[9:11]
            grouped.setdefault(code, []).append({
                "race_key": key, "race_no": int(key[12:14]), "deadline": card["meta"]["deadline"],
                "jcd": code, "file": "data/early_races/" + key + ".json",
                "has_odds": False, "result_status": "future_pre_result",
            })
        calendar = {
            "schema": "BOAT_EDGE_V392_NEXT_DAY_CARDS_V1",
            "ymd": date, "date": f"{date[:4]}-{date[4:6]}-{date[6:8]}",
            "collected_at": now.isoformat(), "scope": "FUTURE_PRE_RESULT_CARD_ONLY",
            "venues": [{
                "jcd": code, "venue": VENUES[code],
                "event": None, "races": sorted(rows, key=lambda row: row["race_no"]),
            } for code, rows in sorted(grouped.items())],
        }
        put_json_if_changed(idxpath, calendar)
        put_json_if_changed(root / "data/site_early_calendar/index.json", {
            "schema": "BOAT_EDGE_V392_NEXT_DAY_INDEX_V1", "dates": [date],
            "source": "OFFICIAL_RACELIST_ONLY_NO_RESULT",
        })
        return {"status": "VERIFIED_CARD_PREVIEWS", "date": date,
                "cards": len(found), "written": saved, "venues": len(grouped)}
    finally:
        if own:
            session.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--mode", choices=("today", "tomorrow"), required=True)
    args = parser.parse_args()
    root = Path(args.root).resolve()
    formal_closed(root)
    now = jstnow()
    status = build_today(root, now) if args.mode == "today" else collect_tomorrow(root, now)
    print("V392_CARD_ONLY_PRE_RESULT " + json.dumps(status, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()

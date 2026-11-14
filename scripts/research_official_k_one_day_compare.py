#!/usr/bin/env python3
"""Decode ONE official 2026-08-01 BOAT RACE K file and reconcile to frozen secondary.
Research-only postrace evidence; NEVER a T-12 forecast input or official 92-day certification.
"""
from __future__ import annotations
import argparse
import csv
import ctypes
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

DAY = "20260801"
OFFICIAL_SHA256 = "8e95b7ddce0fe7849179c1a6cf69e4ad938fada13da527410d29f610709ff8ba"
SECONDARY_BLOB_SHA = "d78e11ebc5af666487f50e72258267a79f959486"
RACE = re.compile(r"^\s{2,}(\d{1,2})R\s{3,}.*H\d{4}m.*?風\s+(.+?)\s+(\d+)m\s+波\s+(\d+)cm")
ENTRY = re.compile(r"^\s{2,}(\d{2}|S[0-2]|K[0-2]|L[0-2]|F|転|エ|妨|沈|落)\s+([1-6])\s+(\d{4})\s+(.+)$")
COURSE = re.compile(r"\s+\d{1,3}\s+\d{1,3}\s+\d+\.\d+\s+([1-6])\s+([+-]?\d+\.\d+|[FL]\d*\.\d+)")
RANKS = {f"{i:02d}" for i in range(1, 7)}

def git_blob_sha(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()

def unpack_lha(raw: bytes, day: str = DAY) -> bytes:
    """Linux libarchive LHA decoder, all in memory; reject unexpected entries."""
    try:
        lib = ctypes.CDLL("libarchive.so.13")
    except OSError as exc:
        raise ValueError("libarchive_missing") from exc
    def fn(name, returns, args):
        f = getattr(lib, name)
        f.restype, f.argtypes = returns, args
        return f
    p = ctypes.c_void_p
    new = fn("archive_read_new", p, [])
    enable = fn("archive_read_support_format_lha", ctypes.c_int, [p])
    open_mem = fn("archive_read_open_memory", ctypes.c_int, [p, p, ctypes.c_size_t])
    next_item = fn("archive_read_next_header", ctypes.c_int, [p, ctypes.POINTER(p)])
    pathname = fn("archive_entry_pathname", ctypes.c_char_p, [p])
    entry_size = fn("archive_entry_size", ctypes.c_longlong, [p])
    read = fn("archive_read_data", ctypes.c_ssize_t, [p, p, ctypes.c_size_t])
    free = fn("archive_read_free", ctypes.c_int, [p])
    obj = new()
    backing = ctypes.create_string_buffer(raw)
    try:
        if enable(obj) != 0 or open_mem(obj, backing, len(raw)) != 0:
            raise ValueError("lha_open_failed")
        header = p()
        if next_item(obj, ctypes.byref(header)) != 0:
            raise ValueError("lha_empty")
        if pathname(header) != ("K" + day[2:] + ".TXT").encode("ascii"):
            raise ValueError("lha_filename_mismatch")
        expected = entry_size(header)
        if not 0 < expected <= 2000000:
            raise ValueError("lha_uncompressed_size_invalid")
        out = bytearray()
        buffer = ctypes.create_string_buffer(32768)
        while len(out) <= 2000000:
            n = read(obj, buffer, len(buffer))
            if n < 0:
                raise ValueError("lha_decompress_error")
            if n == 0:
                break
            out.extend(buffer.raw[:n])
        if len(out) != expected:
            raise ValueError("lha_uncompressed_length_mismatch")
        if next_item(obj, ctypes.byref(header)) != 1:
            raise ValueError("lha_extra_entry_or_error")
        return bytes(out)
    finally:
        free(obj)

def parse_k(text: str, day: str = DAY, expected_races: int = 156, allow_unsettled: bool = False) -> dict:
    venue, current, active = None, None, False
    races = {}
    lines = text.splitlines()
    for i, line in enumerate(lines):
        vm = re.fullmatch(r"(\d{2})KBGN", line)
        if vm:
            venue, current, active = vm.group(1), None, False
            continue
        h = RACE.match(line)
        if h:
            if venue is None:
                raise ValueError("race_outside_venue")
            code = day + venue + f"{int(h.group(1)):02d}"
            if code in races:
                raise ValueError("duplicate_k_race:" + code)
            heading = lines[i + 1].split("ﾚｰｽﾀｲﾑ")
            if len(heading) != 2:
                raise ValueError("missing_k_method:" + code)
            current = {
                "code": code, "venue": venue, "method": "".join(heading[1].split()),
                "wind_m": int(h.group(3)), "wave_cm": int(h.group(4)),
                "wind_direction_text": "".join(h.group(2).split()), "entries": [], "unsettled": False,
            }
            races[code] = current
            active = True
            continue
        if "レース不成立" in line and current is not None:
            current["unsettled"] = True
            active = False
        if re.match(r"^\s+単勝\s+", line):
            active = False
        if not active or current is None:
            continue
        entry = ENTRY.match(line)
        if not entry:
            continue
        status, boat, athlete, tail = entry.groups()
        cs = COURSE.search(tail)
        if status == "F" and not cs:
            raise ValueError("official_F_course_unparsed:" + current["code"])
        current["entries"].append({
            "status": status, "boat": int(boat), "athlete_registration": athlete,
            "course": int(cs.group(1)) if cs else None,
            "st": cs.group(2) if cs else None,
        })
    if not 1 <= expected_races <= 288 or len(races) != expected_races:
        raise ValueError("official_race_count_mismatch:" + str(len(races)) + ":" + str(expected_races))
    for code, item in races.items():
        entries = item["entries"]
        if len(entries) != 6 or {e["boat"] for e in entries} != set(range(1, 7)):
            raise ValueError("official_six_boat_validation_failed:" + code)
        winners = sum(e["status"] == "01" for e in entries)
        if winners != 1:
            if not (allow_unsettled and winners == 0 and item["unsettled"] and item["method"] == ""):
                raise ValueError("official_winner_missing_or_duplicate:" + code)
    return races

def compare(official: dict, secondary_raw: bytes, expected_secondary_sha: str = SECONDARY_BLOB_SHA, day: str = DAY) -> dict:
    sha = git_blob_sha(secondary_raw)
    if sha != expected_secondary_sha:
        raise ValueError("secondary_git_blob_mismatch:" + sha)
    rows = list(csv.DictReader(secondary_raw.decode("utf-8-sig").splitlines()))
    by_code = {r.get("レースコード", ""): r for r in rows}
    if len(rows) != len(by_code) or set(by_code) != set(official):
        raise ValueError("official_secondary_race_universe_differs")
    matches, differences = Counter(), []
    status_count = Counter()
    by_venue = Counter()
    no_course = []
    for key, k in sorted(official.items()):
        row = by_code[key]
        by_venue[k["venue"]] += 1
        entries = k["entries"]
        winner = next(e["boat"] for e in entries if e["status"] == "01")
        status_count.update(e["status"] for e in entries if e["status"] not in RANKS)
        finish = {e["status"]: str(e["boat"]) for e in entries if e["status"] in RANKS}
        checks = {
            "winner": row["1着_艇番"] == str(winner),
            "method": "".join(row["決まり手"].split()) == k["method"],
            "wind_m": float(row["風速(m)"]) == k["wind_m"],
            "wave_cm": float(row["波の高さ(cm)"]) == k["wave_cm"],
        }
        for n in range(1, 7):
            checks[f"finish{n}"] = row[f"{n}着_艇番"] == finish.get(f"{n:02d}", "")
        courses = [e for e in entries if e["course"] is not None]
        if len(courses) == 6 and {e["course"] for e in courses} == set(range(1, 7)):
            for e in courses:
                course = e["course"]
                checks[f"course{course}"] = row[f"{course}コース_艇番"] == str(e["boat"])
                is_f = bool(e["st"] and e["st"].startswith("F"))
                checks[f"fmark{course}"] = ((row[f"{course}コース_F"].strip() == "F") == is_f)
                if e["st"] and (e["st"].startswith("0.") or is_f):
                    try:
                        official_st = -float(e["st"][1:]) if is_f else float(e["st"])
                        checks[f"st{course}"] = abs(
                            float(row[f"{course}コース_スタートタイミング"]) - official_st
                        ) < .005
                    except (TypeError, ValueError):
                        checks[f"st{course}"] = False
        else:
            no_course.append(key)
        for field, passed in checks.items():
            if passed:
                matches[field] += 1
            else:
                differences.append({"race_code": key, "field": field})
    return {
        "schema": "OFFICIAL_K_ONE_DAY_INDEPENDENT_RECONCILIATION_V1",
        "classification": "official_primary_vs_secondary_postrace_research_not_T12",
        "day": day[:4] + "-" + day[4:6] + "-" + day[6:], "official_races": len(official),
        "secondary_rows": len(rows), "secondary_git_blob_sha": sha,
        "official_venue_race_counts": dict(sorted(by_venue.items())),
        "field_match_counts": dict(sorted(matches.items())),
        "field_discrepancy_count": len(differences), "field_discrepancies": differences,
        "official_special_status_counts": dict(sorted(status_count.items())),
        "course_not_fully_comparable_race_codes": no_course,
        "official_K_full_92day_certified": False,
        "official_c1_denominator_defined_or_established": False,
        "T12_eligible": False, "forecast_model_change_authorized": False,
    }

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--k-archive", required=True, type=Path)
    parser.add_argument("--secondary-csv", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    raw = args.k_archive.read_bytes()
    sha = hashlib.sha256(raw).hexdigest()
    if sha != OFFICIAL_SHA256:
        raise ValueError("official_K_SHA256_receipt_mismatch:" + sha)
    extracted = unpack_lha(raw)
    official = parse_k(extracted.decode("cp932"))
    result = compare(official, args.secondary_csv.read_bytes())
    result["official_archive_sha256"] = sha
    result["official_decoded_text_sha256"] = hashlib.sha256(extracted).hexdigest()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "official_races": result["official_races"], "secondary_rows": result["secondary_rows"],
        "field_discrepancies": result["field_discrepancy_count"],
        "official_full_period_certified": False,
    }, ensure_ascii=False))

if __name__ == "__main__":
    main()

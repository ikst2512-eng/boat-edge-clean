"""Read-only real-source acquisition diagnostic. Never stores payloads or publishes data."""
import argparse
import csv
import io
import hashlib
import json
import re
from html.parser import HTMLParser
from datetime import datetime, timezone
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from pathlib import Path

SOURCES = {
    "race_csv": "https://boatracecsv.github.io/data/programs/race_cards/{year}/{month}/{day}.csv",
    "preview_stt": "https://boatracecsv.github.io/data/previews/stt/{year}/{month}/{day}.csv",
    "preview_tkz": "https://boatracecsv.github.io/data/previews/tkz/{year}/{month}/{day}.csv",
    "preview_sui": "https://boatracecsv.github.io/data/previews/sui/{year}/{month}/{day}.csv",
    "official_racelist": "https://www.boatrace.jp/owpc/pc/race/racelist?hd={date}&jcd={venue}&rno={race}",
    "official_beforeinfo": "https://www.boatrace.jp/owpc/pc/race/beforeinfo?hd={date}&jcd={venue}&rno={race}",
}

class OfficialHtmlScanner(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.title = []
        self._in_title = False
        self.row_candidates = []
        self.all_table_rows = []
        self.current_row = None
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "tr":
            self.current_row = {"registrations": [], "text": []}
        if tag == "title":
            self._in_title = True
        if tag == "a":
            href = attrs.get("href", "")
            if "toban=" in href or "racer" in href:
                self.links.append(href)
                if "toban=" in href:
                    found = re.search(r"toban=([0-9]{4})", href)
                    if found and self.current_row is not None:
                        self.current_row["registrations"].append(found.group(1))
    def handle_endtag(self, tag):
        if tag == "tr" and self.current_row is not None:
            if self.current_row["text"]:
                self.all_table_rows.append(" ".join(self.current_row["text"])[:160])
            unique = list(dict.fromkeys(self.current_row["registrations"]))
            if unique:
                self.row_candidates.append({"registrations": unique, "text_sample": " ".join(self.current_row["text"])[:160]})
            self.current_row = None
        if tag == "title":
            self._in_title = False
    def handle_data(self, data):
        if self.current_row is not None and data.strip():
            self.current_row["text"].append(data.strip())
        if self._in_title:
            self.title.append(data)

def html_diagnostics(body):
    try:
        text = body.decode("utf-8")
    except UnicodeDecodeError:
        return {"html_inspection": "blocked_encoding"}
    if "<html" not in text.lower():
        return {"html_inspection": "blocked_not_html"}
    scanner = OfficialHtmlScanner()
    scanner.feed(text)
    order = []
    for link in scanner.links:
        found = re.search(r"toban=([0-9]{4})", link)
        if found and found.group(1) not in order:
            order.append(found.group(1))
    lane_rows = {}
    for row in scanner.row_candidates:
        if len(row["registrations"]) != 1:
            continue
        found = re.match(r"^([１２３４５６1-6])\s+([0-9]{4})(?:\s|/|$)", row["text_sample"])
        if not found or found.group(2) != row["registrations"][0]:
            continue
        lane = "１２３４５６".find(found.group(1)) + 1 if found.group(1) in "１２３４５６" else int(found.group(1))
        if lane in lane_rows:
            lane_rows = {}
            break
        lane_rows[lane] = found.group(2)
    preview_values = {}
    for row in scanner.row_candidates:
        if len(row["registrations"]) != 1:
            continue
        found = re.match(r"^([1-6])\s+(.+?)\s+([0-9]+(?:\.[0-9]+)?)kg\s+([0-9]+\.[0-9]{2})\s+(-?[0-9]+\.[0-9]+)(?:\s|$)", row["text_sample"])
        if found:
            lane = int(found.group(1))
            if lane in preview_values:
                preview_values = {}
                break
            preview_values[lane] = {"registration": row["registrations"][0], "time": found.group(4), "tilt": found.group(5)}
    official_st_by_course = {}
    if "スタート展示" in scanner.all_table_rows:
        start = scanner.all_table_rows.index("スタート展示")
        for sample in scanner.all_table_rows[start + 1: start + 20]:
            match = re.fullmatch(r"([1-6])\s+([F-]?\.?[0-9]{1,2})", sample)
            if match:
                course = int(match.group(1))
                if course in official_st_by_course:
                    official_st_by_course = {}
                    break
                official_st_by_course[course] = match.group(2)
    return {"html_inspection": "structure_only_unverified",
            "html_title": "".join(scanner.title).strip()[:100],
            "racer_link_count": len(scanner.links),
            "toban_parameter_count": len(re.findall(r"toban=", text)),
            "html_is_race_verified": False,
            "official_st_by_course": official_st_by_course if set(official_st_by_course) == set(range(1, 7)) else {},
            "preview_value_candidates": preview_values if set(preview_values) == set(range(1,7)) else {},
            "lane_registration_candidates": lane_rows if set(lane_rows) == set(range(1, 7)) else {},
            "registration_order_candidates": order[:12],
            "registration_candidates": sorted(set(re.findall(r"[?&]toban=([0-9]{4})(?:[&#\"\\s]|$)", text)))[:30]}

def probe(date, venue, race, opener=urlopen):
    datetime.strptime(date, "%Y%m%d")
    if not (venue.isdigit() and 1 <= int(venue) <= 24 and race.isdigit() and 1 <= int(race) <= 12):
        raise ValueError("invalid venue or race")
    vals = dict(date=date, year=date[:4], month=date[4:6], day=date[6:8],
                venue=f"{int(venue):02d}", race=str(int(race)))
    report = {"race_key": f"{date}-{vals['venue']}-{int(race):02d}",
              "observed_at": datetime.now(timezone.utc).isoformat(),
              "status": "UNVERIFIED", "sources": {}}
    for name, template in SOURCES.items():
        url = template.format(**vals)
        entry = {"url": url, "status": "unavailable"}
        try:
            request = Request(url, headers={"User-Agent": "BOAT-EDGE-CLEAN-STAGING/1.0"})
            with opener(request, timeout=12) as response:
                body = response.read(2_000_001)
                entry["http_status"] = response.status
                entry["content_type"] = response.headers.get("Content-Type", "")
                if response.status != 200 or not body or len(body) > 2_000_000:
                    raise ValueError("invalid response or size")
                entry["bytes"] = len(body)
                entry["sha256"] = hashlib.sha256(body).hexdigest()
                entry["status"] = "retrieved_unverified"
                if name not in ("official_racelist", "official_beforeinfo"):
                    try:
                        decoded = body.decode("utf-8-sig")
                        reader = csv.DictReader(io.StringIO(decoded))
                        fields = reader.fieldnames or []
                        entry["csv_columns"] = fields[:12]
                        if "レースコード" not in fields:
                            entry["race_rows"] = "schema_missing_race_code"
                            entry["race_identity_status"] = "blocked"
                        else:
                            target = date + vals["venue"] + f"{int(race):02d}"
                            codes = [row.get("レースコード", "").strip() for row in reader]
                            entry["csv_total_rows"] = len(codes)
                            entry["csv_sample_race_codes"] = codes[:5]
                            matches = sum(code == target for code in codes)
                            entry["race_rows"] = matches
                            entry["race_identity_status"] = "single_row_unverified" if matches == 1 else "blocked"
                            if matches == 1:
                                from clean_csv_staging import map_race_card
                                from clean_preview_staging import stage_preview
                                try:
                                    if name == "race_csv":
                                        mapped = map_race_card(decoded, target, url, report["observed_at"])
                                    else:
                                        mapped = stage_preview(decoded, target, name.removeprefix("preview_"), url)
                                        if name == "preview_stt":
                                            entry["course_st_by_boat"] = mapped["values"]
                                        if name == "preview_tkz":
                                            entry["tilt_time_by_lane"] = mapped["values"]
                                    if name == "race_csv":
                                        entry["registration_numbers"] = sorted(x["registration"] for x in mapped["racers"])
                                        entry["registration_in_lane_order"] = [x["registration"] for x in mapped["racers"]]
                                    entry["record_validation"] = "schema_pass_unverified"
                                    entry["record_fields"] = len(mapped["racers"]) if name == "race_csv" else len(mapped["values"])
                                except (ValueError, KeyError, TypeError) as error:
                                    entry["record_validation"] = "blocked"
                                    entry["validation_error"] = str(error)[:150]
                                    if name == "preview_stt" and str(error) == "invalid exhibition ST":
                                        matching_row = next((row for row in csv.DictReader(io.StringIO(decoded)) if row.get("レースコード") == target), {})
                                        entry["invalid_st_samples"] = [matching_row.get(f"艇{lane}_スタート展示") for lane in range(1, 7)] if matching_row.get("レースコード") == target else []

                    except (UnicodeError, csv.Error, ValueError):
                        entry["race_rows"] = "unreadable_csv"
                else:
                    entry["race_identity_status"] = "not_parsed"
                    entry.update(html_diagnostics(body))
        except (HTTPError, URLError, TimeoutError, OSError, ValueError) as exc:
            entry["error_type"] = type(exc).__name__
        report["sources"][name] = entry
    csv_r = report["sources"]["race_csv"].get("registration_numbers")
    official_r = report["sources"]["official_racelist"].get("registration_candidates")
    if csv_r is not None and official_r is not None and len(official_r) == 6 and len(csv_r) == 6:
        equal = csv_r == official_r
        report["registration_set_comparison"] = {
            "status": "equal_unverified" if equal else "mismatch_blocked",
            "same_set": equal, "lane_mapping_verified": False,
            "official_race_identity_verified": False,
        }
    else:
        report["registration_set_comparison"] = {"status": "not_comparable", "lane_mapping_verified": False}
    official_order = report["sources"]["official_racelist"].get("registration_order_candidates")
    csv_order = report["sources"]["race_csv"].get("registration_in_lane_order")
    if official_order is None or csv_order is None:
        status = "not_comparable"
    elif len(official_order) != 6:
        status = "ambiguous_official_order"
    else:
        status = "order_equal_unverified" if official_order == csv_order else "order_mismatch_blocked"
    report["registration_order_comparison"] = {"status": status, "lane_mapping_verified": False}
    html_lanes = report["sources"]["official_racelist"].get("lane_registration_candidates")
    csv_lanes = report["sources"]["race_csv"].get("registration_in_lane_order")
    if html_lanes and csv_lanes and len(csv_lanes) == 6:
        equal_lanes = all(html_lanes.get(i) == csv_lanes[i-1] for i in range(1,7))
        report["lane_comparison"] = {
            "status": "lane_equal_unverified" if equal_lanes else "lane_mismatch_blocked",
            "same_lane_registration": equal_lanes,
            "official_race_identity_verified": False,
        }
    else:
        report["lane_comparison"] = {"status": "not_comparable", "official_race_identity_verified": False}
    csv_entries = [report["sources"][k] for k in ("race_csv", "preview_stt", "preview_tkz", "preview_sui")]
    all_rows_valid = all(e.get("race_rows") == 1 and e.get("record_validation") == "schema_pass_unverified" for e in csv_entries)
    same_lane = report["lane_comparison"].get("same_lane_registration") is True
    report["readiness_gate"] = {
        "status": "blocked_no_official_previews",
        "csv_structure_pass": all_rows_valid,
        "official_lane_registrations_match": same_lane,
        "official_race_identity_verified": False,
        "official_preview_values_verified": False,
        "can_publish": False, "can_score_fresh": False,
    }
    preview = report["sources"]["official_beforeinfo"]
    before_candidates = preview.get("registration_candidates")
    list_candidates = report["sources"]["official_racelist"].get("registration_candidates")
    same_racers = (
        isinstance(before_candidates, list) and isinstance(list_candidates, list)
        and len(before_candidates) == 6 and len(list_candidates) == 6
        and before_candidates == list_candidates
    )
    official_values = preview.get("preview_value_candidates")
    csv_values = report["sources"]["preview_tkz"].get("tilt_time_by_lane")
    if official_values and csv_values:
        comparisons = []
        for lane in range(1,7):
            ref = official_values[lane]
            values = csv_values[lane]
            try:
                from decimal import Decimal, InvalidOperation
                same = Decimal(ref["time"]) == Decimal(values["展示タイム"]) and Decimal(ref["tilt"]) == Decimal(values["チルト"])
            except (InvalidOperation, TypeError, KeyError):
                same = False
            comparisons.append(same)
        report["preview_tilt_time_comparison"] = {
            "status": "values_equal_unverified" if all(comparisons) else "values_mismatch_blocked",
            "all_six_equal": all(comparisons), "official_race_identity_verified": False,
        }
    else:
        report["preview_tilt_time_comparison"] = {"status": "not_comparable", "official_race_identity_verified": False}
    official_st = preview.get("official_st_by_course")
    csv_st = report["sources"]["preview_stt"].get("course_st_by_boat")
    if official_st and csv_st:
        compare = []
        for boat in range(1, 7):
            course = csv_st[boat]["コース"]
            observed = csv_st[boat]["スタート展示"]
            expected = official_st.get(int(course)) if course and course.isdigit() else None
            from decimal import Decimal, InvalidOperation
            def normalize(value):
                if value is None:
                    return None
                f_flag = value.startswith("F") or value.startswith("-")
                numeric = value[1:] if f_flag else value
                try:
                    return (f_flag, Decimal(numeric))
                except InvalidOperation:
                    return None
            compare.append(expected is not None and observed is not None and normalize(expected) is not None and normalize(expected) == normalize(observed))
        mismatch_samples = [{"boat": boat, "course": csv_st[boat]["コース"], "csv_st": csv_st[boat]["スタート展示"], "official_st": official_st.get(int(csv_st[boat]["コース"]))} for boat in range(1,7)]
        report["official_st_comparison"] = {
            "samples": mismatch_samples,
            "status": "st_equal_unverified" if all(compare) else "st_mismatch_blocked",
            "all_six_equal": all(compare), "course_is_not_boat": True,
            "official_race_identity_verified": False,
        }
    else:
        report["official_st_comparison"] = {"status": "not_comparable", "official_race_identity_verified": False}
    report["official_preview_probe"] = {
        "status": preview.get("html_inspection", "unavailable"),
        "six_racer_sets_equal": same_racers,
        "values_compared": False,
        "official_race_identity_verified": False,
    }
    gate = report["readiness_gate"]
    gate["official_tilt_time_equal_unverified"] = (
        report["preview_tilt_time_comparison"].get("all_six_equal") is True
    )
    gate["official_exhibition_st_equal_unverified"] = (
        report["official_st_comparison"].get("all_six_equal") is True
    )
    gate["official_six_racer_sets_equal_unverified"] = (
        report["official_preview_probe"].get("six_racer_sets_equal") is True
    )
    gate["status"] = "blocked_unverified_official_race_identity_and_provenance"
    return report

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", required=True)
    parser.add_argument("--venue", required=True)
    parser.add_argument("--race", required=True)
    parser.add_argument("--output", default="source-probe-report.json")
    args = parser.parse_args()
    result = probe(args.date, args.venue, args.race)
    output = Path(args.output)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"race_key": result["race_key"], "registration_set_comparison": result["registration_set_comparison"], "registration_order_comparison": result["registration_order_comparison"], "lane_comparison": result["lane_comparison"], "readiness_gate": result["readiness_gate"], "official_preview_probe": result["official_preview_probe"], "preview_tilt_time_comparison": result["preview_tilt_time_comparison"], "official_st_comparison": result["official_st_comparison"], "sources": {k: {"status": v["status"], "race_rows": v.get("race_rows"), "race_identity_status": v.get("race_identity_status"), "csv_columns": v.get("csv_columns"), "csv_total_rows": v.get("csv_total_rows"), "csv_sample_race_codes": v.get("csv_sample_race_codes"), "record_validation": v.get("record_validation"), "validation_error": v.get("validation_error"), "invalid_st_samples": v.get("invalid_st_samples"), "html_inspection": v.get("html_inspection"), "html_title": v.get("html_title"), "racer_link_count": v.get("racer_link_count"), "toban_parameter_count": v.get("toban_parameter_count"), "registration_candidates": v.get("registration_candidates")} for k,v in result["sources"].items()}}, ensure_ascii=False))

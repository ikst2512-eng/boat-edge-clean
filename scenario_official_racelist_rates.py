"""Read-only six racer statistics from ORIGINAL official racelist HTML.

Shares #1713's existing racer ROW and registration parser. The national
win-rate column is distinguished by the original "全国 / 当地 / モーター /
ボート" table header, not by V2 CSV or a caller-supplied rate vector.
This parser does NOT fetch, time-stamp or certify any HTTP evidence, and
must only be used after the existing three-original auditor/replay checks.
"""
import hashlib
import math
import re
from html import unescape
from html.parser import HTMLParser

from scripts.inspect_official_racelist_registrations import (
    ROW, inspect_six_registrations,
)

HEADERS = re.compile(
    r"<th[^>]*>\s*全国\s*</th>\s*<th[^>]*>\s*当地\s*</th>"
    r"\s*<th[^>]*>\s*モーター\s*</th>\s*<th[^>]*>\s*ボート\s*</th>",
    re.S,
)
BOATS = set(range(1, 7))
ST = re.compile(r"^F\d+\s+L\d+\s+(0\.\d{1,2})$")
THREE = re.compile(r"^(\d{1,2}\.\d{1,2})\s+(\d{1,3}\.\d{1,2})\s+(\d{1,3}\.\d{1,2})$")

MOTOR = re.compile(r"^(\d{1,3})\s+(\d{1,3}\.\d{1,2})\s+(\d{1,3}\.\d{1,2})$")


class _CellText(HTMLParser):
    """Extract first-row TD cells, preserving line breaks as separators."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.cells = []
        self.active = None

    def handle_starttag(self, tag, attrs):
        if tag == "td":
            if self.active is not None:
                raise ValueError("nested_official_racer_td_invalid")
            self.active = {"attrs":dict(attrs), "chunks":[]}
        elif tag == "br" and self.active is not None:
            self.active["chunks"].append(" ")

    def handle_data(self, data):
        if self.active is not None:
            self.active["chunks"].append(data + " ")

    def handle_endtag(self, tag):
        if tag == "td":
            if self.active is None:
                raise ValueError("unmatched_official_racer_td")
            self.cells.append({
                "attrs": self.active["attrs"],
                "text": " ".join("".join(self.active["chunks"]).split()),
            })
            self.active = None


def extract_six_official_racelist_rates(raw):
    """No guessed rate for an unreadable boat, no dependence on confirmed results.

    Returns rows in boat-number order; each includes 6-lane registration, 6
    national/local stats and average start time. Because parsed official race
    data may be prior to exhibition, no T-12 eligibility is asserted.
    Official motor display rates alone do not reveal race counts, so never
    coerce them into denominator-validated #1710 scenario signals.
    """
    if type(raw) is not bytes or not 0 < len(raw) <= 1_500_000:
        raise ValueError("racelist_original_bytes_required")
    html = unescape(raw.decode("utf-8", "replace"))
    if len(HEADERS.findall(html)) != 1:
        raise ValueError("official_national_local_column_headers_ambiguous")
    registration_audit = inspect_six_registrations(raw)
    if registration_audit["six_racers_verified"] is not True:
        raise ValueError("official_six_registration_parser_incomplete")
    by_boat = {}
    for match in ROW.finditer(html):
        boat = int(match.group(1))
        if (boat not in BOATS or
                "１２３４５６".index(match.group(2))+1 != boat or
                boat in by_boat):
            raise ValueError("duplicated_or_misaligned_official_lanes")
        cells = _CellText()
        cells.feed("<tr>" + match.group("cells") + "</tr>")
        cells.close()
        # 0 photo, 1 registration/name, 2 F/L/avgST,
        # 3 nationwide win/2ren/3ren, 4 venue win/2ren/3ren.
        if len(cells.cells) < 7 or any(
            "is-lineH2" not in cells.cells[i]["attrs"].get("class","").split()
            for i in (2, 3, 4, 5)
        ):
            raise ValueError("official_racelist_stats_columns_drifted")
        st = ST.fullmatch(cells.cells[2]["text"])
        national = THREE.fullmatch(cells.cells[3]["text"])
        local = THREE.fullmatch(cells.cells[4]["text"])
        motor = MOTOR.fullmatch(cells.cells[5]["text"])
        if st is None or national is None or local is None or motor is None:
            raise ValueError("official_six_rates_or_average_st_missing")
        nation = [float(x) for x in national.groups()]
        venue = [float(x) for x in local.groups()]
        avg_st = float(st.group(1))
        motor_no = int(motor.group(1))
        motor_rates = [float(x) for x in motor.groups()[1:]]
        if (not 1 <= motor_no <= 999
                or not all(math.isfinite(v) and 0 <= v <= 100 for v in motor_rates)
                or not 0 <= avg_st < 1
                or not all(0 < values[0] <= 10 and
                           all(0 <= pct <= 100 for pct in values[1:])
                           for values in (nation, venue))):
            raise ValueError("official_rate_or_start_out_of_bounds")
        by_boat[boat] = {
            "boat":boat,
            "registration_id":registration_audit["registrations_by_lane"][str(boat)],
            "national_win_rate":nation[0],
            "national_2ren_pct":nation[1],
            "national_3ren_pct":nation[2],
            "local_win_rate":venue[0],
            "local_2ren_pct":venue[1],
            "local_3ren_pct":venue[2],
            "average_st_s":avg_st,
            "motor_number":motor_no,
            "motor_2ren_pct":motor_rates[0],
            "motor_3ren_pct":motor_rates[1],
            # Display percentages have no verified starts/success counts.
            "motor_starts":None,
            "motor_2ren_count":None,
        }
    if set(by_boat) != BOATS:
        raise ValueError("official_six_rates_incomplete")
    rows = [by_boat[i] for i in sorted(BOATS)]
    if len(set(row["registration_id"] for row in rows)) != 6:
        raise ValueError("official_racelist_duplicate_registration")
    return {
        "source": "source_bytes_of_unattested_official_racelist",
        "rates_extracted_from_original_html_not_csv": True,
        "boats": rows,
        "national_rates": [row["national_win_rate"] for row in rows],
        "average_st": [row["average_st_s"] for row in rows],
        "motor_numbers": [row["motor_number"] for row in rows],
        "motor_2ren_pct": [row["motor_2ren_pct"] for row in rows],
        "motor_2ren_sample_size_verified": False,
        "racelist_original_bytes_sha256": hashlib.sha256(raw).hexdigest(),
        "local_rates": [row["local_win_rate"] for row in rows],
        "official_HTTP_origin_attested": False,
        "official_T_minus_12_source_certified": False,
        "forecast_usable": False,
        "formal": False,
    }

"""Exploratory original-HTML racelist intake that preserves genuine local 0.00.

The preregistered #1710 parser source is immutable. This separate NON-FORMAL
adapter reuses its same frozen row/header/stat grammar, and ONLY relaxes the
venue (当地) win rate from >0 to >=0. Nationwide ability inputs stay >0.
It neither guesses missing values nor permits a saved/preregistered candidate.
"""
import math

from scripts.inspect_official_racelist_registrations import (
    inspect_six_registrations,
)
from scenario_official_racelist_rates import (
    HEADERS, ROW, ST, THREE, _CellText,
    extract_six_official_racelist_rates,
)
from html import unescape

STUDY_ID = "EXPLORATORY_ONLY_OFFICIAL_LOCAL_ZERO_INTAKE_V1"
BOATS = set(range(1, 7))


def extract_six_with_local_zero_research(raw):
    """Parse original six-boat HTML; never rewrite input bytes or fill zeros."""
    try:
        original = extract_six_official_racelist_rates(raw)
    except ValueError as original_exc:
        # We may only research a strict bounds rejection, never bypass the
        # frozen source's registration, column, or text-shape validation.
        if str(original_exc) != "official_rate_or_start_out_of_bounds":
            raise
    else:
        return dict(original, study_id=STUDY_ID,
                    local_zero_research_fallback_used=False,
                    local_zero_boats=[], method_preregistered=False,
                    model_consumed=False)

    if type(raw) is not bytes or not 0 < len(raw) <= 1_500_000:
        raise ValueError("local_zero_research_original_bytes_invalid")
    html = unescape(raw.decode("utf-8", "replace"))
    if len(HEADERS.findall(html)) != 1:
        raise ValueError("local_zero_research_column_headers_invalid")
    reg = inspect_six_registrations(raw)
    if reg["six_racers_verified"] is not True:
        raise ValueError("local_zero_research_six_registration_invalid")
    parsed = {}
    for match in ROW.finditer(html):
        boat = int(match.group(1))
        if (boat not in BOATS or boat in parsed or
                "１２３４５６".index(match.group(2)) + 1 != boat):
            raise ValueError("local_zero_research_boat_identity_invalid")
        cells = _CellText()
        cells.feed("<tr>" + match.group("cells") + "</tr>")
        cells.close()
        if (len(cells.cells) < 7 or any(
                "is-lineH2" not in cells.cells[i]["attrs"].get(
                    "class", "").split() for i in (2, 3, 4))):
            raise ValueError("local_zero_research_columns_drifted")
        st = ST.fullmatch(cells.cells[2]["text"])
        national = THREE.fullmatch(cells.cells[3]["text"])
        local = THREE.fullmatch(cells.cells[4]["text"])
        if st is None or national is None or local is None:
            raise ValueError("local_zero_research_numeric_text_invalid")
        n = [float(x) for x in national.groups()]
        v = [float(x) for x in local.groups()]
        avg = float(st.group(1))
        if (not 0 <= avg < 1 or not 0 < n[0] <= 10
                or not 0 <= v[0] <= 10
                or any(not 0 <= rate <= 100 for rate in n[1:] + v[1:])
                or any(not math.isfinite(x) for x in n + v + [avg])):
            raise ValueError("local_zero_research_genuine_rate_out_of_bounds")
        parsed[boat] = {
            "boat": boat,
            "registration_id": reg["registrations_by_lane"][str(boat)],
            "national_win_rate": n[0],
            "national_2ren_pct": n[1],
            "national_3ren_pct": n[2],
            "local_win_rate": v[0],
            "local_2ren_pct": v[1],
            "local_3ren_pct": v[2],
            "average_st_s": avg,
        }
    if set(parsed) != BOATS:
        raise ValueError("local_zero_research_six_boat_rates_missing")
    rows = [parsed[i] for i in range(1, 7)]
    zeros = [r["boat"] for r in rows if r["local_win_rate"] == 0]
    if not zeros or len(set(r["registration_id"] for r in rows)) != 6:
        raise ValueError("local_zero_research_wrong_fallback_or_registrations")
    return {
        "source": "source_bytes_of_unattested_official_racelist",
        "rates_extracted_from_original_html_not_csv": True,
        "boats": rows,
        "national_rates": [r["national_win_rate"] for r in rows],
        "average_st": [r["average_st_s"] for r in rows],
        "local_rates": [r["local_win_rate"] for r in rows],
        "study_id": STUDY_ID,
        "local_zero_research_fallback_used": True,
        "local_zero_boats": zeros,
        "method_preregistered": False,
        "model_consumed": False,
        "official_HTTP_origin_attested": False,
        "official_T_minus_12_source_certified": False,
        "forecast_usable": False,
        "formal": False,
    }

"""Distinct F-aware research rate adapter. Never modify pinned #1710 parser.

Reuse the existing original official row/header/cell recognizers unchanged.
An official LOCAL 0.00 is a valid recorded value (it is NOT a missing
numeric and does NOT imply a known race-count denominator). Only six positive
NATIONAL win rates are required by the first-head probability model.
No source fetch, result read, backfill, publication or model output.
"""
import math
from html import unescape

from scripts.inspect_official_racelist_registrations import inspect_six_registrations
from scenario_official_racelist_rates import HEADERS, ROW, ST, THREE, _CellText


def parse_signed_st_study_racelist_rates(raw):
    if type(raw) is not bytes or not 0<len(raw)<=1_500_000:
        raise ValueError("signed_st_racelist_original_bytes_required")
    html=unescape(raw.decode("utf-8","replace"))
    if len(HEADERS.findall(html))!=1:
        raise ValueError("signed_st_racelist_headers_missing_or_ambiguous")
    ids=inspect_six_registrations(raw)
    if ids["six_racers_verified"] is not True:
        raise ValueError("signed_st_racelist_registration_roster_invalid")
    by_boat={}
    for m in ROW.finditer(html):
        boat=int(m.group(1))
        if (boat not in range(1,7) or boat in by_boat
                or "１２３４５６".index(m.group(2))+1!=boat):
            raise ValueError("signed_st_racelist_row_identity_or_duplicate")
        c=_CellText()
        c.feed("<tr>"+m.group("cells")+"</tr>")
        c.close()
        if (len(c.cells)<7 or any(
            "is-lineH2" not in c.cells[i]["attrs"].get("class","").split()
            for i in (2,3,4))):
            raise ValueError("signed_st_racelist_columns_drifted")
        st=ST.fullmatch(c.cells[2]["text"])
        n=THREE.fullmatch(c.cells[3]["text"])
        l=THREE.fullmatch(c.cells[4]["text"])
        if st is None or n is None or l is None:
            raise ValueError("signed_st_racelist_stats_unparseable")
        nation=[float(x) for x in n.groups()]
        venue=[float(x) for x in l.groups()]
        avg=float(st.group(1))
        if (not math.isfinite(avg) or not 0<=avg<1
                or any(not math.isfinite(x) for x in nation+venue)
                or not 0<nation[0]<=10
                or not 0<=venue[0]<=10
                or not all(0<=x<=100 for x in nation[1:]+venue[1:])):
            raise ValueError("signed_st_racelist_true_statistic_out_of_bounds")
        by_boat[boat]={
            "boat":boat,
            "registration_id":ids["registrations_by_lane"][str(boat)],
            "national_win_rate":nation[0],
            "local_win_rate":venue[0],
            "average_st_s":avg,
            "zero_local_win_rate_reported":venue[0]==0.0,
            "local_race_count_known":False,
        }
    if set(by_boat)!=set(range(1,7)):
        raise ValueError("signed_st_racelist_missing_six_boats")
    result=[by_boat[i] for i in range(1,7)]
    if len({r["registration_id"] for r in result})!=6:
        raise ValueError("signed_st_racelist_registration_duplicates")
    return {
        "schema":"SIGNED_ST_SIX_OFFICIAL_RACELIST_RATES_V1",
        "boats":result,
        "national_rates":[r["national_win_rate"] for r in result],
        "average_st":[r["average_st_s"] for r in result],
        "local_rates":[r["local_win_rate"] for r in result],
        "zero_local_rate_boats":[r["boat"] for r in result
                                 if r["zero_local_win_rate_reported"]],
        "local_race_count_not_claimed":True,
        "uses_frozen_official_original_row_recognizer":True,
        "numeric_values_filled_by_guess":False,
        "outcome_read":False,"formal":False,"forecast_usable":False,
    }

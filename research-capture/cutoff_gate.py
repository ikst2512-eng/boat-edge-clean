"""Fail-closed cutoff gate for research capture. No result data is read."""
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import re
JST=ZoneInfo("Asia/Tokyo")

def validate_window(race_id, deadline_jst, observed_utc, minimum_seconds=720, maximum_seconds=1200):
    if not re.fullmatch(r"20\d{6}(?:0[1-9]|1\d|2[0-4])(?:0[1-9]|1[0-2])",race_id):
        return False,"INVALID_RACE_ID"
    if deadline_jst.tzinfo is None or observed_utc.tzinfo is None:
        return False,"NAIVE_TIMESTAMP"
    local=deadline_jst.astimezone(JST)
    if local.strftime("%Y%m%d") != race_id[:8]:
        return False,"DATE_MISMATCH"
    if deadline_jst.utcoffset() != timedelta(hours=9):
        return False,"CUTOFF_NOT_JST"
    remaining=(deadline_jst-observed_utc).total_seconds()
    if remaining > maximum_seconds:return False,"TOO_EARLY"
    if remaining <= minimum_seconds:return False,"TOO_LATE"
    return True,"WINDOW_OK"

if __name__=="__main__":
    d=datetime(2026,10,25,16,6,tzinfo=JST)
    tests=[
       (datetime(2026,10,25,15,45,tzinfo=JST),False,"TOO_EARLY"),
       (datetime(2026,10,25,15,46,1,tzinfo=JST),True,"WINDOW_OK"),
       (datetime(2026,10,25,15,53,59,tzinfo=JST),True,"WINDOW_OK"),
       (datetime(2026,10,25,15,54,tzinfo=JST),False,"TOO_LATE"),
       (datetime(2026,10,25,16,7,tzinfo=JST),False,"TOO_LATE")
    ]
    for instant, expected, label in tests:
        valid,reason=validate_window("202610250512",d,instant)
        assert (valid,reason)==(expected,label),(valid,reason,expected,label)
    assert validate_window("202610260512",d,tests[1][0])[1]=="DATE_MISMATCH"
    print("CUTOFF_GATE_TESTS_PASS 6/6; no network, no results, no prediction")

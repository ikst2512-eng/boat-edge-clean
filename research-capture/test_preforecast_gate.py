"""Offline safety regression; no race endpoints or result values."""
import sys
from pathlib import Path
from datetime import datetime,timedelta,timezone
sys.path.insert(0,str(Path(__file__).resolve().parent))
from preforecast_gate import evaluate
jst=timezone(timedelta(hours=9))
cutoff=datetime(2026,10,25,18,0,tzinfo=jst)
at=cutoff-timedelta(minutes=15)
base={"html_bytes":"<html>展示<div class='is-boatColor1'></div></html>".encode(),"race_id":"202610250512","cutoff_jst":cutoff,"received_at":at,"content_type":"text/html","source_url":"https://www.boatrace.jp/owpc/pc/race/beforeinfo?jcd=05&hd=20261025&rno=12"}
cases=[
 ("incomplete",{}, "incomplete_six_lane_exhibition"),
 ("too_early",{"received_at":cutoff-timedelta(minutes=30)},"outside_predeadline_window"),
 ("too_late",{"received_at":cutoff-timedelta(minutes=11)},"outside_predeadline_window"),
 ("wrong_day",{"race_id":"202610260512"},"race_day_mismatch"),
 ("results",{"html_bytes":"払戻金 展示".encode()},"result_related_content"),
 ("wrong_endpoint",{"source_url":"https://www.boatrace.jp/owpc/pc/race/raceresult"},"source_not_beforeinfo"),
 ("bad_race",{"race_id":"X"},"race_id_invalid"),
 ("bad_content_type",{"content_type":"application/json"},"not_html"),
 ("no_timezone",{"received_at":at.replace(tzinfo=None)},"timezone_missing"),
 ("unknown_charset",{"html_bytes":bytes([255])},"charset_unverified")
]
for name,changes,want in cases:
    sample=base|changes
    actual=evaluate(**sample)
    assert actual["accepted"] is False and actual["reason"]==want and actual["scoring"]=="NOT_RUN", (name,actual)
    print("PASS",name)
print("10/10 SAFETY_GATES_PASS; forecast=0; scoring=NOT_RUN")

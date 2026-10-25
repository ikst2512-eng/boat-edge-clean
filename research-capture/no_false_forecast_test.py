"""Offline regression: prove that the research extractor never authorizes a late or outcome-bearing page."""
from datetime import datetime,timezone,timedelta
from safe_exhibition_extract import inspect
JST=timezone(timedelta(hours=9))
deadline=datetime(2026,10,25,16,6,tzinfo=JST)
cases=[
 ("late",b"<table><tr><td>1</td></tr></table>",datetime(2026,10,25,17,39,tzinfo=JST),"TOO_LATE"),
 ("outcomes","<table>払戻金</table>".encode(),datetime(2026,10,25,15,50,tzinfo=JST),"RESULT_TOKEN_QUARANTINE"),
 ("missing_mapping",b"<table><tr><td>1</td></tr></table>",datetime(2026,10,25,15,50,tzinfo=JST),"SIX_LANE_MAPPING_NOT_CERTIFIED")
]
for name,raw,when,expected in cases:
  actual=inspect(raw,"202610250512",deadline,when)
  assert actual["gate_reason"]==expected,(name,actual)
  assert actual["forecast_allowed"] is False,name
print("RESEARCH_NO_FALSE_FORECAST_PASS 3/3")

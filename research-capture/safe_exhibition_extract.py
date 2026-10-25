"""Fail-closed six-lane exhibition extraction from official beforeinfo HTML.
Does not read outcome endpoints or produce a forecast.
"""
from html.parser import HTMLParser
from datetime import datetime
import hashlib,re
from cutoff_gate import validate_window

class Tables(HTMLParser):
    def __init__(self):
        super().__init__();self.tables=[];self.table=None;self.row=None;self.cell=None
    def handle_starttag(self,t,a):
        if t=="table":self.table=[]
        elif t=="tr" and self.table is not None:self.row=[]
        elif t in ("td","th") and self.row is not None:self.cell=[]
    def handle_data(self,s):
        if self.cell is not None:self.cell.append(s)
    def handle_endtag(self,t):
        if t in ("td","th") and self.cell is not None and self.row is not None:
            self.row.append(" ".join("".join(self.cell).split()));self.cell=None
        elif t=="tr" and self.row is not None and self.table is not None:
            self.table.append(self.row);self.row=None
        elif t=="table" and self.table is not None:
            self.tables.append(self.table);self.table=None

def inspect(raw,race_id,cutoff_jst,observed_utc):
    valid,reason=validate_window(race_id,cutoff_jst,observed_utc)
    report={"race_id":race_id,"window_ok":valid,"gate_reason":reason,"source_sha256":hashlib.sha256(raw).hexdigest(),"forecast_allowed":False,"scoring":"NOT_RUN"}
    if not valid:return report
    page=raw.decode("utf-8","replace")
    if re.search("払戻金|確定結果|着順結果",page):
        report["gate_reason"]="RESULT_TOKEN_QUARANTINE"
        return report
    p=Tables();p.feed(page)
    report["table_count"]=len(p.tables)
    # Verify only structure. Numeric extraction is withheld until six unambiguous
    # boat identities, entry courses and exhibition fields map to the same race.
    report["row_lengths"]=[[len(r) for r in table] for table in p.tables]
    report["gate_reason"]="SIX_LANE_MAPPING_NOT_CERTIFIED"
    return report

if __name__=="__main__":
    from datetime import timezone,timedelta
    j=timezone(timedelta(hours=9));cut=datetime(2026,10,25,16,6,tzinfo=j)
    ok=inspect(b"<table><tr><td>1</td></tr></table>","202610250512",cut,datetime(2026,10,25,15,50,tzinfo=j))
    assert ok["gate_reason"]=="SIX_LANE_MAPPING_NOT_CERTIFIED" and ok["table_count"]==1
    late=inspect(b"<table></table>","202610250512",cut,datetime(2026,10,25,15,55,tzinfo=j))
    assert late["gate_reason"]=="TOO_LATE"
    quarantine=inspect("払戻金".encode(),"202610250512",cut,datetime(2026,10,25,15,50,tzinfo=j))
    assert quarantine["gate_reason"]=="RESULT_TOKEN_QUARANTINE"
    print("SAFE_EXTRACTION_GATES_PASS 3/3")

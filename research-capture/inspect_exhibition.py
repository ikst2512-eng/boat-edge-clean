"""Fail-closed parsing of official pre-race exhibition HTML; not a forecast engine."""
from html.parser import HTMLParser
import json,re,sys,hashlib

class Tables(HTMLParser):
    def __init__(self):
        super().__init__();self.tables=[];self.current=None;self.row=None;self.cell=None;self.depth=0
    def handle_starttag(self,tag,attrs):
        if tag=="table":
            if self.depth==0:self.current=[]
            self.depth+=1
        elif tag=="tr" and self.depth==1:self.row=[]
        elif tag in ("td","th") and self.depth==1 and self.row is not None:self.cell=[]
    def handle_data(self,data):
        if self.cell is not None:self.cell.append(data)
    def handle_endtag(self,tag):
        if tag in ("td","th") and self.cell is not None:
            self.row.append(" ".join("".join(self.cell).split()));self.cell=None
        elif tag=="tr" and self.row is not None:
            self.current.append(self.row);self.row=None
        elif tag=="table" and self.depth:
            self.depth-=1
            if self.depth==0:self.tables.append(self.current);self.current=None

def inspect(raw):
    page=raw.decode("utf-8","replace")
    t=Tables();t.feed(page)
    headers=[row for table in t.tables for row in table if any("展示" in cell or "進入" in cell for cell in row)]
    # Do not infer numeric values from arbitrary HTML cells. A verified six-boat schema is mandatory.
    return {"source_sha256":hashlib.sha256(raw).hexdigest(),"table_count":len(t.tables),
            "rows":sum(len(x) for x in t.tables),"exhibition_header_rows":len(headers),
            "six_boat_exhibition_verified":False,"accepted_as_model_input":False,
            "forecast_generated":False,"scoring":"NOT_RUN"}
if __name__=="__main__":
    if len(sys.argv)!=2:raise SystemExit("usage: inspect_exhibition.py PATH")
    with open(sys.argv[1],"rb") as f:report=inspect(f.read())
    print(json.dumps(report,ensure_ascii=False,indent=2))

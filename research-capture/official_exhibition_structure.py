"""Fail-closed structural parser for official BOAT RACE beforeinfo.
This module does not read results endpoints and never emits a forecast.
"""
import datetime as dt
import hashlib
import json
import re
import urllib.request
from html.parser import HTMLParser

class TableScanner(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_table = 0
        self.in_cell = 0
        self.current = []
        self.rows = []
        self.cell_text = []
        self.colors = set()
        self.row_count = 0
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "table":
            self.in_table += 1
        if self.in_table and tag == "tr":
            self.current = []
            self.row_count += 1
        if self.in_table and tag in ("td", "th"):
            self.in_cell += 1
            self.cell_text = []
        for cls in a.get("class", "").split():
            m = re.fullmatch(r"is-boatColor([1-6])", cls)
            if m:
                self.colors.add(int(m.group(1)))
    def handle_data(self, text):
        if self.in_cell:
            self.cell_text.append(text)
    def handle_endtag(self, tag):
        if tag in ("td","th") and self.in_cell:
            text = re.sub(r"\s+", " ", "".join(self.cell_text)).strip()
            self.current.append(text)
            self.in_cell -= 1
        if tag == "tr" and self.in_table:
            if self.current:
                self.rows.append(self.current)
        if tag == "table" and self.in_table:
            self.in_table -= 1

def inspect(raw, charset="utf-8"):
    text = raw.decode(charset, "replace")
    doc = TableScanner()
    doc.feed(text)
    labels = ("展示タイム", "展示ST", "スタート展示", "進入")
    # Summary contains no athlete identity, finish order, payouts or raw page.
    return {
        "source_sha256": hashlib.sha256(raw).hexdigest(),
        "bytes": len(raw),
        "tables": len(re.findall(r"<table(?:\\s|>)", text, re.I)),
        "rows": doc.row_count,
        "boat_colors": sorted(doc.colors),
        "label_counts": {x: text.count(x) for x in labels},
        "numeric_cell_count": sum(bool(re.fullmatch(r"\\d+(?:\\.\\d+)?", cell)) for row in doc.rows for cell in row),
        "result_related_token": bool(re.search("払戻金|確定結果|着順結果", text)),
        "candidate_six_boat_structure": len(doc.colors) == 6,
        "exhibition_values_verified": False,
        "safe_for_prediction": False,
        "scoring": "NOT_RUN"
    }

if __name__ == "__main__":
    now=dt.datetime.now(dt.timezone(dt.timedelta(hours=9)))
    date=now.strftime("%Y%m%d")
    url=f"https://www.boatrace.jp/owpc/pc/race/beforeinfo?jcd=05&hd={date}&rno=12"
    out={"at_jst":now.isoformat(),"venue":"05","race_no":12,"day":date,"results_endpoint_requested":False}
    try:
        with urllib.request.urlopen(urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0"}),timeout=15) as response:
            raw=response.read(200001)
            out.update(inspect(raw,response.headers.get_content_charset() or "utf-8"))
            out["http_status"]=response.status
    except Exception as ex:
        out.update({"error_type":type(ex).__name__,"safe_for_prediction":False})
    print(json.dumps(out,ensure_ascii=False,indent=2))

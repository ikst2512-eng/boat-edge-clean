"""Non-sensitive structural probe for official beforeinfo tables.

No numeric race values are emitted or persisted. No forecast or result access.
"""
import hashlib
import json
import re
from html.parser import HTMLParser

class TableShape(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tables=[]; self.table=None; self.row=None; self.cell=None
        self.row_classes=[]; self.cell_classes=[]
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag=="table" and self.table is None: self.table=[]
        elif tag=="tr" and self.table is not None:
            self.row=[]; self.row_classes=a.get("class","").split()
        elif tag in ("td","th") and self.row is not None:
            self.cell={"text":[],"classes":a.get("class","").split(),"tag":tag}
    def handle_data(self,data):
        if self.cell is not None:self.cell["text"].append(data)
    def handle_endtag(self,tag):
        if tag in ("td","th") and self.cell is not None and self.row is not None:
            s=re.sub(r"\s+"," ","".join(self.cell["text"])).strip()
            self.row.append({"numeric":bool(re.fullmatch(r"(?:\d{1,3}(?:\.\d{1,3})?)",s)),
                             "labels":[v for v in ("展示","進入","ST","モーター","コース") if v in s],
                             "lane_classes":[i for i in range(1,7) if any(re.search(r"(?:boatColor|is-boatColor|is-boatcolor)"+str(i)+r"\b",c) for c in self.cell["classes"])],
                             "tag":self.cell["tag"]})
            self.cell=None
        elif tag=="tr" and self.row is not None and self.table is not None:
            self.table.append({"cells":self.row,"row_lanes":[i for i in range(1,7) if any(re.search(r"(?:boatColor|is-boatColor|is-boatcolor)"+str(i)+r"\b",c) for c in self.row_classes)]})
            self.row=None
        elif tag=="table" and self.table is not None:
            self.tables.append(self.table);self.table=None

def inspect(raw):
    text=raw.decode("utf-8","replace")
    p=TableShape();p.feed(text)
    groups=[]
    for ti,table in enumerate(p.tables):
        for ri,row in enumerate(table):
            cells=row["cells"]
            label_set=sorted(set(x for c in cells for x in c["labels"]))
            numeric=sum(c["numeric"] for c in cells)
            if label_set or numeric>=4:
                groups.append({"table":ti,"row":ri,"cells":len(cells),"numeric_cells":numeric,
                               "labels":label_set,"row_lanes":row["row_lanes"],
                               "cell_lane_markers":sorted(set(i for c in cells for i in c["lane_classes"]))})
    return {"sha256":hashlib.sha256(raw).hexdigest(),"tables":len(p.tables),
            "row_shapes":groups[:120],"candidate_count":len(groups),
            "result_related_token":bool(re.search(r"払戻金|確定結果|着順結果",text)),
            "official_six_values_verified":False,"forecast_allowed":False,"scoring":"NOT_RUN"}

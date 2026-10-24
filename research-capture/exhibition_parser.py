"""Fail-closed six-lane exhibition parser, without any results/scoring access."""
from html.parser import HTMLParser
import re, json, sys, pathlib

class Tables(HTMLParser):
    def __init__(self):
        super().__init__(); self.depth=0; self.rows=[]; self.row=None; self.cell=None; self.tables=[]
    def handle_starttag(self,tag,attrs):
        if tag=="table":
            self.depth+=1
            if self.depth==1:self.rows=[]
        if self.depth and tag=="tr":self.row=[]
        if self.depth and tag in ("th","td"):self.cell=[]
    def handle_data(self,data):
        if self.cell is not None:self.cell.append(data)
    def handle_endtag(self,tag):
        if tag in ("th","td") and self.cell is not None:
            if self.row is not None:self.row.append(" ".join("".join(self.cell).split()))
            self.cell=None
        if tag=="tr" and self.row is not None:
            if any(self.row):self.rows.append(self.row)
            self.row=None
        if tag=="table" and self.depth:
            self.depth-=1
            if self.depth==0:self.tables.append(self.rows)

def extract(raw, *, race_id, received_before_cutoff, result_free_attested):
    assert re.fullmatch(r"20\d{6}(?:0[1-9]|1\d|2[0-4])(?:0[1-9]|1[0-2])",race_id)
    if not received_before_cutoff or not result_free_attested:
        raise ValueError("receipt or result-isolation gate missing")
    html=raw.decode("utf-8","replace")
    if re.search(r"払戻金|確定結果|着順結果",html):
        raise ValueError("result-bearing token: refuse entire page")
    p=Tables();p.feed(html)
    # Only headings explicitly defining official exhibition time permit six numeric rows.
    candidates=[]
    for table in p.tables:
        head=" ".join(" ".join(row) for row in table[:3])
        if "展示" not in head or "タイム" not in head:continue
        boat_rows=[]
        for row in table:
            if not row or row[0] not in ["1","2","3","4","5","6"]:continue
            nums=[v for v in row[1:] if re.fullmatch(r"6\.\d{2}",v)]
            if len(nums)!=1:continue
            boat_rows.append((int(row[0]),float(nums[0])))
        if len(boat_rows)==6 and set(k for k,_ in boat_rows)==set(range(1,7)):
            candidates.append(sorted(boat_rows))
    if len(candidates)!=1:raise ValueError(f"EXHIBITION_NOT_PROVEN: {len(candidates)} candidate tables")
    return {"race_id":race_id,"exhibition_time_by_boat":dict(candidates[0]),"no_results":True}

def selftest():
    body=b'<table><tr><th>\xe5\xb1\x95\xe7\xa4\xba\xe3\x82\xbf\xe3\x82\xa4\xe3\x83\xa0</th></tr>'+b"".join(f"<tr><td>{i}</td><td>{6.7+i/100:.2f}</td></tr>".encode() for i in range(1,7))+b"</table>"
    got=extract(body,race_id="202610250512",received_before_cutoff=True,result_free_attested=True)
    assert len(got["exhibition_time_by_boat"])==6
    for bad in (False,None):
        try:extract(body,race_id="202610250512",received_before_cutoff=bool(bad),result_free_attested=True)
        except ValueError:pass
        else:raise AssertionError("must block missing time proof")
    try:extract(body+b"\xe6\x89\x95\xe6\x88\xbb\xe9\x87\x91",race_id="202610250512",received_before_cutoff=True,result_free_attested=True)
    except ValueError:pass
    else:raise AssertionError("must reject result-bearing HTML")
    print("PARSER_SELFTEST_PASS; no external results accessed")

if __name__=="__main__":selftest()

"""Extract possible six-lane exhibition rows from official beforeinfo HTML.

Research-only. Never reads results endpoints, never creates forecasts.
An extracted candidate is NOT a verified official exhibition record.
"""
import hashlib
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

class Tables(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tables = []
        self.table = None
        self.row = None
        self.cell = None
    def handle_starttag(self, tag, attrs):
        if tag == "table" and self.table is None:
            self.table = []
        elif self.table is not None and tag == "tr":
            self.row = []
        elif self.row is not None and tag in ("td", "th"):
            self.cell = []
    def handle_data(self, data):
        if self.cell is not None:
            self.cell.append(data)
    def handle_endtag(self, tag):
        if tag in ("td", "th") and self.cell is not None and self.row is not None:
            self.row.append(re.sub(r"\s+", " ", "".join(self.cell)).strip())
            self.cell = None
        elif tag == "tr" and self.row is not None and self.table is not None:
            self.table.append(self.row)
            self.row = None
        elif tag == "table" and self.table is not None:
            self.tables.append(self.table)
            self.table = None

def inspect(raw: bytes, *, cutoff_verified=False):
    # Evaluate only a purpose-bound pre-result input. Generic result tokens
    # conservatively block publication, including boilerplate false positives.
    text = raw.decode("utf-8", "replace")
    p = Tables()
    p.feed(text)
    unsafe = bool(re.search(r"払戻金|確定結果|着順結果", text))
    entries = []
    for ti, table in enumerate(p.tables):
        for ri, row in enumerate(table):
            cells = [c.strip() for c in row]
            if not any("展示" in c or "ST" in c or "進入" in c for c in cells):
                continue
            numeric = [c for c in cells if re.fullmatch(r"(?:[1-6]|[0-9]{1,2}\.[0-9]{1,2})", c)]
            entries.append({"table_index":ti, "row_index":ri, "cell_count":len(cells), "numeric_candidates":len(numeric)})
    return {
        "raw_sha256": hashlib.sha256(raw).hexdigest(),
        "tables": len(p.tables),
        "candidate_rows": entries,
        "six_official_values_verified": False,
        "official_cutoff_verified": bool(cutoff_verified),
        "result_related_token": unsafe,
        "forecast_allowed": False,
        "scoring": "NOT_RUN",
        "reason": "Candidate-only metadata; six racer values and independent deadline not verified",
    }

if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: python3 exhibition_six_lane.py local-beforeinfo.html")
    print(json.dumps(inspect(Path(sys.argv[1]).read_bytes()), ensure_ascii=False, indent=2))

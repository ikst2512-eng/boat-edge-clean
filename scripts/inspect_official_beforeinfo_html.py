"""Diagnostic-only token inventory from preserved official beforeinfo HTML.

No six-boat, race identity, pre-deadline, or forecast eligibility inference.
"""
from html.parser import HTMLParser
from pathlib import Path
import argparse
import hashlib
import json
import re

LABELS=("展示タイム","チルト","スタート展示","進入","ST","風向","風速","波高")
# ST is a short abbreviation. A substring match also mistakes TEST, LAST,
# STATS and HTML diagnostic prose for actual start-timing label evidence.
ST_LABEL=re.compile(r"(?<![A-Za-z])ST(?![A-Za-z])")
def matches_label(label, text):
    return bool(ST_LABEL.search(text)) if label=="ST" else label in text
# Inert HTML must never be mistaken for six-lane evidence. The inventory is
# diagnostic only and intentionally does not certify publication or completeness.
INERT_TAGS=frozenset(("script","style","template","noscript","head","svg","iframe"))
class VisibleText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.fragments=[]
        self.inert_stack=[]
        self.table_rows=[]
        self.current_row=None
    def handle_starttag(self,tag,attrs):
        if tag=="tr" and not self.inert_stack:
            self.current_row=[]
        if tag in INERT_TAGS:
            self.inert_stack.append(tag)
    def handle_endtag(self,tag):
        if tag=="tr" and not self.inert_stack and self.current_row is not None:
            if self.current_row:self.table_rows.append(self.current_row)
            self.current_row=None
        if tag in INERT_TAGS and self.inert_stack and self.inert_stack[-1]==tag:
            self.inert_stack.pop()
    def handle_data(self,data):
        if not self.inert_stack:
            t=" ".join(data.split())
            if t:
                self.fragments.append(t)
                if self.current_row is not None:self.current_row.append(t)

def inspect(saved_dir):
    base=Path(saved_dir)
    manifest=json.loads((base/"manifest.json").read_text(encoding="utf-8"))
    raw=(base/"beforeinfo.html").read_bytes()
    if hashlib.sha256(raw).hexdigest()!=manifest.get("sha256"):
        raise ValueError("original HTML SHA mismatch")
    if manifest.get("race_code")!=base.name or base.parent.name!=base.name[:8]:
        raise ValueError("official probe race identity does not match evidence path")
    if manifest.get("bytes") is not None and manifest["bytes"]!=len(raw):
        raise ValueError("official probe byte length mismatch")
    if manifest.get("source")!="official_beforeinfo_html" or manifest.get("forecast_usable") is not False:
        raise ValueError("not isolated official probe evidence")
    # Refuse incomplete or fabricated capture metadata even when raw bytes hash-match.
    from datetime import datetime, timedelta
    timestamp=manifest.get("received_at_jst")
    try:
        receipt=datetime.fromisoformat(timestamp)
    except (TypeError, ValueError):
        raise ValueError("official probe receipt timestamp missing or invalid") from None
    try:
        started=datetime.fromisoformat(manifest["request_started_at_jst"])
    except (KeyError, TypeError, ValueError):
        raise ValueError("official request start timestamp missing or invalid") from None
    if started.utcoffset()!=timedelta(hours=9) or started>receipt:
        raise ValueError("official HTTP observation chronology unverified")
    if receipt.utcoffset()!=timedelta(hours=9) or manifest.get("http_status")!=200 or manifest.get("status")!="raw_http_observed_not_t12_certified":
        raise ValueError("official probe receipt metadata unverified")
    if manifest.get("t12_eligible") is not False or manifest.get("complete_six_lanes")!="unverified":
        raise ValueError("official probe must remain non-certified")
    from urllib.parse import urlparse, parse_qs
    day, venue, race=base.name[:8],int(base.name[8:10]),int(base.name[10:])
    expected={"hd":[day],"jcd":[f"{venue:02d}"],"rno":[str(race)]}
    for field in ("url","response_url"):
        value=manifest.get(field)
        if not isinstance(value,str):
            raise ValueError("official probe source URL missing")
        parsed=urlparse(value)
        if (parsed.scheme!="https" or parsed.hostname not in ("www.boatrace.jp","boatrace.jp")
                or parsed.path!="/owsp/sp/race/beforeinfo"
                or parse_qs(parsed.query)!=expected):
            raise ValueError("official probe source URL race identity mismatch")
    parser=VisibleText()
    parser.feed(raw.decode("utf-8",errors="replace"))
    tokens=parser.fragments
    # Source-backed row context assists manual lane mapping. Row count alone
    # never certifies six lanes: official pages contain unrelated tables.
    labeled_rows=[{"row_index":i,"tokens":[s[:120] for s in row[:32]],
                   "labels":[label for label in LABELS if any(matches_label(label,s) for s in row)]}
                  for i,row in enumerate(parser.table_rows)
                  if any(matches_label(label,s) for label in LABELS for s in row)][:24]
    matched={label:[i for i,t in enumerate(tokens) if matches_label(label,t)][:15] for label in LABELS}
    # Preserve bounded, source-backed neighboring text to design a lane parser
    # from actual official pages; do not classify boat counts from labels.
    context={label:[{"index":i,"nearby":tokens[max(0,i-2):min(len(tokens),i+5)]}
                    for i in positions] for label,positions in matched.items()}
    context={label:[{"index":row["index"],"nearby":[item[:120] for item in row["nearby"]]}
                    for row in rows] for label,rows in context.items()}
    return {"race_code":manifest.get("race_code"),"sha256_verified":True,
            "request_started_at_jst":started.isoformat(),
            "received_at_jst":receipt.isoformat(),
            "http_elapsed_seconds":(receipt-started).total_seconds(),
            "visible_text_fragments":len(tokens),"label_positions":matched,
            "diagnostic_labeled_table_rows":labeled_rows,
            "label_context":context,
            "six_lane_values":"unverified","t12_eligible":False,"forecast_usable":False}

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("saved_dir")
    a=ap.parse_args()
    print(json.dumps(inspect(a.saved_dir),ensure_ascii=False,indent=2))

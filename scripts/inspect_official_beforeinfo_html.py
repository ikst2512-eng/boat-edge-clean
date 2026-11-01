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
class VisibleText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.fragments=[]
        self.hidden=0
    def handle_starttag(self,tag,attrs):
        if tag in ("script","style"):self.hidden+=1
    def handle_endtag(self,tag):
        if tag in ("script","style") and self.hidden:self.hidden-=1
    def handle_data(self,data):
        if not self.hidden:
            t=" ".join(data.split())
            if t:self.fragments.append(t)

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
    matched={label:[i for i,t in enumerate(tokens) if label in t][:15] for label in LABELS}
    # Preserve bounded, source-backed neighboring text to design a lane parser
    # from actual official pages; do not classify boat counts from labels.
    context={label:[{"index":i,"nearby":tokens[max(0,i-2):min(len(tokens),i+5)]}
                    for i in positions] for label,positions in matched.items()}
    context={label:[{"index":row["index"],"nearby":[item[:120] for item in row["nearby"]]}
                    for row in rows] for label,rows in context.items()}
    return {"race_code":manifest.get("race_code"),"sha256_verified":True,
            "visible_text_fragments":len(tokens),"label_positions":matched,
            "label_context":context,
            "six_lane_values":"unverified","t12_eligible":False,"forecast_usable":False}

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("saved_dir")
    a=ap.parse_args()
    print(json.dumps(inspect(a.saved_dir),ensure_ascii=False,indent=2))

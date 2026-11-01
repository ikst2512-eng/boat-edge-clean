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
    parser=VisibleText()
    parser.feed(raw.decode("utf-8",errors="replace"))
    tokens=parser.fragments
    matched={label:[i for i,t in enumerate(tokens) if label in t][:15] for label in LABELS}
    return {"race_code":manifest.get("race_code"),"sha256_verified":True,
            "visible_text_fragments":len(tokens),"label_positions":matched,
            "six_lane_values":"unverified","t12_eligible":False,"forecast_usable":False}

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("saved_dir")
    a=ap.parse_args()
    print(json.dumps(inspect(a.saved_dir),ensure_ascii=False,indent=2))

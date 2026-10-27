"""Read-only official result HTML parser for offline manifest preparation.

Input HTML must be independently captured with source URL, timestamp and
SHA-256; these source claims are not independently authenticated by this parser.
No network access or production modification.
"""
import argparse
import hashlib
import json
import re
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit, parse_qs

class PlainText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts=[]
    def handle_data(self, data):
        text=unescape(data).strip()
        if text:
            self.parts.append(text)

def parse_result(html, url):
    uri=urlsplit(url)
    if (uri.scheme != "https" or uri.hostname not in ("www.boatrace.jp", "boatrace.jp")
        or uri.path != "/owpc/pc/race/raceresult" or uri.username or uri.password
        or uri.port not in (None, 443)):
        raise ValueError("untrusted_official_result_url")
    query=parse_qs(uri.query)
    if set(query) != {"hd","jcd","rno"} or any(len(query[k]) != 1 for k in query):
        raise ValueError("invalid_result_query")
    hd,jcd,rno=(query[k][0] for k in ("hd","jcd","rno"))
    if not re.fullmatch(r"20[0-9]{6}",hd):
        raise ValueError("invalid_date")
    from datetime import datetime
    datetime.strptime(hd,"%Y%m%d")
    if not re.fullmatch(r"0[1-9]|1[0-9]|2[0-4]",jcd) or not re.fullmatch(r"[1-9]|1[0-2]",rno):
        raise ValueError("invalid_race_id")
    if len(html.encode("utf-8")) > 1500000:
        raise ValueError("oversize_html")
    parser=PlainText()
    parser.feed(html)
    flat=" ".join(parser.parts)
    # Extract ONLY the win-type trifecta payout row, not trifecta-odds or trifecta-pick widgets.
    matches=re.findall(r"(?:3連単|３連単)\s*([1-6])\s*[-－]\s*([1-6])\s*[-－]\s*([1-6])\s*[¥￥]?\s*[0-9,]+",flat)
    matches=[m for m in matches if len(set(m))==3]
    if len(matches) != 1:
        raise ValueError("missing_or_ambiguous_trifecta")
    return {"race_code": f"{hd}{jcd}{int(rno):02d}",
            "ticket":"-".join(matches[0]),"status":"final","source_kind":"official",
            "source_url":url,"html_sha256":hashlib.sha256(html.encode("utf-8")).hexdigest(),
            "verification_status":"UNVERIFIED_SOURCE_RECEIPT"}

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("html_file")
    p.add_argument("--official-url",required=True)
    a=p.parse_args()
    print(json.dumps(parse_result(Path(a.html_file).read_text(encoding="utf-8"),a.official_url),
                     ensure_ascii=False,indent=2))

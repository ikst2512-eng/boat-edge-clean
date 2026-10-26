"""Experimental fail-closed parser for isolated BOATRACE racelist HTML.

No production ingestion, validation of provenance, or Fresh promotion.
DOM assumptions require real, hash-pinned official fixtures before deployment.
"""
from html.parser import HTMLParser
from urllib.parse import urlparse, parse_qs
import re

BOAT = re.compile(r"^is-boatColor([1-6])$")
REG = re.compile(r"^[0-9]{4}$")


class _Rows(HTMLParser):
    def __init__(self):
        super().__init__()
        self.rows = []
        self.row = None
        self.cell = None
        self.anchor = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "tr":
            if self.row is not None:
                raise ValueError("nested race row")
            self.row = {"lanes": [], "racers": []}
        if self.row is None:
            return
        lane_class = attrs.get("class", "")
        for token in lane_class.split():
            lane = BOAT.fullmatch(token)
            if lane:
                self.row["lanes"].append(int(lane.group(1)))
        if tag == "a":
            query = parse_qs(urlparse(attrs.get("href", "")).query)
            token = query.get("toban", [])
            if len(token) == 1 and REG.fullmatch(token[0]):
                self.anchor = {"registration": token[0], "name": ""}
        if tag in ("td", "th"):
            self.cell = tag

    def handle_data(self, data):
        if self.anchor is not None:
            self.anchor["name"] += data

    def handle_endtag(self, tag):
        if tag == "a" and self.anchor is not None:
            name = " ".join(self.anchor["name"].split())
            if name:
                self.row["racers"].append({"registration": self.anchor["registration"], "name": name})
            self.anchor = None
        if tag in ("td", "th"):
            self.cell = None
        if tag == "tr" and self.row is not None:
            self.rows.append(self.row)
            self.row = None


def extract_six_candidates(html_bytes, source_url, race_key):
    """Return candidates, not official verification. Reject ambiguity or contamination."""
    match = re.fullmatch(r"(20[0-9]{6})-(0[1-9]|1[0-9]|2[0-4])-(0[1-9]|1[0-2])", race_key)
    if not match:
        raise ValueError("invalid race identity")
    u = urlparse(source_url)
    if u.scheme != "https" or u.hostname != "www.boatrace.jp" or u.path != "/owpc/pc/race/racelist" or u.username or u.password:
        raise ValueError("untrusted source")
    q = parse_qs(u.query)
    if (q.get("hd"), q.get("jcd"), q.get("rno")) != ([match[1]], [match[2]], [str(int(match[3]))]):
        raise ValueError("source race mismatch")
    if not isinstance(html_bytes, bytes) or len(html_bytes) > 2_000_000:
        raise ValueError("invalid HTML")
    try:
        content = html_bytes.decode("utf-8")
    except UnicodeDecodeError as e:
        raise ValueError("unknown HTML encoding") from e
    parser = _Rows()
    parser.feed(content)
    records = []
    for row in parser.rows:
        lanes = set(row["lanes"])
        if not lanes:
            continue
        if len(lanes) != 1 or len(row["racers"]) != 1:
            raise ValueError("ambiguous racelist row")
        records.append({"lane": next(iter(lanes)), **row["racers"][0]})
    if len(records) != 6 or sorted(r["lane"] for r in records) != [1, 2, 3, 4, 5, 6]:
        raise ValueError("six unique racelist rows required")
    if len({r["registration"] for r in records}) != 6:
        raise ValueError("duplicate registration")
    return {"race_key": race_key, "status": "html_candidates_unverified",
            "official_provenance_verified": False, "racers": sorted(records, key=lambda x: x["lane"])}

"""Research-only extraction of six start-exhibition course/ST rows.

Based on publicly documented historic official CSS classes. NOT validated on
2026 official HTML and deliberately NOT connected to live site or Fresh.
"""
from html.parser import HTMLParser
import re


class _ExhibitionParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []
        self.boats = []

    def handle_starttag(self, tag, attrs):
        classes = set(dict(attrs).get("class", "").split())
        record = None
        if "table1_boatImage1" in classes:
            record = {"number": [], "st": []}
            self.boats.append(record)
        parent = next((f["record"] for f in reversed(self.stack)
                       if f["record"] is not None), None)
        record = record or parent
        target = None
        if "table1_boatImage1Number" in classes:
            target = "number"
        if "table1_boatImage1Time" in classes:
            target = "st"
        self.stack.append({"tag": tag, "record": record, "target": target})

    def handle_endtag(self, tag):
        for idx in range(len(self.stack)-1, -1, -1):
            if self.stack[idx]["tag"] == tag:
                del self.stack[idx:]
                return

    def handle_data(self, data):
        record = next((f["record"] for f in reversed(self.stack)
                       if f["target"] is not None), None)
        target = next((f["target"] for f in reversed(self.stack)
                       if f["target"] is not None), None)
        if record is not None:
            record[target].append(data.strip())


def research_start_exhibition(raw):
    """Return six research records or raise. Never verify actual race entry."""
    if not raw or len(raw) > 1_500_000:
        raise ValueError("invalid source size")
    p = _ExhibitionParser()
    p.feed(raw.decode("utf-8", "strict"))
    if len(p.boats) != 6:
        raise ValueError("exactly six start-exhibition records required")
    records = []
    for position, record in enumerate(p.boats, 1):
        number = "".join(record["number"]).strip()
        st = "".join(record["st"]).strip().upper()
        if not re.fullmatch(r"[1-6]", number):
            raise ValueError("invalid exhibition boat number")
        match = re.fullmatch(r"(F|L)?(?:0\\.|\\.)?([0-9]{2})", st)
        if not match:
            raise ValueError("invalid exhibition ST")
        value = int(match.group(2)) / 100
        if match.group(1) == "F":
            value = -value
        elif match.group(1) == "L":
            raise ValueError("L exhibition ST requires manual review")
        records.append({"exhibition_course": position,
                        "boat_number": int(number),
                        "exhibition_st": value})
    if sorted(row["boat_number"] for row in records) != list(range(1, 7)):
        raise ValueError("duplicate/missing exhibition boat")
    return {"status": "research_unverified", "source": "historical_css_layout",
            "actual_entry_verified": False, "verified_preview": False,
            "start_exhibition": records}

"""Fail-closed extraction gate; metadata only, never read results endpoints."""
from html.parser import HTMLParser
import re

class RaceTables(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tables = 0
        self.rows = 0
        self.cells = 0
        self.colors = set()
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "table": self.tables += 1
        if tag == "tr": self.rows += 1
        if tag in ("td", "th"): self.cells += 1
        for value in attrs.get("class", "").split():
            m = re.fullmatch(r"is-boatColor([1-6])", value)
            if m: self.colors.add(int(m.group(1)))

def verify_structure(html_text):
    p = RaceTables()
    p.feed(html_text)
    return {
        "table_count": p.tables,
        "row_count": p.rows,
        "cell_count": p.cells,
        "boat_color_count": len(p.colors),
        "six_colors_present": p.colors == set(range(1, 7)),
        "exhibition_present": "展示" in html_text,
        "entry_present": "進入" in html_text,
        "source_is_safe_for_forecast": False,
        "six_numeric_exhibition_rows_extracted": False,
    }

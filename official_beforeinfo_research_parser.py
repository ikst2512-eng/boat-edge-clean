"""Research-only extraction of six start-exhibition course/ST rows.

Based on publicly documented historic official CSS classes. NOT validated on
2026 official HTML and deliberately NOT connected to live site or Fresh.
"""
from html.parser import HTMLParser
import re


class ResearchParseUnavailable(ValueError):
    """Valid archived source could not be interpreted by experimental CSS parser."""


class ExhibitionNotPublished(ResearchParseUnavailable):
    """The current official start-exhibition table has six empty placeholders."""


class _CurrentTablePlaceholder(HTMLParser):
    """Identify the exact blank six-row table seen in archived 2026 official HTML."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tables = []
        self.table = None
        self.section = None
        self.in_cell = False
        self.cell_attrs = {}
        self.cell_text = []
        self.in_row = False
        self.row_cells = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "table":
            self.table = {"heading": False, "rows": []}
        elif self.table is not None:
            if tag in ("thead", "tbody"):
                self.section = tag
            elif tag == "tr":
                self.in_row = True
                self.row_cells = []
            elif tag in ("th", "td"):
                self.in_cell = True
                self.cell_attrs = attrs
                self.cell_text = []

    def handle_data(self, text):
        if self.in_cell:
            self.cell_text.append(text)

    def handle_endtag(self, tag):
        if self.table is None:
            return
        if tag in ("th", "td") and self.in_cell:
            content = "".join(self.cell_text).strip()
            if self.section == "thead" and "スタート展示" in content:
                self.table["heading"] = True
            if self.section == "tbody":
                self.row_cells.append((self.cell_attrs.get("colspan"), content))
            self.in_cell = False
        elif tag == "tr" and self.in_row:
            if self.section == "tbody":
                self.table["rows"].append(self.row_cells)
            self.in_row = False
        elif tag in ("thead", "tbody"):
            self.section = None
        elif tag == "table":
            self.tables.append(self.table)
            self.table = None


def current_exhibition_is_blank(raw):
    parser = _CurrentTablePlaceholder()
    parser.feed(raw.decode("utf-8", "strict"))
    parser.close()
    matching = [t for t in parser.tables if t["heading"]]
    return len(matching) == 1 and len(matching[0]["rows"]) == 6 and all(
        row == [("3", "")] for row in matching[0]["rows"]
    )


class _ExhibitionParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []
        self.boats = []

    VOID = frozenset(("area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"))

    def handle_starttag(self, tag, attrs):
        if tag in self.VOID:
            return
        attributes = dict(attrs)
        classes = set((attributes.get("class") or "").split())
        style = re.sub(r"\s+", "", attributes.get("style") or "").lower()
        if (tag in ("script", "style", "template", "noscript", "svg", "head")
                or "hidden" in attributes
                or (attributes.get("aria-hidden") or "").lower() == "true"
                or "display:none" in style or "visibility:hidden" in style):
            self.stack.append({"tag": tag, "record": None, "target": None, "blocked": True})
            return
        if any(frame.get("blocked") for frame in self.stack):
            self.stack.append({"tag": tag, "record": None, "target": None, "blocked": True})
            return
        parent = next((f["record"] for f in reversed(self.stack)
                       if f["record"] is not None), None)
        record = None
        if "table1_boatImage1" in classes:
            if parent is not None:
                raise ValueError("nested exhibition boat records")
            record = {"number": [], "st": []}
            self.boats.append(record)
        record = record or parent
        target = None
        if record is not None and "table1_boatImage1Number" in classes:
            target = "number"
        if record is not None and "table1_boatImage1Time" in classes:
            target = "st"
        self.stack.append({"tag": tag, "record": record, "target": target, "blocked": False})

    def handle_startendtag(self, tag, attrs):
        # Self-closing tags must never leave a phantom parent in the stack.
        return

    def handle_endtag(self, tag):
        for idx in range(len(self.stack)-1, -1, -1):
            if self.stack[idx]["tag"] == tag:
                del self.stack[idx:]
                return

    def handle_data(self, data):
        if any(frame.get("blocked") for frame in self.stack):
            return
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
    p.close()
    if p.stack:
        raise ValueError("unclosed exhibition HTML structure")
    if len(p.boats) != 6:
        raise ValueError("exactly six start-exhibition records required")
    records = []
    for position, record in enumerate(p.boats, 1):
        number = "".join(record["number"]).strip()
        st = "".join(record["st"]).strip().upper()
        if not re.fullmatch(r"[1-6]", number):
            raise ValueError("invalid exhibition boat number")
        # A bare "08" is ambiguous (hundredths versus display placeholder).
        # Require an explicit decimal point and retain the F marker separately.
        match = re.fullmatch(r"(F|L)?(?:0[.]|[.])([0-9]{2})", st)
        if not match:
            raise ValueError("invalid exhibition ST")
        value = int(match.group(2)) / 100
        if match.group(1) == "F":
            value = -value
        elif match.group(1) == "L":
            raise ValueError("L exhibition ST requires manual review")
        records.append({"exhibition_course": position,
                        "boat_number": int(number),
                        "exhibition_st": value,
                        "exhibition_st_raw": st,
                        "exhibition_st_flying": match.group(1) == "F"})
    if sorted(row["boat_number"] for row in records) != list(range(1, 7)):
        raise ValueError("duplicate/missing exhibition boat")
    return {"status": "research_unverified", "source": "historical_css_layout",
            "actual_entry_verified": False, "verified_preview": False,
            "start_exhibition": records}


def research_saved_start_exhibition(directory, race_key, digest, *, deadline):
    """Research parser entry point: archived official bytes must pass readback first."""
    from official_prerace_capture import read_raw_receipt
    receipt, raw = read_raw_receipt(directory, race_key, digest, deadline=deadline)
    try:
        if current_exhibition_is_blank(raw):
            raise ExhibitionNotPublished("six empty official start-exhibition rows")
        result = research_start_exhibition(raw)
    except ExhibitionNotPublished:
        raise
    except (ValueError, UnicodeError) as exc:
        raise ResearchParseUnavailable("research CSS parsing unavailable") from exc
    result["race_key"] = receipt["race_key"]
    result["raw_sha256"] = receipt["sha256"]
    result["captured_at"] = receipt["fetched_at"]
    return result

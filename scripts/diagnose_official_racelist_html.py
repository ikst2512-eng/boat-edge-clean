"""Read-only HTML shape diagnostics. No six-racer or entry certification."""
from html.parser import HTMLParser


class _Shape(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tables = 0
        self.rows = 0
        self.body = 0
        self.scripts = 0
        self.forms = 0

    def handle_starttag(self, tag, attrs):
        if tag == "table":
            self.tables += 1
        elif tag == "tr":
            self.rows += 1
        elif tag == "body":
            self.body += 1
        elif tag == "script":
            self.scripts += 1
        elif tag == "form":
            self.forms += 1


def diagnose_racelist_html(raw):
    if not isinstance(raw, bytes) or not raw:
        raise ValueError("missing source HTML")
    shape = _Shape()
    shape.feed(raw.decode("utf-8", "replace"))
    shape.close()
    return {
        "html_table_count": shape.tables,
        "html_tr_count": shape.rows,
        "html_body_count": shape.body,
        "html_script_count": shape.scripts,
        "html_form_count": shape.forms,
        "six_racer_rows_verified": False,
        "official_entry_verified": False,
        "diagnostic_only": True,
    }

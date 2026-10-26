"""Diagnostic-only inspection of archived official beforeinfo HTML.

This is not a production parser. It does not extract boat values, infer courses,
or promote source documents to a verified race snapshot.
"""
from html.parser import HTMLParser
import re


class _VisibleText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.hidden = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.hidden += 1

    def handle_endtag(self, tag):
        if tag in ("script", "style") and self.hidden:
            self.hidden -= 1

    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(data)


def inspect_beforeinfo_html(receipt, raw):
    """Report only visible section coverage; always return unverified."""
    if receipt.get("status") != "raw_html_only" or receipt.get("verified_preview") is not False:
        raise ValueError("only raw, unverified source receipts accepted")
    if len(raw) > 1_500_000 or not raw:
        raise ValueError("invalid HTML input size")
    text = raw.decode("utf-8", errors="strict")
    parser = _VisibleText()
    parser.feed(text)
    visible = re.sub(r"\s+", "", "".join(parser.parts))
    labels = {
        "exhibition_time": "展示タイム" in visible,
        "tilt": "チルト" in visible,
        "start_exhibition": "スタート展示" in visible,
        "weather": any(label in visible for label in ("気温", "風速", "水温", "波高")),
    }
    return {
        "race_key": receipt["race_key"],
        "sections_present": labels,
        "missing_sections": [k for k, found in labels.items() if not found],
        "status": "inspection_only",
        "verified_preview": False,
        "actual_entry_verified": False,
        "racers": [],
        "start_exhibition": [],
    }

"""Diagnostic-only inspection of archived official beforeinfo HTML.

This is not a production parser. It does not extract boat values, infer courses,
or promote source documents to a verified race snapshot.
"""
from html.parser import HTMLParser
import re


class _VisibleText(HTMLParser):
    """Ignore hidden DOM sections so placeholders cannot prove availability."""
    VOID = frozenset(("area", "base", "br", "col", "embed", "hr",
                      "img", "input", "link", "meta", "param", "source",
                      "track", "wbr"))
    HIDDEN = frozenset(("script", "style", "template", "noscript", "svg"))

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.stack = []

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        styles = re.sub(r"\s+", "", attributes.get("style") or "").lower()
        hidden = (tag in self.HIDDEN or "hidden" in attributes
                  or (attributes.get("aria-hidden") or "").lower() == "true"
                  or "display:none" in styles or "visibility:hidden" in styles)
        if tag not in self.VOID:
            parent_hidden = self.stack[-1][1] if self.stack else False
            self.stack.append((tag, hidden or parent_hidden))

    def handle_startendtag(self, tag, attrs):
        pass

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index][0] == tag:
                del self.stack[index:]
                break

    def handle_data(self, data):
        if not self.stack or not self.stack[-1][1]:
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
    # Preserve element boundaries: hidden sections must not join two text fragments.\n    visible = " ".join(re.sub(r"\\s+", "", part) for part in parser.parts)
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


def inspect_saved_beforeinfo(directory, race_key, digest, *, deadline):
    """Inspect only after independently validating the complete archived receipt.

    Returns diagnostics, never a production race JSON or verified lane values.
    """
    from official_prerace_capture import read_raw_receipt
    receipt, raw = read_raw_receipt(directory, race_key, digest, deadline=deadline)
    return inspect_beforeinfo_html(receipt, raw)

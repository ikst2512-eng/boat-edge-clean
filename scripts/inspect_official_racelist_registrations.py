"""Fail-closed six-lane registration parsing from observed official racelist XHTML."""
import re
from html import unescape

# Anchored to the actual main racer row in archived 2026-11-03 Toda 12R XHTML.
ROW = re.compile(
    r'<tr\b[^>]*>\s*<td\b(?=[^>]*class="is-boatColor([1-6])\s+is-fs14")'
    r'(?=[^>]*rowspan="4")[^>]*>\s*([１２３４５６])\s*</td>'
    r'(?P<cells>.{0,4096}?)</tr>',
    re.S,
)
REG = re.compile(r'/owpc/pc/data/racersearch/profile\?toban=([0-9]{4})')


def inspect_six_registrations(raw):
    if not isinstance(raw, bytes):
        raise ValueError("expected original bytes")
    html = unescape(raw.decode("utf-8", "replace"))
    registrations = {}
    for row in ROW.finditer(html):
        lane = int(row.group(1))
        label_lane = "１２３４５６".index(row.group(2)) + 1
        ids = REG.findall(row.group("cells"))
        if (lane != label_lane or not 1 <= len(ids) <= 2\n                or len(set(ids)) != 1 or lane in registrations):
            raise ValueError("ambiguous racer row")
        registrations[lane] = ids[0]
    complete = (set(registrations) == set(range(1, 7))
                and len(set(registrations.values())) == 6)
    return {
        "six_racers_verified": complete,
        "registrations_by_lane": {str(l): registrations[l] for l in sorted(registrations)} if complete else {},
        "entry_verified": False, "forecast_usable": False, "t12_eligible": False,
    }

"""Unpromoted official racelist motor display research for #1710.

Runs AFTER the exact preregistered six-racer racelist parser. Does not
alter its frozen Git blob, treat a displayed rate as a count-backed rate,
or attest a real HTTP/T-12 receipt. This adapter is NOT in the model path.
"""
from hashlib import sha256
from html import unescape
import re

from scripts.inspect_official_racelist_registrations import ROW
from scenario_official_racelist_rates import (
    _CellText, extract_six_official_racelist_rates,
)

_MOTOR = re.compile(r"^(\d{1,3})\s+(\d{1,3}\.\d{1,2})\s+(\d{1,3}\.\d{1,2})$")
_BOATS = set(range(1, 7))


def extract_motor_display_unqualified(raw):
    """Parse original HTML, never infer motor run counts or success counts.

    Per-race registration and source receipt linkage remains the job of the
    independent three-original auditor / #1746, not this static parser.
    """
    frozen = extract_six_official_racelist_rates(raw)
    html = unescape(raw.decode("utf-8", "replace"))
    parsed = {}
    for match in ROW.finditer(html):
        boat = int(match.group(1))
        if boat not in _BOATS or boat in parsed:
            raise ValueError("ambiguous_motor_lane")
        cells = _CellText()
        cells.feed("<tr>" + match.group("cells") + "</tr>")
        cells.close()
        if (len(cells.cells) < 7 or
                "is-lineH2" not in cells.cells[5]["attrs"].get("class", "").split()):
            raise ValueError("motor_column_drifted")
        motor = _MOTOR.fullmatch(cells.cells[5]["text"])
        if motor is None:
            raise ValueError("motor_rate_unreadable")
        number = int(motor.group(1))
        r2, r3 = float(motor.group(2)), float(motor.group(3))
        if not 1 <= number <= 999 or not 0 <= r2 <= r3 <= 100:
            raise ValueError("motor_display_out_of_bounds")
        parsed[boat] = {
            "boat": boat,
            "registration_id": frozen["boats"][boat - 1]["registration_id"],
            "motor_number": number,
            "displayed_motor_2ren_pct": r2,
            "displayed_motor_3ren_pct": r3,
            "motor_starts": None,
            "motor_2ren_successes": None,
        }
    if set(parsed) != _BOATS:
        raise ValueError("six_motor_lanes_required")
    return {
        "schema": "OFFICIAL_RACELIST_MOTOR_DISPLAY_UNQUALIFIED_V1",
        "source_sha256": sha256(raw).hexdigest(),
        "rows": [parsed[boat] for boat in range(1, 7)],
        "sample_denominator_verified": False,
        "same_race_http_receipt_verified": False,
        "pre_T12_receipt_verified": False,
        "input_to_matrix_allowed": False,
        "formal": False,
        "production_changed": False,
    }

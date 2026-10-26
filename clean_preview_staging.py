"""Isolated preview CSV validator: never publishes or authorizes scoring.

BoatraceCSV is third-party data. A staging match does not establish official
source authenticity. Previews may arrive close to cutoff, so timestamps must
not be treated as proof of predeadline forecast inputs.
"""
import csv
import io
import re
from datetime import datetime

KINDS = {"stt", "tkz", "sui"}
ST_PATTERN = re.compile(r"^(?:F[.]?[0-9]{1,2}|[.]?[0-9]{1,2}|[0-9][.][0-9]{1,2})$")
NUMBER_PATTERN = re.compile(r"^-?[0-9]+(?:[.][0-9]+)?$")
BASE = "https://boatracecsv.github.io/data/previews/"
CODE = re.compile(r"^20[0-9]{10}$")


def stage_preview(text, race_code, kind, source_url):
    if kind not in KINDS or not isinstance(race_code, str) or not CODE.fullmatch(race_code):
        raise ValueError("invalid preview identity")
    day = datetime.strptime(race_code[:8], "%Y%m%d").strftime("%Y-%m-%d")
    expected = BASE + kind + "/" + race_code[:4] + "/" + race_code[4:6] + "/" + race_code[6:8] + ".csv"
    if source_url != expected:
        raise ValueError("preview source mismatch")
    if not isinstance(text, str) or len(text.encode("utf-8")) > 2_000_000:
        raise ValueError("invalid preview CSV")
    rows = list(csv.DictReader(io.StringIO(text.lstrip("\ufeff"))))
    matches = [r for r in rows if r.get("レースコード") == race_code]
    if len(matches) != 1:
        raise ValueError("preview race unavailable or duplicate")
    row = matches[0]
    if (row.get("レース日") != day or row.get("レース場") != race_code[8:10]
            or row.get("レース回") != str(int(race_code[10:12])).zfill(2) + "R"):
        raise ValueError("cross-race preview row")
    try:
        received = datetime.fromisoformat(row["取得日時"])
    except (TypeError, ValueError, KeyError):
        raise ValueError("invalid preview provenance time") from None
    if received.utcoffset() is None:
        raise ValueError("naive preview provenance time")
    deadline = row.get("締切時刻")
    if not isinstance(deadline, str) or not re.fullmatch(r"(?:[01][0-9]|2[0-3]):[0-5][0-9]", deadline):
        raise ValueError("invalid deadline")
    values = {}
    if kind in ("stt", "tkz"):
        fields = ("コース", "スタート展示") if kind == "stt" else ("展示タイム", "チルト")
        for lane in range(1, 7):
            vals = {}
            for field in fields:
                col = f"艇{lane}_{field}"
                if col not in row:
                    raise ValueError("missing six-lane column")
                raw = row[col]
                vals[field] = raw.strip() if isinstance(raw, str) and raw.strip() else None
            values[lane] = vals
        if kind == "stt":
            for lane in range(1, 7):
                st = values[lane]["スタート展示"]
                if st is not None and not ST_PATTERN.fullmatch(st):
                    raise ValueError("invalid exhibition ST")
            courses = [values[i]["コース"] for i in range(1, 7)]
            if any(x is None or not re.fullmatch("[1-6]", x) for x in courses) or set(courses) != set("123456"):
                raise ValueError("unknown or duplicate exhibition entry")
        else:
            for lane in range(1, 7):
                for field in ("展示タイム", "チルト"):
                    value = values[lane][field]
                    if value is not None and not NUMBER_PATTERN.fullmatch(value):
                        raise ValueError("invalid exhibition numeric field")
    elif kind == "sui":
        for field in ("風速(m)", "風向", "波の高さ(cm)", "天候", "気温(℃)", "水温(℃)"):
            if field not in row:
                raise ValueError("missing weather column")
            values[field] = row[field] or None
    return {"race_code": race_code, "kind": kind, "deadline": deadline,
            "fetched_at": received.isoformat(), "source_url": source_url,
            "values": values, "status": "staged_unpublished", "source_kind": "third_party_csv_unverified"}

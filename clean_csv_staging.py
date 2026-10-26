"""Read-only CSV race-card mapper for isolated CLEAN staging.

BoatraceCSV is a third-party derived feed, NOT the official source of record.
No result, prediction, publication, or formal Fresh authorization is emitted.
"""
import csv
import io
import re
from datetime import datetime
from urllib.parse import urlparse

BASE = "https://boatracecsv.github.io/data/programs/"
CODE = re.compile(r"^20[0-9]{10}$")


def map_race_card(csv_text, race_code, source_url, fetched_at):
    if not isinstance(race_code, str) or not CODE.fullmatch(race_code):
        raise ValueError("invalid race code")
    datetime.strptime(race_code[:8], "%Y%m%d")
    if not isinstance(source_url, str) or source_url != (
        BASE + "race_cards/" + race_code[:4] + "/" + race_code[4:6] + "/" + race_code[6:8] + ".csv"
    ):
        raise ValueError("CSV source URL mismatch")
    try:
        fetched = datetime.fromisoformat(fetched_at)
    except (TypeError, ValueError):
        raise ValueError("invalid fetched timestamp") from None
    if fetched.tzinfo is None or fetched.utcoffset() is None:
        raise ValueError("timestamp must include timezone")
    if not isinstance(csv_text, str) or len(csv_text.encode("utf-8")) > 2_000_000:
        raise ValueError("invalid CSV size")
    rows = list(csv.DictReader(io.StringIO(csv_text.lstrip("\ufeff"))))
    matches = [r for r in rows if r.get("レースコード") == race_code]
    if len(matches) != 1:
        raise ValueError("race missing or duplicated")
    row = matches[0]
    racers = []
    for lane in range(1, 7):
        prefix = f"艇{lane}_"
        name = row.get(prefix + "選手名")
        registration = row.get(prefix + "登録番号")
        if not name or not name.strip() or not registration or not registration.isascii() or not registration.isdigit():
            raise ValueError("incomplete six-racer card")
        racers.append({"lane": lane, "name": name.strip(), "registration": registration})
    if not re.fullmatch(r"(?:0?[1-9]|1[0-9]|2[0-4])", row.get("レース場コード", "")) or row["レース場コード"].zfill(2) != race_code[8:10]:
        raise ValueError("venue mismatch")
    race_no = row.get("レース回", "")
    if not re.fullmatch(r"(?:[1-9]|1[0-2])R", race_no) or f"{int(race_no[:-1]):02d}" != race_code[10:12]:
        raise ValueError("race number mismatch")
    if row.get("レース日") != datetime.strptime(race_code[:8], "%Y%m%d").strftime("%Y-%m-%d"):
        raise ValueError("race date mismatch")
    return {
        "race_code": race_code, "racers": racers,
        "source_url": source_url, "fetched_at": fetched.isoformat(),
        "source_kind": "third_party_csv_unverified", "status": "staged_unpublished",
    }

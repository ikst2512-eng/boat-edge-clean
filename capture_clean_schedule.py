"""Persist CLEAN-owned immutable daily schedule snapshots, no legacy repository."""
import json
import os
from datetime import datetime
from pathlib import Path
from clean_schedule import clean_schedule
from research_model import JST

ROOT = Path(__file__).resolve().parent
def capture(day=None):
    day = day or datetime.now(JST).strftime("%Y%m%d")
    status, source = clean_schedule(day)
    if status != 200:
        raise ValueError("independent schedule unavailable: " + source.get("status", "unknown"))
    venues = {}
    for race in source["races"]:
        jcd = race["venue_code"]
        venues.setdefault(jcd, []).append({"race_no": race["race_no"],
                                            "deadline": race["deadline_jst"][11:16]})
    record = {"date": f"{day[:4]}-{day[4:6]}-{day[6:8]}",
              "phase": "PRE_RESULT", "results_seen": False,
              "unlock": False, "scoring": False,
              "source_kind": "CLEAN_INDEPENDENT_PUBLISHED_SCHEDULE",
              "source_sha256": source["source_sha256"],
              "source_received_jst": source["source_received_jst"],
              "venues": [{"jcd": code, "races": sorted(races,key=lambda r:r["race_no"])}
                         for code,races in sorted(venues.items())]}
    path = ROOT / "schedule_snapshots" / (day+".json")
    path.parent.mkdir(exist_ok=True)
    if path.is_symlink():
        raise ValueError("symlink prohibited")
    if path.exists():
        previous=json.loads(path.read_text(encoding="utf-8"))
        if previous != record:
            # Live title CSV can change; preserve first observed snapshot.
            print("EXISTS_UNCHANGED_RECORD: no overwrite", day)
        return {"already_saved": 1, "saved": 0, "date": day}
    with path.open("x",encoding="utf-8") as out:
        json.dump(record,out,ensure_ascii=False,sort_keys=True)
        out.flush()
        os.fsync(out.fileno())
    return {"already_saved": 0, "saved": 1, "date": day}
if __name__=="__main__":
    print(json.dumps(capture(),ensure_ascii=False))

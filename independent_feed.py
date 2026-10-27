"""CLEAN-owned research archive reader. Never fall back to the legacy repository."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
KEY = re.compile(r"^[0-9]{8}[0-9]{2}[0-9]{2}$")


def research_snapshot(hd, jcd, rno):
    try:
        if not re.fullmatch(r"[0-9]{8}", str(hd)):
            raise ValueError()
        venue, race = int(jcd), int(rno)
        if not 1 <= venue <= 24 or not 1 <= race <= 12:
            raise ValueError()
        key = f"{hd}{venue:02d}{race:02d}"
        if not KEY.fullmatch(key):
            raise ValueError()
    except (ValueError, TypeError):
        return 400, {"ok": False, "status": "invalid_request"}
    path = ROOT / "research_snapshots" / (key + ".json")
    if path.is_symlink() or not path.is_file():
        return 404, {"ok": False, "status": "not_collected", "race_code": key}
    try:
        if path.stat().st_size > 20000:
            raise ValueError("oversize")
        data = json.loads(path.read_text(encoding="utf-8"))
        tickets = data.get("predictions")
        if (data.get("race_code") != key or data.get("status") != "research"
                or data.get("validated") is not False
                or not isinstance(tickets, list) or len(tickets) != 10
                or len(set(tickets)) != 10
                or not all(isinstance(t, str) and re.fullmatch(r"[1-6]-[1-6]-[1-6]", t)
                               and len(set(t.split("-"))) == 3 for t in tickets)):
            raise ValueError("invalid research archive")
        return 200, {
            "ok": True, "status": "research", "validated": False,
            "formal": False, "scoring": False, "race_code": key,
            "predictions": tickets, "model_version": data.get("model_version"),
            "generated_at": data.get("generated_at"),
            "message": "CLEAN独立保存の研究予想。正式予想・的中率集計には使用しません。",
        }
    except (OSError, ValueError, TypeError, AttributeError):
        return 503, {"ok": False, "status": "invalid_archive", "race_code": key}

"""Fail-closed reader for independently confirmed CLEAN result archives.

No legacy repository fallback. Nothing in this module collects official results.
A result must have an explicit original source, confirmation time and finish order.
"""
import json
import re
from pathlib import Path
from datetime import datetime
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

ROOT = Path(__file__).resolve().parent
CODE_RE = re.compile(r"^[0-9]{8}(?:0[1-9]|1[0-9]|2[0-4])(?:0[1-9]|1[0-2])$")


def read_result(hd, jcd, rno):
    try:
        if not isinstance(hd, str) or not re.fullmatch(r"[0-9]{8}", hd):
            raise ValueError("date")
        datetime.strptime(hd, "%Y%m%d")
        venue, race = int(jcd), int(rno)
        if not 1 <= venue <= 24 or not 1 <= race <= 12:
            raise ValueError("race")
        code = f"{hd}{venue:02d}{race:02d}"
    except (ValueError, TypeError):
        return 400, {"ok": False, "status": "invalid_request"}
    path = ROOT / "confirmed_results" / (code + ".json")
    if path.is_symlink():
        return 503, {"ok": False, "status": "invalid_result_archive", "race_code": code}
    try:
        if path.is_file():
            if path.stat().st_size > 20000:
                raise ValueError("oversize")
            raw = path.read_bytes()
        else:
            # Read-only CLEAN self-repository, never legacy boat-edge. This
            # decouples new immutable result commits from Render redeploy lag.
            url = ("https://raw.githubusercontent.com/ikst2512-eng/"
                   "boat-edge-clean/main/confirmed_results/" + code + ".json")
            try:
                with urlopen(Request(url, headers={"User-Agent": "CLEAN-RESULT-READER/1.0"}),
                             timeout=8) as response:
                    raw = response.read(20001)
            except HTTPError as exc:
                if exc.code == 404:
                    return 404, {"ok": False, "status": "not_confirmed", "race_code": code}
                raise
            if len(raw) > 20000:
                raise ValueError("oversize")
        data = json.loads(raw.decode("utf-8"))
        if not isinstance(data, dict):
            raise ValueError("record")
        if data.get("race_code") != code or data.get("status") != "confirmed":
            raise ValueError("status")
        finish = data.get("finish_order")
        if not isinstance(finish, list) or len(finish) != 3:
            raise ValueError("finish")
        if any(not isinstance(n, int) or isinstance(n, bool) or n not in range(1, 7) for n in finish):
            raise ValueError("lanes")
        if len(set(finish)) != 3:
            raise ValueError("duplicate")
        source = data.get("source_url")
        if not isinstance(source, str) or not source.startswith("https://") or len(source) > 2048:
            raise ValueError("source")
        for name in ("confirmed_at_jst", "collected_at_jst"):
            when = data.get(name)
            parsed = datetime.fromisoformat(when) if isinstance(when, str) else None
            if parsed is None or parsed.utcoffset() is None:
                raise ValueError(name)
        return 200, {"ok": True, "status": "confirmed", "race_code": code,
                     "finish_order": finish, "source_url": source,
                     "confirmed_at_jst": data["confirmed_at_jst"],
                     "collected_at_jst": data["collected_at_jst"]}
    except (OSError, ValueError, TypeError, KeyError, AttributeError, URLError, TimeoutError):
        return 503, {"ok": False, "status": "invalid_result_archive", "race_code": code}

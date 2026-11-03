"""Check public Render HTTP responses without changing forecast data."""
import json
import sys
from urllib.request import Request, urlopen

BASE = "https://boat-edge-clean.onrender.com"

def get(path):
    req = Request(BASE + path, headers={"User-Agent": "BOAT-EDGE-CLEAN-public-smoke/1"})
    with urlopen(req, timeout=75) as response:
        if response.status != 200:
            raise AssertionError(f"{path}: HTTP {response.status}")
        return response.read()

def main():
    html = get("/forecast").decode("utf-8")
    required = (
        "AI予想｜4モード",
        'id="fourModeForecastPanel"',
        "本命・バランス・穴・絞り",
        'id="legacyTopnResearch"',
        "/api/four-mode-archive",
    )
    missing = [token for token in required if token not in html]
    if missing:
        raise AssertionError("Public HTML is missing expected 4-mode elements: " + repr(missing))
    # This archive existed before today's UI change; historical, not formal.
    raw = get("/api/four-mode-archive?code=202610280101")
    record = json.loads(raw)
    if (record.get("status") != "historical_research_only"
            or record.get("production_forecast") is not False
            or record.get("verified_first_git_add") is not False
            or set(record.get("modes", {})) != {"hit", "balance", "hole", "narrow"}):
        raise AssertionError("Public four-mode API contract mismatch")
    print(json.dumps({"public_forecast_http": 200, "public_archive_http": 200,
                      "four_modes_present": True, "legacy_topn_collapsed": True,
                      "historical_not_formal": True}, sort_keys=True))

if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"PRODUCTION_SMOKE_FAILED: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise SystemExit(1)

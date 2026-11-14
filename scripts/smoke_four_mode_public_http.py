"""Check public Render HTTP responses without changing forecast data."""
import json
import sys
from urllib.request import Request, urlopen
from urllib.error import HTTPError

BASE = "https://boat-edge-clean.onrender.com"

def get(path):
    req = Request(BASE + path, headers={"User-Agent": "BOAT-EDGE-CLEAN-public-smoke/1"})
    with urlopen(req, timeout=75) as response:
        if response.status != 200:
            raise AssertionError(f"{path}: HTTP {response.status}")
        return response.read()

def deployed_revision():
    """Read the public Render revision, never substitute main's SHA."""
    req = Request(BASE + "/healthz",
                  headers={"User-Agent": "BOAT-EDGE-CLEAN-public-smoke/1"})
    try:
        with urlopen(req, timeout=30) as response:
            sha = response.headers.get("X-Boat-Edge-Deploy-Commit", "")
            if response.status == 200 and len(sha) == 40 and all(ch in "0123456789abcdef" for ch in sha.lower()):
                return sha.lower()
    except (OSError, TimeoutError):
        pass
    return "unverified"


def main():
    revision = deployed_revision()
    print("RENDER_PUBLIC_DEPLOY_COMMIT=" + revision, flush=True)
    html = get("/forecast").decode("utf-8")
    required = (
        "展開重視予想｜4モード",
        "/api/v133-reference-preview",
        'id="restoredScenarioPanel"',
        'id="restoredScenarioStatus"',
        "/api/legacy-scenario-preview",
        'id="fourModeForecastPanel"',
        "V2全国勝率基準｜保存済み4モード",
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
    # Invalid future request exercises only the new route's validation:
    # it must not fetch sources, create a candidate or rewrite an archive.
    req = Request(BASE + "/api/legacy-scenario-preview?hd=20261112&jcd=99&rno=1",
                  headers={"User-Agent": "BOAT-EDGE-CLEAN-public-smoke/1"})
    try:
        with urlopen(req, timeout=30) as response:
            raise AssertionError("invalid venue unexpectedly accepted: "+str(response.status))
    except HTTPError as error:
        if error.code != 400:
            raise AssertionError("restored scenario API absent or wrong status: "+str(error.code))
        payload = json.loads(error.read(5000))
        if payload != {"ok": False, "status": "invalid_race"}:
            raise AssertionError("restored scenario API response mismatch")
        if error.headers.get("Access-Control-Allow-Origin") != "https://ikst2512-eng.github.io":
            raise AssertionError("restored scenario API lacks Pages CORS")
    # New V127/V133 reference route is valid only on a deployed matching
    # backend; an invalid request must reject without reading race data.
    req = Request(BASE + "/api/v133-reference-preview?hd=invalid&jcd=01&rno=1",
                  headers={"User-Agent": "BOAT-EDGE-CLEAN-public-smoke/1"})
    try:
        with urlopen(req, timeout=30) as response:
            raise AssertionError("invalid V133 request unexpectedly accepted: "+str(response.status))
    except HTTPError as error:
        if error.code != 400:
            raise AssertionError("V133 API not deployed or wrong status: "+str(error.code)+", Render revision: "+revision)
        payload = json.loads(error.read(5000))
        if payload != {"ok": False, "status": "invalid_race"}:
            raise AssertionError("V133 API response mismatch")
        if error.headers.get("Access-Control-Allow-Origin") != "https://ikst2512-eng.github.io":
            raise AssertionError("V133 API lacks Pages CORS")
    print(json.dumps({"public_forecast_http": 200, "public_archive_http": 200,
                      "restored_scenario_api_rejects_invalid": 400,
                      "four_modes_present": True, "legacy_topn_collapsed": True,
                      "historical_not_formal": True}, sort_keys=True))

if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"PRODUCTION_SMOKE_FAILED: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise SystemExit(1)

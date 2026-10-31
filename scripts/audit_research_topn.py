"""Read-only research Top-N audit for the complete archived race schedule."""
import concurrent.futures
import json
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

BASE = "https://raw.githubusercontent.com/ikst2512-eng/boat-edge-clean/main/"
DAY = "20261031"

def read(path):
    try:
        with urlopen(BASE + path, timeout=15) as response:
            return json.load(response), None
    except HTTPError as exc:
        if exc.code == 404:
            return None, "missing"
        return None, "http_error"
    except (URLError, TimeoutError, ValueError, OSError):
        return None, "read_error"

schedule, error = read("schedule_snapshots/" + DAY + ".json")
if error or not isinstance(schedule, dict):
    raise RuntimeError("schedule unavailable: " + str(error))
codes = [DAY + str(venue["jcd"]).zfill(2) + str(race["race_no"]).zfill(2)
         for venue in schedule["venues"] for race in venue["races"]]
assert len(codes) == len(set(codes)) and len(codes) >= 100

def check(code):
    prediction, pe = read("prospective_predictions/" + code + ".json")
    result, re = read("confirmed_results/" + code + ".json")
    if pe == "read_error" or re == "read_error" or pe == "http_error" or re == "http_error":
        return code, "retrieval_error", None
    if pe or re:
        return code, ("missing_both" if pe and re else "missing_prediction" if pe else "missing_result"), None
    try:
        assert prediction["race_code"] == result["race_code"] == code
        assert prediction["formal"] is False and prediction["scoring"] is False
        assert prediction["status"] == "prospective_candidate" and result["status"] == "confirmed"
        picks = prediction["predictions"]
        assert len(picks) == len(set(picks)) == 10
        assert all(len(t.split("-")) == 3 and len(set(t.split("-"))) == 3
                   and all(n in ("1","2","3","4","5","6") for n in t.split("-")) for t in picks)
        finish = result["finish_order"]
        assert len(finish) == len(set(finish)) == 3
        assert all(type(n) is int and 1 <= n <= 6 for n in finish)
        ticket = "-".join(map(str, finish))
        return code, "matched", next((i+1 for i,t in enumerate(picks) if t == ticket), None)
    except (AssertionError, KeyError, TypeError, ValueError):
        return code, "invalid_evidence", None

with concurrent.futures.ThreadPoolExecutor(max_workers=16) as pool:
    records = sorted(pool.map(check, codes))
counts = {}
for _, state, _ in records:
    counts[state] = counts.get(state, 0) + 1
sample = counts.get("matched", 0)
print("SCHEDULE_RACES", len(codes), "RESEARCH_ONLY formal_scoring=false")
print("EVIDENCE_COUNTS", json.dumps(counts, sort_keys=True))
if sample:
    for n in (3,5,10):
        hits = sum(state=="matched" and rank is not None and rank<=n for _,state,rank in records)
        print(f"RESEARCH_ONLY_TOP{n}: {hits}/{sample} ({hits/sample:.1%}); formal_scoring=false")
for code,state,rank in records:
    if state == "matched":
        print("RACE",code,"rank",rank or "outside_top10")
if counts.get("retrieval_error"):
    raise RuntimeError("Fetch errors present; audit is incomplete, do not publish as final")

"""Production smoke test of a real previously saved race (fail closed)."""
import json
from urllib.request import Request, urlopen
from urllib.parse import urlencode

BASE = "https://boat-edge-clean.onrender.com"
PARAMS = {"hd": "20261030", "jcd": "01", "rno": "1"}
def check(endpoint):
    url = BASE + endpoint + "?" + urlencode(PARAMS)
    with urlopen(Request(url, headers={"User-Agent": "CLEAN-ARCHIVE-E2E/1.0",
                                       "Cache-Control": "no-cache"}), timeout=30) as response:
        payload = json.load(response)
        if response.status != 200:
            raise AssertionError((endpoint, response.status))
    return payload

forecast = check("/api/predictions")
assert forecast.get("status") == "research", forecast
assert forecast.get("validated") is False, forecast
assert forecast.get("formal") is False, forecast
assert forecast.get("source") == "saved_prospective_candidate", forecast
assert forecast.get("predictions") == [
    "1-2-4","1-2-3","1-3-2","1-3-5","3-1-4",
    "2-1-3","1-2-5","2-1-4","1-4-2","3-1-2"
], forecast
print(json.dumps({"endpoint": "predictions", "result": "PASS", "tickets": 10,
                  "source": forecast["source"]}, ensure_ascii=False))
result = check("/api/clean-result")
assert result.get("race_code") == "202610300101", result
assert result.get("status") == "confirmed", result
assert result.get("finish_order") == [3,1,4], result
print(json.dumps({"endpoint": "clean-result", "result": "PASS",
                  "race_code": result["race_code"]}, ensure_ascii=False))

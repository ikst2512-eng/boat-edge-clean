"""Check ACTUAL Render public HTML, not only GitHub main or a fixture."""
import re
import sys
from urllib.request import Request,urlopen

URL="https://boat-edge-clean.onrender.com/forecast"
with urlopen(Request(URL,headers={"User-Agent":"BOAT-EDGE-CLEAN-DEPLOY-AUDIT/1.0","Cache-Control":"no-cache"}),timeout=45) as resp:
    if resp.status!=200:raise SystemExit("RENDER_HTTP_"+str(resp.status))
    html=resp.read(2_000_001).decode("utf-8")
if len(html)>2_000_000:raise SystemExit("RENDER_HTML_TOO_LARGE")
checks={
    "forecast_route": 'id="forecast"' in html,
    "research_10_only": "3連単予想｜上位10点（研究・未検証）" in html,
    "race_list_in_forecast": 0<=html.find('id="forecast"')<html.find('id="resultList"')<html.find('id="resultSection"'),
    "no_old_four_mode_switch": "旧4パターンの比較検証を表示" not in html,
    "no_legacy_target": "目標的中率：本命60%" not in html,
    "no_duplicate_tabs": '<nav class="view-tabs"' not in html,
    "one_html_end": len(re.findall(r"</html>",html,re.I))==1,
    "no_raw_js_tail": re.search(r"</script>\s*</body>\s*</html>\s*$",html,re.I) is not None,
}
for key,passed in checks.items():print(("PASS" if passed else "FAIL")+" "+key)
if not all(checks.values()):sys.exit("RENDER_FORECAST_CONTRACT_FAILED")
print("PASS public Render HTML contains current forecast UI and no old markup")

# Verify the same-origin prediction route still answers on the deployed Render
# instance; an HTML-only health check cannot catch a broken prediction API.
import json
from urllib.parse import urlencode
api_url="https://boat-edge-clean.onrender.com/api/predictions?"+urlencode({"hd":"20261022","jcd":"12","rno":"1"})
with urlopen(Request(api_url,headers={"User-Agent":"BOAT-EDGE-CLEAN-DEPLOY-AUDIT/1.0","Cache-Control":"no-cache"}),timeout=45) as response:
    if response.status!=200:raise SystemExit("RENDER_PREDICTION_API_HTTP_"+str(response.status))
    payload=json.load(response)
if payload.get("ok") is not True or payload.get("status") not in ("research","unavailable"):
    raise SystemExit("RENDER_PREDICTION_API_INVALID_STATUS")
if payload["status"]=="research":
    tickets=payload.get("predictions",[])
    if len(tickets)!=10 or len(set(tickets))!=10 or payload.get("validated") is not False:
        raise SystemExit("RENDER_PREDICTION_API_INVALID_TICKETS")
print("PASS deployed same-origin prediction API schema; historical missing research is not fabricated")

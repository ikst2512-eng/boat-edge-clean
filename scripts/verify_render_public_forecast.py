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

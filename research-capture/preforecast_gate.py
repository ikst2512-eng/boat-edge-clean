"""Gate HTML evidence before *any* forecast; strict offline pure functions."""
from datetime import datetime, timedelta, timezone
import hashlib
import re

JST = timezone(timedelta(hours=9))
RESULT_MARKERS = ("払戻金", "確定結果", "着順結果")
def evaluate(*, html_bytes, race_id, cutoff_jst, received_at, content_type, source_url):
    def reject(reason):
        return {"accepted": False, "reason": reason, "forecast_generated": False, "scoring": "NOT_RUN"}
    if not re.fullmatch(r"20\d{6}(?:0[1-9]|1\d|2[0-4])(?:0[1-9]|1[0-2])", race_id):
        return reject("race_id_invalid")
    if cutoff_jst.tzinfo is None or received_at.tzinfo is None:
        return reject("timezone_missing")
    if cutoff_jst.utcoffset() != timedelta(hours=9):
        return reject("cutoff_timezone_wrong")
    if cutoff_jst.strftime("%Y%m%d") != race_id[:8]:
        return reject("race_day_mismatch")
    if not source_url.startswith("https://www.boatrace.jp/owpc/pc/race/beforeinfo?"):
        return reject("source_not_beforeinfo")
    if "html" not in content_type.lower():
        return reject("not_html")
    remaining = (cutoff_jst - received_at).total_seconds()
    if not 720 < remaining <= 1200:
        return reject("outside_predeadline_window")
    try:
        page = html_bytes.decode("utf-8", "strict")
    except UnicodeDecodeError:
        return reject("charset_unverified")
    if any(marker in page for marker in RESULT_MARKERS):
        return reject("result_related_content")
    from exhibition_gate import verify_structure
    structure = verify_structure(page)
    if not structure["six_colors_present"] or not structure["exhibition_present"]:
        return reject("incomplete_six_lane_exhibition")
    # Structure verification is not field extraction: forbid model use.
    return {"accepted":False,"reason":"numeric_fields_not_verified","source_sha256":hashlib.sha256(html_bytes).hexdigest(),"structure":structure,"forecast_generated":False,"scoring":"NOT_RUN"}

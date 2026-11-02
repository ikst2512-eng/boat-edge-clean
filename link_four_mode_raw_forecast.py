"""Read-only correspondence of frozen forecast hashes with local raw HTTP receipts."""
import json
from pathlib import Path
from audit_four_mode_raw_receipts import audit


def link_forecast(code, root, receipts):
    root, receipts = Path(root), Path(receipts)
    base = audit(receipts)
    if base["status"] != "local_integrity_verified":
        return {"status": "raw_receipts_unverified", "reason": base["status"], "formal": False}
    path = root / "four_mode_forecasts" / (code + ".json")
    if (not code.isascii() or not code.isdigit() or len(code) != 12
            or path.is_symlink() or not path.is_file() or path.stat().st_size > 30000):
        return {"status": "forecast_unavailable", "formal": False}
    try:
        forecast = json.loads(path.read_text(encoding="utf-8"))
        if forecast.get("race_code") != code:
            raise ValueError("race_mismatch")
        hashes = forecast["source_sha256"]
        manifests = [json.loads(p.read_text(encoding="utf-8")) for p in receipts.glob("*.json")]
        observed = {m["sha256"] for m in manifests}
        matches = {kind: isinstance(hashes.get(kind), str) and hashes[kind].lower() in observed
                   for kind in ("title", "race_cards")}
    except (ValueError, OSError, KeyError, TypeError):
        return {"status": "forecast_untrusted", "formal": False}
    return {"status": "both_hashes_present" if all(matches.values()) else "incomplete_source_link",
            "race_code": code, "matches": matches, "formal": False,
            "independent_source_authenticity_verified": False,
            "remote_first_seen_verified": False}

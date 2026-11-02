"""Read-only four-mode frozen-archive result comparison. NOT formal accuracy."""
import json
from datetime import datetime, timedelta
from pathlib import Path
from four_mode_archive_api import archived_four_modes, MODES

ROOT = Path(__file__).resolve().parent


def compare_race(code, root=ROOT):
    root = Path(root)
    status, archive = archived_four_modes(code, root)
    if status != 200:
        return {"race_code": code, "status": "archive_unavailable_or_invalid",
                "formal": False, "reason": archive["status"]}
    # The archive API validates format but NOT first remote receipt.
    result_path = root / "confirmed_results" / (code + ".json")
    if result_path.is_symlink() or not result_path.is_file() or result_path.stat().st_size > 20000:
        return {"race_code": code, "status": "result_unavailable",
                "formal": False}
    try:
        record = json.loads(result_path.read_text(encoding="utf-8"))
        order = record["finish_order"]
        if (record.get("race_code") != code or record.get("status") != "confirmed"
                or type(order) is not list or len(order) != 3
                or any(type(x) is not int or x not in range(1, 7) for x in order)
                or len(set(order)) != 3
                or not isinstance(record.get("source_url"), str)
                or not record["source_url"].startswith("https://")):
            raise ValueError("untrusted result")
        # Distinguish timestamps recorded in the file from independent arrival proof.
        generated = datetime.fromisoformat(archive["generated_at_jst"])
        deadline = datetime.fromisoformat(archive["deadline_jst"])
        if generated.utcoffset() != timedelta(hours=9) or deadline.utcoffset() != timedelta(hours=9):
            raise ValueError("invalid timezone")
        if deadline.strftime("%Y%m%d") != code[:8]:
            raise ValueError("deadline date mismatch")
        winning = "-".join(map(str, order))
        modes = {}
        for key in MODES:
            tickets = [row["combo"] for row in archive["modes"][key]["tickets"]]
            rank = tickets.index(winning) + 1 if winning in tickets else None
            modes[key] = {"hit": rank is not None, "ticket_count": len(tickets),
                          "winning_rank": rank,
                          "top3": rank is not None and rank <= 3,
                          "top5": rank is not None and rank <= 5,
                          "top10": rank is not None and rank <= 10}
        return {"race_code": code, "status": "historical_comparison_only",
                "winning_ticket": winning, "modes": modes,
                "formal": False, "simulated_only": True,
                "remote_first_seen_verified": False,
                "warning": "Not independently proven published before cutoff; no actual stakes or ROI."}
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return {"race_code": code, "status": "invalid_result_or_timing", "formal": False}

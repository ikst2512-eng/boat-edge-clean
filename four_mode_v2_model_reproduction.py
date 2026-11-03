"""Read-only reproduction audit for archived V2 four-mode Top3 concentration.

This verifies exact saved ticket order/rounded model scores against the
CURRENT exploratory national-win-rate-only model, without rewriting files.
It does not establish first publication, data provenance, or predictive skill.
"""
import json
import re
from collections import Counter
from pathlib import Path

from clean_four_modes import rank_modes
from research_model import probabilities
from four_mode_archive_api import archived_four_modes

ROOT = Path(__file__).resolve().parent
VERSION = "CLEAN_FOUR_MODES_V2_PROVISIONAL_UNCALIBRATED"
MODES = ("narrow", "hit", "balance", "hole")


def audit(root=ROOT):
    root = Path(root)
    directory = root / "four_mode_forecasts"
    result = {
        "status": "read_only_v2_model_reproduction",
        "formal": False,
        "independent_first_publication_verified": False,
        "model_inputs": "six_national_win_rates_only",
        "second_third_conditional_shape": "fixed_historical_index_counts",
        "valid_v2_archives": 0,
        "exact_ticket_and_probability_matches": 0,
        "mismatch_count": 0,
        "mismatch_examples": [],
        "invalid_archive_count": 0,
        "input_head_rate_max_is_boat1": 0,
        "saved_hit_top3_all_head1": 0,
        "hit_top3_signatures": {},
        "warning": "Current-model reproduction is not independent model provenance or a valid accuracy test.",
    }
    if not directory.is_dir():
        result["status"] = "no_forecast_directory"
        return result
    signatures = Counter()
    for path in sorted(directory.glob("*.json")):
        if not re.fullmatch(r"20[0-9]{10}", path.stem):
            continue
        if path.is_symlink() or path.stat().st_size > 30000:
            result["invalid_archive_count"] += 1
            continue
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(raw, dict):
                raise ValueError("invalid_archive")
        except (OSError, TypeError, ValueError):
            result["invalid_archive_count"] += 1
            continue
        if raw.get("model_version") != VERSION:
            continue
        status, archive = archived_four_modes(path.stem, root)
        if status != 200 or archive.get("model_version") != VERSION:
            result["invalid_archive_count"] += 1
            continue
        try:
            rates = raw["input_national_win_rates"]
            if not isinstance(rates, list):
                raise ValueError("invalid_rates")
            expected = rank_modes(probabilities(rates))
            stored = archive["modes"]
            matched = all(
                [(t["combo"], t["p"]) for t in stored[mode]["tickets"]]
                == [(t["combo"], t["p"]) for t in expected[mode]["tickets"]]
                for mode in MODES
            )
            top3 = [t["combo"] for t in stored["hit"]["tickets"][:3]]
            if len(top3) != 3:
                raise ValueError("missing_top3")
        except (KeyError, ValueError, TypeError, OverflowError, AssertionError):
            result["invalid_archive_count"] += 1
            continue
        result["valid_v2_archives"] += 1
        result["exact_ticket_and_probability_matches"] += int(matched)
        result["mismatch_count"] += int(not matched)
        if not matched and len(result["mismatch_examples"]) < 8:
            result["mismatch_examples"].append(path.stem)
        result["input_head_rate_max_is_boat1"] += int(
            rates[0] == max(rates))
        result["saved_hit_top3_all_head1"] += int(
            all(t[0] == "1" for t in top3))
        signatures["|".join(top3)] += 1
    result["hit_top3_signatures"] = dict(sorted(signatures.items()))
    if sum(signatures.values()) != result["valid_v2_archives"]:
        raise ValueError("signature_count_mismatch")
    return result


if __name__ == "__main__":
    print("V2_MODEL_REPRODUCTION=" + json.dumps(audit(), sort_keys=True))

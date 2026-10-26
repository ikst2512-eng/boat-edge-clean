"""Convert research snapshot to an explicitly unverified paired-comparison draft.

Never fills receipt attestations, outcomes, or independent-audit booleans.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path
from paired_compare import TICKETS, timestamp

SCOPE = "source_csv_byte_hashes_ordered_title_cards"

def draft(raw, *, filename_sha256):
    if not isinstance(raw, dict) or raw.get("status") != "research" or raw.get("validated") is not False:
        raise ValueError("not an unvalidated research snapshot")
    code = raw.get("race_code")
    if not isinstance(code, str) or not re.fullmatch(r"20[0-9]{10}", code):
        raise ValueError("bad race code")
    if raw.get("input_hash_scope") != SCOPE:
        raise ValueError("unknown source hash scope")
    def sha(value, length):
        if not isinstance(value, str) or re.fullmatch("[0-9a-f]{" + str(length) + "}", value) is None:
            raise ValueError("missing or invalid SHA")
        return value
    title = sha(raw.get("source_title_sha256"), 64)
    cards = sha(raw.get("source_cards_sha256"), 64)
    composite = hashlib.sha256((title + ":" + cards).encode("ascii")).hexdigest()
    if composite != raw.get("input_sha256"):
        raise ValueError("source hash chain mismatch")
    sha(raw.get("model_sha"), 40)
    probabilities = raw.get("probabilities")
    if not isinstance(probabilities, dict) or set(probabilities) != TICKETS:
        raise ValueError("missing 120-ticket distribution")
    if len(raw.get("predictions", [])) != 10:
        raise ValueError("missing top10")
    ordered = sorted(probabilities, key=lambda t: (-probabilities[t], t))
    if raw["predictions"] != ordered[:10]:
        raise ValueError("top10 differs from frozen probabilities")
    timestamp(raw["generated_at"])
    timestamp(raw["source_received_at"])
    timestamp(raw["cutoff_jst"])
    return {
        "race_key": f"{code[:8]}-{code[8:10]}-{int(code[10:12])}",
        "race_cutoff_safety_jst": raw["cutoff_jst"],
        "snapshot_sha256": sha(filename_sha256, 64),
        "forecast_draft": {
            "model_id": raw["model_id"],
            "model_sha": raw["model_sha"],
            "input_sha256": composite,
            "generated_at": raw["generated_at"],
            "source_received_at": raw["source_received_at"],
            "probabilities": probabilities,
            "independently_verified": False,
        },
        "ready_for_scoring": False,
        "blockers": [
            "independently verified original-byte receipt and source provenance",
            "Git first-addition commit/time and independent server receipt",
            "pre-registered paired model identities and both frozen forecasts",
            "permitted independently verified official outcome and official deadline",
        ],
    }

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("snapshot", type=Path)
    args = parser.parse_args()
    original = args.snapshot.read_bytes()
    result = draft(json.loads(original), filename_sha256=hashlib.sha256(original).hexdigest())
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()

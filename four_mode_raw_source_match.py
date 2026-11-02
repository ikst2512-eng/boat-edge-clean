"""Offline exact-byte SHA256 comparison for independently preserved sources.

Matching bytes does not prove when or where those bytes were fetched.
Never changes archived forecasts or authorizes formal performance.
"""
import argparse
import hashlib
import json
from pathlib import Path

from four_mode_archive_api import archived_four_modes


def compare_bytes(code, title_path, cards_path, root=Path(__file__).resolve().parent):
    status, archive = archived_four_modes(code, root)
    if status != 200:
        return {"status": "archive_invalid_or_missing", "formal": False}
    forecast_path = Path(root) / "four_mode_forecasts" / (code + ".json")
    record = json.loads(forecast_path.read_text(encoding="utf-8"))
    digests = record.get("source_sha256")
    if not isinstance(digests, dict):
        return {"status": "missing_recorded_digests", "formal": False}
    matches = {}
    for kind, path in (("title", title_path), ("race_cards", cards_path)):
        path = Path(path)
        expected = digests.get(kind)
        if (path.is_symlink() or not path.is_file() or path.stat().st_size > 10_000_000
                or not isinstance(expected, str) or len(expected) != 64):
            return {"status": "source_bytes_unavailable_or_invalid", "formal": False}
        observed = hashlib.sha256(path.read_bytes()).hexdigest()
        matches[kind] = observed == expected.lower()
    return {
        "status": "raw_byte_digest_match" if all(matches.values()) else "source_digest_mismatch",
        "race_code": code, "matching": matches,
        "formal": False, "remote_first_seen_verified": False,
        "source_receipt_time_independently_verified": False,
        "warning": "Exact bytes alone do not prove source origin or predeadline availability."
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("race_code")
    parser.add_argument("--title-bytes", type=Path, required=True)
    parser.add_argument("--cards-bytes", type=Path, required=True)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    print(json.dumps(compare_bytes(args.race_code, args.title_bytes, args.cards_bytes,
                                   args.root), ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()

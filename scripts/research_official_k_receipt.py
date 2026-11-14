#!/usr/bin/env python3
"""Read-only official BOAT RACE daily K archive acquisition for research.

Receipts only. Do not decode or promote files to official row reconciliation,
T-12 eligibility, forecasts, historical scores, or model adjustments.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import urllib.request
from pathlib import Path

FIRST = dt.date(2026, 8, 1)
LAST = dt.date(2026, 10, 31)
MAX_BYTES = 20 * 1024 * 1024
RESEARCH_CLASS = "official_K_download_receipt_only_not_row_reconciled_not_T12"


def archive_url(day: dt.date) -> str:
    if not FIRST <= day <= LAST:
        raise ValueError(f"date_outside_fixed_study_period:{day}")
    return ("https://www1.mbrace.or.jp/od2/K/"
            f"{day:%Y%m}/k{day:%y%m%d}.lzh")


def _is_lzh(payload: bytes) -> bool:
    # Checks only basic signature; full archive integrity needs decompression.
    return len(payload) >= 16 and bool(re.fullmatch(rb"-lh[0-9a-z]-", payload[2:7]))


def get_archive(day: dt.date, target_dir: Path, opener=urllib.request.urlopen) -> dict:
    """Fail closed on absent/changed files. Never overwrite prior archive."""
    url = archive_url(day)
    target_dir.mkdir(parents=True, exist_ok=True)
    if target_dir.is_symlink():
        raise ValueError("symlink_output_dir_forbidden")
    path = target_dir / f"k{day:%y%m%d}.lzh"
    req = urllib.request.Request(
        url, headers={"User-Agent": "boat-edge-research-official-k-receipt/1.0"})
    with opener(req, timeout=25) as response:
        status = response.getcode()
        effective_url = response.geturl()
        if status != 200:
            raise ValueError(f"official_download_http_status:{day}:{status}")
        if effective_url != url:
            raise ValueError(f"unexpected_redirect:{day}:{effective_url}")
        payload = response.read(MAX_BYTES + 1)
    if len(payload) > MAX_BYTES:
        raise ValueError(f"download_too_large:{day}")
    if not _is_lzh(payload):
        raise ValueError(f"invalid_lzh_magic_or_truncated:{day}")
    digest = hashlib.sha256(payload).hexdigest()
    if path.is_symlink():
        raise ValueError(f"symlink_archive_forbidden:{path}")
    if path.exists():
        if path.read_bytes() != payload:
            raise ValueError(f"changed_or_conflicting_existing_archive:{day}")
    else:
        with path.open("xb") as output:
            output.write(payload)
    return {
        "date": day.isoformat(), "url": url, "filename": path.name,
        "sha256": digest, "bytes": len(payload),
        "status": "downloaded_source_bytes_only_not_decompressed_or_reconciled",
    }


def collect(start: dt.date, end: dt.date, target_dir: Path,
            opener=urllib.request.urlopen) -> dict:
    archive_url(start)
    archive_url(end)
    if start > end:
        raise ValueError("invalid_date_order")
    receipts = []
    for offset in range((end - start).days + 1):
        day = start + dt.timedelta(days=offset)
        receipts.append(get_archive(day, target_dir, opener=opener))
    return {
        "schema": "BOAT_EDGE_OFFICIAL_K_RECEIPTS_V1",
        "classification": RESEARCH_CLASS,
        "official_primary_rows_decoded": 0,
        "official_primary_rows_reconciled": 0,
        "eligible_for_prediction": False,
        "date_start": start.isoformat(), "date_end": end.isoformat(),
        "receipts": receipts,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", type=dt.date.fromisoformat, required=True)
    parser.add_argument("--end", type=dt.date.fromisoformat, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    # A complete manifest is published only when every day succeeds.
    report = collect(args.start, args.end, args.output_dir)
    manifest = args.output_dir / (
        f"official_k_receipts_{args.start:%Y%m%d}_{args.end:%Y%m%d}.json")
    if manifest.is_symlink():
        raise ValueError("symlink_manifest_forbidden")
    encoded = (json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2)
               + "\n").encode("utf-8")
    if manifest.exists() and manifest.read_bytes() != encoded:
        raise ValueError("manifest_conflict_refusing_overwrite")
    if not manifest.exists():
        with manifest.open("xb") as output:
            output.write(encoded)
    print(json.dumps({
        "archive_days": len(report["receipts"]),
        "source_rows_reconciled": 0,
        "status": RESEARCH_CLASS, "manifest": str(manifest)
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()

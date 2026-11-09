#!/usr/bin/env python3
"""Explicit, single-venue research-only retrieval of a BOAT RACE diagram PNG.

Never used by production, automated polling, prediction, or T-12 collection.
A successful direct HTTPS response establishes a local network receipt only.
It does NOT certify diagram bearings, wind-arrow semantics, or forecast input.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

try:
    from scripts.research_water_diagram_byte_gate import (
        check_source_url, official_diagram_url, png_dimensions, MAX_BYTES)
except ModuleNotFoundError:
    from research_water_diagram_byte_gate import (
        check_source_url, official_diagram_url, png_dimensions, MAX_BYTES)

SCHEMA = "BOAT_EDGE_OFFICIAL_WATER_DIAGRAM_DIRECT_HTTP_RECEIPT_V1"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


def fetch_once(jcd: str, *, opener=None, timestamp=None, timeout: float = 15.0):
    """Fetch one canonical URL. opener injection is for OFFLINE unit tests only."""
    url = official_diagram_url(jcd)
    requester = opener or urllib.request.urlopen
    clock = timestamp or utc_now
    start = clock()
    request = urllib.request.Request(
        url, headers={"Accept": "image/png", "Accept-Encoding": "identity",
                      "Cache-Control": "no-cache", "User-Agent": "BOAT-EDGE-research-original-evidence/1.0"})
    with requester(request, timeout=timeout) as response:
        status = response.status
        final_url = response.geturl()
        headers = response.headers
        content_type = (headers.get("Content-Type") or "").split(";", 1)[0].strip().lower()
        encoding = (headers.get("Content-Encoding") or "identity").strip().lower()
        length = headers.get("Content-Length")
        if status != 200:
            raise ValueError("http_status_not_200:" + str(status))
        check_source_url(jcd, final_url)
        if content_type != "image/png":
            raise ValueError("unexpected_content_type:" + content_type)
        if encoding != "identity":
            raise ValueError("compressed_or_transformed_http_body")
        if length is not None and (not re.fullmatch(r"[0-9]+", str(length)) or int(length) > MAX_BYTES):
            raise ValueError("invalid_content_length")
        raw = response.read(MAX_BYTES + 1)
        if len(raw) > MAX_BYTES or (length is not None and int(length) != len(raw)):
            raise ValueError("oversize_or_incomplete_http_body")
        width, height = png_dimensions(raw)
        finish = clock()
        receipt = {
            "schema": SCHEMA,
            "jcd": jcd,
            "requested_url": url,
            "final_url": final_url,
            "http_status": status,
            "content_type": content_type,
            "content_encoding": encoding,
            "http_date_header": headers.get("Date"),
            "http_etag_header": headers.get("ETag"),
            "http_last_modified_header": headers.get("Last-Modified"),
            "response_started_utc": start,
            "response_finished_utc": finish,
            "png_sha256": hashlib.sha256(raw).hexdigest(),
            "png_bytes": len(raw),
            "png_dimensions": [width, height],
            "http_200_final_url_and_png_integrity_passed": True,
            "source_attested_by_independent_service": False,
            "diagram_bearing_independently_verified": False,
            "same_race_wind_arrow_original_verified": False,
            "t12_beforeinfo_source_verified": False,
            "production_wind_use_authorized": False,
            "note": "This HTTPS receipt establishes only response bytes seen by this research client; not compass/arrow/T-12 certification."
        }
    return raw, receipt


def write_bundle(output_root: Path, raw: bytes, receipt: dict) -> Path:
    """Never overwrite an earlier receipt, and write COMPLETE only at the end."""
    if output_root.is_symlink() or not output_root.is_dir():
        raise ValueError("output_root_must_be_existing_real_directory")
    if not isinstance(receipt, dict) or receipt.get("schema") != SCHEMA:
        raise ValueError("untrusted_receipt_schema")
    if hashlib.sha256(raw).hexdigest() != receipt.get("png_sha256"):
        raise ValueError("receipt_not_matching_raw_file")
    # A self-consistent digest is not proof that the bytes are a PNG. The
    # public write_bundle helper must repeat all essential source checks.
    dimensions = png_dimensions(raw)
    if receipt.get("png_bytes") != len(raw) or receipt.get("png_dimensions") != list(dimensions):
        raise ValueError("receipt_length_or_png_dimensions_inconsistent")
    if receipt.get("content_type") != "image/png" or receipt.get("content_encoding") != "identity":
        raise ValueError("receipt_content_type_or_encoding_inconsistent")
    check_source_url(receipt.get("jcd"), receipt.get("final_url"))
    forbidden_true = (
        "source_attested_by_independent_service", "diagram_bearing_independently_verified",
        "same_race_wind_arrow_original_verified", "t12_beforeinfo_source_verified",
        "production_wind_use_authorized")
    if (receipt.get("http_status") != 200
            or receipt.get("http_200_final_url_and_png_integrity_passed") is not True
            or any(receipt.get(k) is not False for k in forbidden_true)):
        raise ValueError("false_success_or_production_flag")
    if receipt.get("requested_url") != official_diagram_url(receipt["jcd"]):
        raise ValueError("original_request_url_mismatch")
    stamp_raw = receipt.get("response_finished_utc")
    if not isinstance(stamp_raw, str) or not re.fullmatch(
            r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?\+00:00", stamp_raw):
        raise ValueError("untrusted_receipt_timestamp")
    stamp = stamp_raw.replace(":", "").replace("-", "").replace(".", "")
    folder = output_root / f"jcd_{receipt['jcd']}_{stamp}_{receipt['png_sha256'][:12]}"
    folder.mkdir(mode=0o700, exist_ok=False)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    for name, data in (("original_response.png", raw),
                       ("receipt.json", (json.dumps(receipt, ensure_ascii=False, indent=2) + "\n").encode())):
        fd = os.open(folder / name, flags, 0o600)
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
    fd = os.open(folder / "COMPLETE", flags, 0o600)
    with os.fdopen(fd, "wb") as f:
        f.write(b"response files complete; independent diagram review still needed\n")
    return folder


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--jcd", required=True, help="Exactly one venue, 01..24")
    p.add_argument("--output-root", type=Path, required=True, help="Existing non-symlink research directory")
    p.add_argument("--timeout", type=float, default=15.0)
    args = p.parse_args()
    if not 1 <= args.timeout <= 30:
        p.error("timeout must be 1..30 seconds")
    try:
        raw, receipt = fetch_once(args.jcd, timeout=args.timeout)
        target = write_bundle(args.output_root, raw, receipt)
    except Exception as exc:
        # Never report a network error as a successful official HTTP status.
        raise SystemExit("NO_RECEIPT: " + type(exc).__name__ + ": " + str(exc)) from exc
    print(json.dumps({"result": "raw_response_saved_for_manual_audit",
                      "bundle": str(target), "sha256": receipt["png_sha256"],
                      "official_heading_certified": False, "T12_eligible": False}, ensure_ascii=False))


if __name__ == "__main__":
    main()

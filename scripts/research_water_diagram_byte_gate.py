#!/usr/bin/env python3
"""Offline, research-only PNG-byte receipt for one BOAT RACE water diagram.

This gate never downloads a URL or certifies that user-supplied bytes came
from it. It cannot authorize venue bearing, same-race arrows, or T-12 weather.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import struct
import zlib
from pathlib import Path

PNG_SIG = b"\x89PNG\r\n\x1a\n"
MAX_BYTES = 5_000_000
MAX_CHUNKS = 4096
JCD = frozenset(f"{i:02d}" for i in range(1, 25))
SCHEMA = "BOAT_EDGE_OFFICIAL_WATER_DIAGRAM_BYTE_RECEIPT_V1"


def official_diagram_url(jcd: str) -> str:
    if type(jcd) is not str or jcd not in JCD:
        raise ValueError("invalid_jcd")
    return f"https://www.boatrace.jp/static_extra/pc/images/img_water1_{jcd}.png"


def check_source_url(jcd: str, url: str) -> None:
    if type(url) is not str or url not in (
        official_diagram_url(jcd), official_diagram_url(jcd).replace("www.boatrace.jp", "boatrace.jp")):
        raise ValueError("noncanonical_or_unproven_source_url")


def png_dimensions(data: bytes) -> tuple[int, int]:
    """Reject mislabeled HTML, corruption, extra bytes and unbounded chunks."""
    if not isinstance(data, bytes) or len(data) < 60 or len(data) > MAX_BYTES or not data.startswith(PNG_SIG):
        raise ValueError("not_sized_png_bytes")
    offset, chunks, seen_ihdr, seen_idat, seen_iend = 8, 0, False, False, False
    width = height = 0
    while offset < len(data):
        chunks += 1
        if chunks > MAX_CHUNKS or offset + 12 > len(data):
            raise ValueError("bad_png_chunk_count_or_bounds")
        size = struct.unpack_from(">I", data, offset)[0]
        end = offset + 12 + size
        if size > MAX_BYTES or end > len(data):
            raise ValueError("truncated_or_oversized_png_chunk")
        kind = data[offset + 4:offset + 8]
        body = data[offset + 8:offset + 8 + size]
        crc = struct.unpack_from(">I", data, offset + 8 + size)[0]
        if zlib.crc32(kind + body) & 0xffffffff != crc:
            raise ValueError("invalid_png_crc")
        if not re.fullmatch(rb"[A-Za-z]{4}", kind):
            raise ValueError("bad_png_chunk_name")
        if chunks == 1:
            if kind != b"IHDR" or size != 13:
                raise ValueError("png_missing_first_ihdr")
            width, height, depth, color, compression, filtering, interlace = struct.unpack(">IIBBBBB", body)
            if not 1 <= width <= 12000 or not 1 <= height <= 12000 or depth not in (1, 2, 4, 8, 16) or color not in (0, 2, 3, 4, 6) or compression != 0 or filtering != 0 or interlace not in (0, 1):
                raise ValueError("invalid_png_ihdr")
            seen_ihdr = True
        elif kind == b"IHDR":
            raise ValueError("duplicate_ihdr")
        elif kind == b"IDAT":
            seen_idat = True
        elif kind == b"IEND":
            if size != 0 or end != len(data):
                raise ValueError("invalid_png_iend_or_trailing_data")
            seen_iend = True
            break
        offset = end
    if not (seen_ihdr and seen_idat and seen_iend):
        raise ValueError("png_missing_required_chunks")
    return width, height


def make_receipt(jcd: str, source_url: str, raw: bytes, *, claimed_page_revision: str | None = None) -> dict:
    check_source_url(jcd, source_url)
    width, height = png_dimensions(raw)
    if claimed_page_revision is not None and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", claimed_page_revision):
        raise ValueError("invalid_page_revision_format")
    return {
        "schema": SCHEMA,
        "jcd": jcd,
        "claimed_official_image_url": source_url,
        "claimed_page_revision": claimed_page_revision,
        "png_raw_sha256": hashlib.sha256(raw).hexdigest(),
        "png_raw_length": len(raw),
        "png_dimensions_px": {"width": width, "height": height},
        "file_integrity_verified": True,
        "official_http_original_response_proven": False,
        "source_url_claim_cryptographically_verified": False,
        "official_diagram_north_axis_second_review_passed": False,
        "same_race_official_arrow_original_sha_verified": False,
        "t12_weather_input_verified": False,
        "approved_relative_wind_direction": None,
        "production_transform_authorized": False,
        "explanation": "SHA proves bytes of locally supplied file only; original official HTTP receipt, North arrow and T-12 evidence are separately unverified.",
    }


def receipt_for_file(jcd: str, source_url: str, png_path: Path, *, claimed_page_revision: str | None = None) -> dict:
    if png_path.is_symlink():
        raise ValueError("symlink_png_refused")
    st = png_path.stat()
    if not stat.S_ISREG(st.st_mode) or st.st_size > MAX_BYTES:
        raise ValueError("not_regular_or_oversized_file")
    raw = png_path.read_bytes()
    return make_receipt(jcd, source_url, raw, claimed_page_revision=claimed_page_revision)


def verify_receipt_against_bytes(receipt: dict, raw: bytes) -> None:
    if not isinstance(receipt, dict) or receipt.get("schema") != SCHEMA:
        raise ValueError("receipt_schema_wrong")
    if receipt != make_receipt(receipt["jcd"], receipt["claimed_official_image_url"], raw,
            claimed_page_revision=receipt.get("claimed_page_revision")):
        raise ValueError("receipt_mismatch_or_false_certification")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--jcd", required=True)
    parser.add_argument("--png", required=True, type=Path)
    parser.add_argument("--source-url", required=True)
    parser.add_argument("--claimed-page-revision")
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    if args.out.exists() or args.out.is_symlink():
        raise SystemExit("refuse_overwrite_existing_receipt")
    receipt = receipt_for_file(args.jcd, args.source_url, args.png,
                              claimed_page_revision=args.claimed_page_revision)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive create; output is research-only, not a production configuration.
    fd = os.open(args.out, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(receipt, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(json.dumps({"jcd": args.jcd, "status": "local_bytes_only", "sha256": receipt["png_raw_sha256"],
                      "official_source_verified": False, "T12_eligible": False}))


if __name__ == "__main__":
    main()

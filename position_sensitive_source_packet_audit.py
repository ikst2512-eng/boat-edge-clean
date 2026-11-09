"""Read-only, byte-consistency check for candidate pre-race source packets.

Never authenticates an alleged official origin or first remote receipt; a caller
could supply fake bytes and timestamps. No network, no results, no prediction.
"""
from datetime import datetime, timedelta
from hashlib import sha256
from urllib.parse import urlsplit, parse_qs
import re

KINDS = ("beforeinfo", "odds3t", "weather", "racecard")
ENDPOINTS = {
    "beforeinfo": "/owpc/pc/race/beforeinfo",
    "odds3t": "/owpc/pc/race/odds3t",
    "weather": "/owpc/pc/race/beforeinfo",
    "racecard": "/owpc/pc/race/racelist",
}
JST = timedelta(hours=9)
CODE = re.compile(r"20[0-9]{10}\Z")
SHA = re.compile(r"[a-f0-9]{64}\Z")
MAX_BYTES = 4_000_000
MAX_SKEW_DAYS = 1


def _clock(value, label):
    if type(value) is not str:
        raise ValueError("invalid_" + label)
    try:
        dt = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("invalid_" + label) from exc
    if dt.utcoffset() != JST or dt.tzinfo is None:
        raise ValueError("must_have_jst_offset_" + label)
    return dt


def _identity(raw_url, kind, code):
    if type(raw_url) is not str or len(raw_url) > 500 or any(c.isspace() for c in raw_url):
        raise ValueError("invalid_source_url")
    url = urlsplit(raw_url)
    if (url.scheme != "https" or url.hostname != "www.boatrace.jp"
            or url.username is not None or url.password is not None or url.port is not None
            or url.fragment or url.path != ENDPOINTS[kind]):
        raise ValueError("unapproved_source_url_or_endpoint")
    q = parse_qs(url.query, keep_blank_values=True, strict_parsing=True)
    if set(q) != {"hd", "jcd", "rno"} or any(len(values) != 1 for values in q.values()):
        raise ValueError("invalid_source_race_query")
    hd, jcd, rno = q["hd"][0], q["jcd"][0], q["rno"][0]
    if not (re.fullmatch(r"[0-9]{8}", hd) and re.fullmatch(r"[0-9]{1,2}", jcd)
            and re.fullmatch(r"[0-9]{1,2}", rno)
            and 1 <= int(jcd) <= 24 and 1 <= int(rno) <= 12
            and hd + f"{int(jcd):02d}{int(rno):02d}" == code):
        raise ValueError("source_race_mismatch")


def _one(kind, data, code, cutoff, day):
    if type(data) is not dict or set(data) != {
            "url", "raw_bytes", "sha256", "received_at_jst", "race_code"}:
        raise ValueError("incomplete_packet_item")
    if data["race_code"] != code:
        raise ValueError("packet_race_identity_mismatch")
    _identity(data["url"], kind, code)
    raw = data["raw_bytes"]
    if type(raw) is not bytes or not 0 < len(raw) <= MAX_BYTES:
        raise ValueError("unsafe_source_body")
    digest = sha256(raw).hexdigest()
    if type(data["sha256"]) is not str or not SHA.fullmatch(data["sha256"]) or digest != data["sha256"]:
        raise ValueError("raw_body_sha256_mismatch")
    seen = _clock(data["received_at_jst"], "source_received")
    if not day <= seen < cutoff:
        raise ValueError("source_not_pre_t12_or_wrong_day")
    return {
        "raw_bytes_sha256_self_consistent": True,
        "observed_url_host_and_race_parameters_consistent": True,
        "claim_time_before_t12": True,
        "raw_length": len(raw),
        "claimed_received_at_jst": seen.isoformat(),
        "sha256": digest,
        # This is NOT source authentication: a URL string proves no origin.
        "independently_authenticated_official_source": False,
        "source_body_semantics_parsed_verified": False,
        "first_remote_receipt_verified": False,
    }


def audit_packet(packet):
    """Always report incompleteness rather than backfill absent official records.

    A complete packet is just locally self-consistent, NOT formally eligible.
    """
    if type(packet) is not dict or set(packet) != {"race_code", "deadline_jst", "snapshots"}:
        raise ValueError("unapproved_or_outcome_contaminated_packet")
    code = packet["race_code"]
    if type(code) is not str or not CODE.fullmatch(code):
        raise ValueError("invalid_race_code")
    deadline = _clock(packet["deadline_jst"], "deadline")
    try:
        date = datetime.strptime(code[:8], "%Y%m%d").replace(tzinfo=deadline.tzinfo)
    except ValueError as exc:
        raise ValueError("invalid_race_date") from exc
    if deadline.date() != date.date():
        raise ValueError("deadline_race_day_mismatch")
    cutoff = deadline - timedelta(minutes=12)
    if cutoff <= date:
        raise ValueError("invalid_t12_cutoff")
    snapshots = packet["snapshots"]
    if type(snapshots) is not dict or set(snapshots) - set(KINDS):
        raise ValueError("invalid_source_kinds")
    present, missing = {}, {}
    for kind in KINDS:
        if kind not in snapshots:
            missing[kind] = "source_missing"
            continue
        try:
            present[kind] = _one(kind, snapshots[kind], code, cutoff, date)
        except (ValueError, TypeError, OverflowError) as exc:
            missing[kind] = str(exc)
    return {
        "race_code": code,
        "status": "untrusted_claimed_original_bytes_pre_t12_inventory_only",
        "self_consistent_kind_count": len(present),
        "required_kind_count": len(KINDS),
        "self_consistent_kinds": sorted(present),
        "missing_or_invalid_kinds": missing,
        "per_kind": present,
        "all_raw_source_kinds_locally_self_consistent": len(present) == len(KINDS),
        "parsed_six_boats_verified": False,
        "parsed_odds120_verified": False,
        "parsed_official_weather_verified": False,
        "independent_official_origin_verified": False,
        "independent_first_remote_receipt_verified": False,
        "complete_run_attempt_inventory_verified": False,
        "independently_eligible_candidate": False,
        "formal": False,
        "model_improvement_proven": False,
        "promotion_allowed": False,
        "production_changed": False,
        "warning": (
            "Self-supplied bytes and timestamps cannot prove official delivery, "
            "semantic content, six/120 values, or independent first remote receipt. "
            "This gate is not a forecast and never authorizes model promotion."
        ),
    }

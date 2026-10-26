"""Read verified PR15 immutable receipt before bridging research observations.

Requires PR15's read_raw_receipt injected by the integration caller. Never
treats a free-standing dict as proof of source authenticity.
"""
from hashlib import sha256
from clean_research_provenance_bridge import compare_capture_identity


def bridge_saved_official_receipt(racelist, parsed_beforeinfo, *, directory, deadline, read_raw_receipt, reparse_raw=None):
    digest = parsed_beforeinfo.get("raw_sha256") if isinstance(parsed_beforeinfo, dict) else None
    race_key = parsed_beforeinfo.get("race_key") if isinstance(parsed_beforeinfo, dict) else None
    if not isinstance(digest, str) or not isinstance(race_key, str):
        raise ValueError("missing parser provenance")
    receipt, raw = read_raw_receipt(directory, race_key, digest, deadline=deadline)
    if not isinstance(receipt, dict) or not isinstance(raw, bytes):
        raise ValueError("invalid verified readback")
    if sha256(raw).hexdigest() != digest or receipt.get("bytes") != len(raw):
        raise ValueError("readback bytes mismatch")
    if reparse_raw is not None:
        reconstructed = reparse_raw(raw)
        if (not isinstance(reconstructed, dict)
                or reconstructed.get('status') != 'research_unverified'
                or reconstructed.get('start_exhibition') != parsed_beforeinfo.get('start_exhibition')):
            raise ValueError('saved research parser output does not match verified raw bytes')
    return compare_capture_identity(racelist, parsed_beforeinfo, deadline=deadline,
                                    official_receipt=receipt)

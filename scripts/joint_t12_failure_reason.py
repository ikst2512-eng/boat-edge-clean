"""Conservative failure categories for research-only official T-12 receipts.

Classification is diagnostic only; it never authorizes retries or predictions.
"""
def classify(status, error=None):
    status = str(status or "")
    error = str(error or "")
    if status in ("beforeinfo_after_t12", "insufficient_time_to_fetch_odds"):
        return "cutoff"
    if status == "beforeinfo_failed_or_deadline_missing":
        return classify("source_failure", error)
    if status in ("odds_failed", "official_beforeinfo_capture_exception",
                  "official_odds_capture_exception", "official_json_probe_failed",
                  "official_odds_probe_failed", "source_failure"):
        if error in ("TimeoutError", "socket.timeout", "URLError", "ConnectionError",
                     "ConnectionResetError", "ConnectionRefusedError",
                     "BrokenPipeError"):
            return "transport"
        if error == "HTTPError":
            # HTTP status and publication evidence are required before calling
            # a source 'not published' or declaring an upstream outage.
            return "http_unresolved"
        if error in ("FileExistsError", "PermissionError", "OSError"):
            return "storage_or_io_unresolved"
        return "unknown"
    if status == "joint_original_audit_failed":
        return "audit_invalid"
    return "unknown"

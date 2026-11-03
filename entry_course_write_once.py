"""Exclusive local freeze for pre-cutoff course research captures.

An ephemeral filesystem is NOT durable independent archival evidence.
A separate authenticated Git/object-store preservation step remains necessary.
"""
from datetime import datetime, timezone
from pathlib import Path
import json
import os
import re


def freeze_capture(candidate, directory, *, clock=None):
    if not isinstance(candidate,dict) or candidate.get("schema") not in ("entry-course-prospective-capture-v1","entry-course-late-preview-study-v1"):
        raise ValueError("invalid_candidate_capture")
    code=candidate.get("race_code")
    if not isinstance(code,str) or not re.fullmatch(r"20\d{10}",code):
        raise ValueError("invalid_candidate_race")
    try:
        cutoff=datetime.fromisoformat(candidate["cutoff_at"])
        frozen=datetime.fromisoformat(candidate["frozen_at"])
    except (KeyError,ValueError,TypeError):
        raise ValueError("invalid_capture_clock")
    actual=(clock or (lambda:datetime.now(timezone.utc)))()
    if (cutoff.utcoffset() is None or frozen.utcoffset() is None
            or actual.utcoffset() is None or frozen>actual or actual>cutoff):
        raise ValueError("capture_write_after_cutoff")
    root=Path(directory)
    if root.is_symlink():
        raise ValueError("capture_directory_symlink")
    root.mkdir(parents=True,exist_ok=True)
    if root.is_symlink():
        raise ValueError("capture_directory_symlink")
    path=root/(code+".json")
    record=dict(candidate,write_received_at=actual.isoformat(),
                local_snapshot_only=True,independently_archived=False)
    data=json.dumps(record,ensure_ascii=False,sort_keys=True)+"\n"
    with path.open("x",encoding="utf-8") as out:
        out.write(data)
        out.flush()
        os.fsync(out.fileno())
    return path

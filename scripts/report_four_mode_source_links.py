"""Link raw source receipts only for forecasts added by this capture publication.

Checking every same-day archive from checkout creates false missing-hash counts
when a later no-op capture has no reason to preserve the original run's receipts.
This is local correspondence only, NOT independent source or remote-first-seen proof.
"""
import json
import re
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

from link_four_mode_raw_forecast import link_forecast

SHA = re.compile(r"[a-f0-9]{40}\Z")
FORECAST = re.compile(r"four_mode_forecasts/(20[0-9]{10})\.json\Z")
JST = timezone(timedelta(hours=9))


def added_in_this_publication(root, *, git=None):
    root = Path(root)
    target = root / "four-mode-evidence/publication.json"
    if not target.exists():
        return "no_publication_evidence", []
    if target.is_symlink() or not target.is_file() or target.stat().st_size > 10000:
        raise ValueError("invalid publication file")
    try:
        publication = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError) as exc:
        raise ValueError("invalid publication JSON") from exc
    if not isinstance(publication, dict):
        raise ValueError("invalid publication object")
    if publication.get("outcome") in ("no_eligible_candidates", "failed"):
        return "no_new_publication", []
    if publication.get("outcome") != "pushed_to_main":
        raise ValueError("unknown publication outcome")
    sha = publication.get("commit_sha")
    count = publication.get("added_forecasts")
    if not isinstance(sha, str) or not SHA.fullmatch(sha):
        raise ValueError("invalid publication sha")
    if type(count) is not int or not 0 < count <= 500:
        raise ValueError("invalid publication count")
    git = git or (lambda args: subprocess.check_output(
        ["git", *args], text=True, cwd=root).strip())
    if git(["rev-parse", "HEAD"]) != sha:
        raise ValueError("publication commit differs from HEAD")
    paths = git(["diff-tree", "--no-commit-id", "--name-only", "--diff-filter=A",
                 "-r", sha, "--", "four_mode_forecasts/"]).splitlines()
    if len(paths) != count or any(not FORECAST.fullmatch(path) for path in paths):
        raise ValueError("published first-add archive mismatch")
    return "published_local_first_add", paths


def report(root=".", *, now=None, git=None, link=link_forecast):
    root = Path(root)
    now = now or datetime.now(JST)
    day = now.astimezone(JST).strftime("%Y%m%d")
    try:
        status, paths = added_in_this_publication(root, git=git)
        if any(not Path(path).stem.startswith(day) for path in paths):
            raise ValueError("publication date mismatch")
    except (ValueError, OSError, subprocess.SubprocessError) as exc:
        status, paths = "invalid_publication_evidence", []
        issue = str(exc)[:100]
    else:
        issue = None
    receipts = root / "four-mode-evidence/raw-sources"
    rows = [link(Path(path).stem, root, receipts) for path in paths]
    matched = sum(row.get("status") == "both_hashes_present" for row in rows)
    result = {"schema": "FOUR_MODE_LOCAL_SOURCE_LINK_REPORT_V2",
              "day_jst": day, "scope": "only_new_archives_in_this_run_publication",
              "publication_scope_status": status,
              "checked": len(rows) if status != "invalid_publication_evidence" else None,
              "hashes_present": matched if status != "invalid_publication_evidence" else None,
              "formal": False, "remote_first_seen_verified": False,
              "rows": rows}
    if issue is not None:
        result["error"] = issue
    return result


if __name__ == "__main__":
    output = report()
    destination = Path("four-mode-evidence/source-links.json")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(output, ensure_ascii=False, sort_keys=True) + "\n",
                           encoding="utf-8")
    print("FOUR_MODE_SOURCE_LINKS=" + json.dumps({
        "checked": output["checked"], "hashes_present": output["hashes_present"],
        "status": output["publication_scope_status"], "formal": False}, sort_keys=True))

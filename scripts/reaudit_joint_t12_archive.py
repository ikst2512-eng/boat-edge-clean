"""Independently re-audit original official sources inside a T12 artifact ZIP."""
import io
import json
import tempfile
import zipfile
from pathlib import Path, PurePosixPath
from scripts.audit_joint_official_receipts import audit_pair


def reaudit_archive(raw, run_id):
    if not isinstance(run_id, int) or isinstance(run_id, bool) or run_id <= 0:
        raise ValueError("invalid run ID")
    with zipfile.ZipFile(io.BytesIO(raw)) as archive, tempfile.TemporaryDirectory() as temp:
        files = archive.infolist()
        if len(files) > 10000 or sum(x.file_size for x in files) > 100_000_000:
            raise ValueError("unsafe archive size")
        seen = set()
        for entry in files:
            path = PurePosixPath(entry.filename)
            if path.is_absolute() or ".." in path.parts or entry.file_size > 2_000_000:
                raise ValueError("unsafe archive entry")
            if entry.filename in seen:
                raise ValueError("duplicate archive entry")
            seen.add(entry.filename)
        reports = sorted(name for name in seen if name.startswith("reports/joint_") and name.endswith(".json"))
        outcomes = []
        for name in reports:
            attempt_str = name[len("reports/joint_"):-len(".json")]
            if attempt_str not in tuple(str(n) for n in range(1, 7)):
                raise ValueError("invalid attempt filename")
            attempt = int(attempt_str)
            item = json.loads(archive.read(name))
            if not isinstance(item, dict) or item.get("attempt") != attempt or type(item.get("attempt")) is not int:
                raise ValueError("invalid attempt report identity")
            race = item.get("race_code")
            if type(race) is not str or len(race) != 12 or not race.isascii() or not race.isdigit():
                raise ValueError("invalid race")
            prefix = f"evidence/observations/"
            before = prefix + f"before{run_id}_{attempt}/{race[:8]}/{race}/"
            odds = prefix + f"odds{run_id}_{attempt}/{race[:8]}/{race}/"
            necessary = (before + "beforeinfo.json", before + "manifest.json",
                         odds + "original.html", odds + "manifest.json")
            verified = False
            reason = "source_originals_missing"
            if all(key in seen for key in necessary):
                try:
                    for key in necessary:
                        dest = Path(temp) / key
                        dest.parent.mkdir(parents=True, exist_ok=True)
                        dest.write_bytes(archive.read(key))
                    result = audit_pair(Path(temp) / before, Path(temp) / odds)
                    if result["race_code"] != race:
                        raise ValueError("race mismatch after audit")
                    verified = result["both_complete_before_t12"] is True
                    reason = "source_pair_verified" if verified else "source_pair_not_complete"
                except (ValueError, KeyError, TypeError, UnicodeError, OSError, json.JSONDecodeError):
                    reason = "source_audit_failed"
            outcomes.append({"attempt": attempt, "race_code": race,
                             "reported_success": item.get("both_complete_before_t12") is True,
                             "originals_verified_complete": verified, "status": reason})
        return {"run_id": run_id, "attempt_reports": len(outcomes),
                "independently_verified_complete_pairs": sum(x["originals_verified_complete"] for x in outcomes),
                "attempts": outcomes,
                "scope": "original archive contents re-audited; research only, no forecast authorization"}

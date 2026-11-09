"""Read-only pinned Git object audit of ALL workflow YAMLs in a repository.

Checks an immutable main commit via local Git HEAD and ls-tree; every workflow
blob is rehashed using actual Git blob object format. The Git tree inventory
is exhaustive, but NOT an exhaustive executable program call graph or real
schedule execution, nor proof no indirect official racelist capture exists.
"""
import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

PINNED = "4bd080ad77778053575cf497c8a6b85b959ce173"
SCHEMA = "T12_ALL_PINNED_MAIN_WORKFLOW_SOURCES_V1"
PATH = re.compile(r"\.github/workflows/[a-zA-Z0-9_.-]+\.ya?ml\Z")
SHA40 = re.compile(r"[a-f0-9]{40}\Z")
EVENT = re.compile(r"\s{2}([a-z][a-z_]*):(?:\s.*)?\Z")
ON = re.compile(r"""(?:on|'on'|"on"):\s*(.*?)\s*\Z""")
TRIAD_EXEC = re.compile(
    r"(?:scripts\.observe_three_official_t12_originals|"
    r"scripts/observe_three_official_t12_originals\.py|"
    r"scripts\.capture_official_racelist_receipt|"
    r"scripts/capture_official_racelist_receipt\.py|"
    r"from\s+scripts\.capture_official_racelist_receipt\s+import)"
)


def _events(value):
    """Parse top-level Actions on block; unknown forms remain unclassified."""
    lines = value.splitlines()
    on_lines = [(i, ON.fullmatch(s)) for i, s in enumerate(lines)
                if ON.fullmatch(s)]
    if len(on_lines) != 1:
        return None
    start, match = on_lines[0]
    inline = match.group(1).split("#", 1)[0].strip()
    if inline:
        if re.fullmatch(r"[a-z][a-z_]*", inline):
            return [inline]
        if re.fullmatch(r"\[\s*[a-z_]+(?:\s*,\s*[a-z_]+)*\s*\]", inline):
            return re.findall(r"[a-z_]+", inline)
        return None
    found = []
    for line in lines[start+1:]:
        if line and not line[0].isspace() and not line.lstrip().startswith("#"):
            break
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if line.startswith("  ") and not line.startswith("   "):
            match_event = EVENT.fullmatch(line)
            if match_event is None or match_event.group(1) in found:
                return None
            found.append(match_event.group(1))
    return found or None


def inspect(files, *, pinned=PINNED):
    if not isinstance(files, dict) or not files:
        raise ValueError("workflow tree not available")
    if not isinstance(pinned, str) or not SHA40.fullmatch(pinned):
        raise ValueError("nonimmutable workflow tree")
    entries = []
    for name, raw in sorted(files.items()):
        if not isinstance(name, str) or not PATH.fullmatch(name):
            raise ValueError("untrusted Git workflow tree path")
        if not isinstance(raw, bytes) or not 0 < len(raw) <= 150_000:
            raise ValueError("Git workflow file invalid")
        try:
            source = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ValueError("non UTF-8 workflow source") from exc
        events = _events(source)
        declared_scheduled = events is not None and "schedule" in events
        executable_mentions = [
            line.strip() for line in source.splitlines()
            if TRIAD_EXEC.search(line)
            and not line.lstrip().startswith("#")
            and not line.strip().startswith("- 'scripts/")
        ]
        entries.append({
            "path": name,
            "git_blob_sha1": hashlib.sha1(
                b"blob " + str(len(raw)).encode() + b"\0" + raw
            ).hexdigest(),
            "trigger_classified": events is not None,
            "declared_events": events,
            "schedule_event_declared": declared_scheduled,
            "triad_or_racelist_executable_text_references": executable_mentions,
        })
    scheduled = [row for row in entries if row["schedule_event_declared"]]
    direct = [row for row in scheduled
              if row["triad_or_racelist_executable_text_references"]]
    unknown = [row["path"] for row in entries if not row["trigger_classified"]]
    return {
        "schema": SCHEMA,
        "pinned_main_commit": pinned,
        "git_workflow_tree_exhaustively_enumerated": True,
        "github_workflow_files_examined": len(entries),
        "workflows_with_classifiable_on_declaration": len(entries) - len(unknown),
        "unclassified_workflow_on_declarations": unknown,
        "workflows_with_declared_schedule_event": len(scheduled),
        "declared_scheduled_workflow_paths": [row["path"] for row in scheduled],
        "scheduled_workflows_with_direct_racelist_or_tri_capture_text": [
            {"path": row["path"],
             "matching_source_lines": row["triad_or_racelist_executable_text_references"]}
            for row in direct],
        "direct_executable_reference_match_count": len(direct),
        "all_workflow_blob_sha1_verified_against_pinned_git_tree": True,
        "files": entries,
        "absence_of_any_indirect_source_capture_proven": False,
        "workflow_scheduling_executions_proven": False,
        "official_three_originals_replayed_by_this_audit": False,
        "forecast_model_consumption_proven": False,
        "first_forecast_remote_git_acceptance_proven": False,
        "new_formal_certifications": 0,
        "formal_accuracy_denominator": None,
        "formal": False,
        "t12_eligible": False,
        "accuracy_scoring_allowed": False,
        "note": (
            "Exhaustive ONLY for tracked YAML workflow blobs in this immutable "
            "Git tree; pattern checks do not execute jobs, resolve shell "
            "programs, transitive imports, external actions or reusable workflows. "
            "Unclassified event blocks explicitly prevent universal negative claims."
        ),
    }


def _git(directory, *cmd):
    result = subprocess.run(
        ["git", "-C", str(directory), *cmd],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30,
        check=False)
    if result.returncode != 0:
        raise ValueError("Git pinned-source read unavailable")
    return result.stdout


def scan(directory, *, pinned=PINNED):
    root = Path(directory)
    if not root.is_dir() or root.is_symlink():
        raise ValueError("pinned Git checkout unavailable")
    if _git(root, "rev-parse", "HEAD").decode().strip() != pinned:
        raise ValueError("Git checkout is not the pinned main commit")
    tree = _git(root, "ls-tree", "-rz", pinned, "--", ".github/workflows")
    files = {}
    shas = {}
    for item in tree.split(b"\0"):
        if not item:
            continue
        header, path_bytes = item.split(b"\t", 1)
        mode, kind, sha_bytes = header.split(b" ")
        if mode != b"100644" or kind != b"blob":
            raise ValueError("nonfile workflow Git tree record")
        try:
            path = path_bytes.decode("utf-8")
            sha = sha_bytes.decode("ascii")
        except UnicodeDecodeError as exc:
            raise ValueError("invalid pinned Git object path") from exc
        if not PATH.fullmatch(path) or not SHA40.fullmatch(sha):
            raise ValueError("noncanonical workflow in pinned Git tree")
        if path in files:
            raise ValueError("duplicate Git tree path")
        raw = _git(root, "cat-file", "blob", sha)
        computed = hashlib.sha1(
            b"blob " + str(len(raw)).encode() + b"\0" + raw
        ).hexdigest()
        if sha != computed:
            raise ValueError("Git workflow blob SHA mismatch")
        files[path] = raw
        shas[path] = sha
    if len(files) != 149:
        raise ValueError("pinned Nov9 Git tree workflow inventory incomplete")
    result = inspect(files, pinned=pinned)
    if any(row["git_blob_sha1"] != shas[row["path"]] for row in result["files"]):
        raise ValueError("workflow content changed from tree read")
    return result


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--pinned-checkout", required=True)
    p.add_argument("--output", required=True)
    a = p.parse_args()
    report = scan(a.pinned_checkout)
    target = Path(a.output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                      encoding="utf-8")
    print("T12_FULL_WORKFLOW_INVENTORY=" + json.dumps({
        key: val for key, val in report.items() if key not in (
            "files", "declared_scheduled_workflow_paths")
    }, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()

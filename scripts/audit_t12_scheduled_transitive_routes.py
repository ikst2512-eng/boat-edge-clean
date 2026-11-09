"""Read-only pinned-main static scheduled script graph; never formal certification."""
import argparse
import ast
import hashlib
import json
import re
import subprocess
from collections import deque
from pathlib import Path
from scripts.audit_t12_full_workflow_inventory import PINNED, _events

TARGET = ("capture_official_racelist_receipt", "observe_three_official_t12_originals", "/owpc/pc/race/racelist")
# Known workflow setup/upload actions are still external code, never negative proof.
# This list is only used for human triage of unresolved references.
SETUP_ACTION_PREFIXES = (
    "actions/checkout@", "actions/setup-python@", "actions/setup-node@",
    "actions/setup-java@", "actions/cache@", "actions/upload-artifact@",
    "actions/download-artifact@",
)
PY = re.compile(r"\bpython(?:3(?:\.\d+)?)?\s+(?:-u\s+|-B\s+|-O\s+)*(?:-m\s+([\w.]+)|([\w./-]+\.py))")
SH = re.compile(r"\b(?:bash|sh)\s+([\w./-]+\.sh)")
IMP = re.compile(r"(?m)^\s*(?:from\s+([\w.]+)\s+import|import\s+([\w.]+))")


def git(root, *args):
    p = subprocess.run(["git", "-C", str(root), *args], capture_output=True, timeout=45)
    if p.returncode:
        raise ValueError("pinned Git read unavailable")
    return p.stdout


def module_path(name, paths):
    if not name or not re.fullmatch(r"[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*", name):
        return None
    stem = name.replace(".", "/")
    return next((p for p in (stem+".py", stem+"/__init__.py") if p in paths), None)


def literal_links(text, paths):
    found = set()
    for match in PY.finditer(text):
        module, file = match.groups()
        p = module_path(module, paths) if module else file.removeprefix("./")
        if p in paths:
            found.add(p)
    for match in SH.finditer(text):
        p = match.group(1).removeprefix("./")
        if p in paths:
            found.add(p)
    for match in IMP.finditer(text):
        p = module_path(match.group(1) or match.group(2), paths)
        if p:
            found.add(p)
    return found


def job_commands(text):
    lines = text.splitlines()
    try:
        i = lines.index("jobs:") + 1
    except ValueError:
        return [], []
    runs, uses = [], []
    while i < len(lines):
        line = lines[i]
        if line and not line[0].isspace() and not line.startswith("#"):
            break
        m = re.match(r"^(\s+)(?:-\s+)?(run|uses):\s*(.*)$", line)
        if m:
            indent, kind, value = m.groups()
            if kind == "uses":
                uses.append(value.strip().strip("'\""))
            else:
                block = [value]
                if value.strip() in ("|", "|-", "|+", ">", ">-", ">+") or not value.strip():
                    j = i+1
                    while j < len(lines):
                        v = lines[j]
                        if v.strip() and len(v)-len(v.lstrip()) <= len(indent):
                            break
                        block.append(v)
                        j += 1
                    i = j-1
                runs.append("\n".join(block))
        i += 1
    return runs, uses


def python_links(text, paths):
    try:
        tree = ast.parse(text)
    except (SyntaxError, ValueError):
        return set(), {"unparseable_python"}
    links, unknown = set(), set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names = [x.name for x in node.names]
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            names = [node.module] + [node.module+"."+x.name for x in node.names]
        else:
            names = []
        for name in names:
            p = module_path(name, paths)
            if p:
                links.add(p)
        if isinstance(node, ast.Call):
            try:
                fn = ast.unparse(node.func)
            except (ValueError, AttributeError):
                continue
            if fn in ("importlib.import_module", "__import__", "runpy.run_module"):
                x = node.args[0] if node.args else None
                if isinstance(x, ast.Constant) and isinstance(x.value, str):
                    p = module_path(x.value, paths)
                    if p:
                        links.add(p)
                else:
                    unknown.add("dynamic_import")
            if fn in ("subprocess.run", "subprocess.Popen", "subprocess.call", "subprocess.check_output", "os.system", "os.popen"):
                x = node.args[0] if node.args else None
                if isinstance(x, ast.Constant) and isinstance(x.value, str):
                    links.update(literal_links(x.value, paths))
                elif isinstance(x, (ast.Tuple, ast.List)) and all(isinstance(y, ast.Constant) and isinstance(y.value, str) for y in x.elts):
                    links.update(literal_links(" ".join(y.value for y in x.elts), paths))
                else:
                    unknown.add("dynamic_subprocess")
            if fn in ("eval", "exec", "runpy.run_path"):
                unknown.add("dynamic_code")
    return links, unknown


def inspect(workflows, paths, load, strict=True):
    scheduled = []
    for p, source in workflows.items():
        events = _events(source.decode("utf-8"))
        if events is None:
            raise ValueError("unclassified trigger")
        if "schedule" in events:
            scheduled.append(p)
    if strict and (len(workflows) != 149 or len(scheduled) != 51):
        raise ValueError("pinned workflow counts changed")
    rows = []
    for workflow in sorted(scheduled):
        runs, uses = job_commands(workflows[workflow].decode("utf-8"))
        parent, seen, todo, unknown = {}, set(), deque(), set()
        external_refs = set()
        def add(p, by):
            if p in paths and p not in parent and p != workflow:
                parent[p] = by
                todo.append(p)
        for run in runs:
            for p in literal_links(run, paths):
                add(p, workflow)
            if re.search(r"\b(?:curl|wget|node|npm|npx|docker)\b", run):
                unknown.add("non_python_network_or_process")
            if "$" + "{{" in run:
                unknown.add("dynamic_workflow_expression")
        for use in uses:
            if use.startswith("./"):
                p = use.removeprefix("./")
                if p in paths and p.endswith((".yml", ".yaml")):
                    add(p, workflow)
                else:
                    unknown.add("local_action_unexpanded")
            elif "@" in use:
                external_refs.add(use)
                unknown.add("external_action_unexpanded")
        matches = []
        while todo:
            p = todo.popleft()
            if p in seen:
                continue
            if len(seen) >= 2000:
                unknown.add("file_limit")
                break
            seen.add(p)
            raw = load(p)
            if raw is None:
                unknown.add("missing_source")
                continue
            source = raw.decode("utf-8")
            if any(x in source or x in p for x in TARGET):
                trail = [p]
                while parent.get(trail[-1]) not in (None, workflow):
                    trail.append(parent[trail[-1]])
                matches.append({"file": p, "via": [workflow]+list(reversed(trail))})
            links = set()
            if p.endswith(".py"):
                links, missing = python_links(source, paths)
                unknown.update(missing)
            elif p.endswith((".yml", ".yaml")):
                inner, uses2 = job_commands(source)
                for run in inner:
                    links.update(literal_links(run, paths))
                for use in uses2:
                    if use.startswith("./") and use.removeprefix("./") in paths:
                        links.add(use.removeprefix("./"))
                    elif use.startswith("./"):
                        unknown.add("nested_local_action_unexpanded")
                    elif "@" in use:
                        external_refs.add(use)
                        unknown.add("external_action_unexpanded")
            elif p.endswith(".sh"):
                links = literal_links(source, paths)
                if re.search(r"\b(?:source|eval|curl|wget)\b", source):
                    unknown.add("dynamic_shell")
            for child in links:
                add(child, p)
        non_external_unknown = unknown - {"external_action_unexpanded"}
        setup_refs = sorted(x for x in external_refs if x.startswith(SETUP_ACTION_PREFIXES))
        other_refs = sorted(external_refs - set(setup_refs))
        rows.append({"workflow": workflow, "run_blocks": len(runs),
                     "local_sources_reached": len(seen), "racelist_candidate_chains": matches,
                     "unresolved": sorted(unknown),
                     "unresolved_non_external": sorted(non_external_unknown),
                     "external_action_refs": sorted(external_refs),
                     "external_setup_action_refs": setup_refs,
                     "external_other_action_refs": other_refs,
                     "only_external_action_unresolved": unknown == {"external_action_unexpanded"},
                     "absence_proven": False})
    return {"schema": "T12_PINNED_TRANSITIVE_STATIC_V1", "main_sha": PINNED,
            "workflows": len(workflows), "scheduled_workflows": len(scheduled),
            "scheduled_with_candidate_chain": sum(bool(x["racelist_candidate_chains"]) for x in rows),
            "scheduled_with_unresolved": sum(bool(x["unresolved"]) for x in rows),
            "scheduled_with_non_external_unknown": sum(bool(x["unresolved_non_external"]) for x in rows),
            "scheduled_with_only_external_action_unknown": sum(x["only_external_action_unresolved"] for x in rows),
            "scheduled_with_other_external_action_refs": sum(bool(x["external_other_action_refs"]) for x in rows),
            "scheduled_with_no_unresolved": sum(not x["unresolved"] for x in rows),
            "rows": rows, "no_indirect_capture_proven": False, "official_http_capture_proven": False,
            "same_race_three_originals_proven": False, "new_forecast_remote_acceptance_proven": False,
            "formal": False, "t12_eligible": False, "new_formal_certifications": 0,
            "formal_accuracy_denominator": None,
            "limitations": "Literal static graph only. Setup-action labeling is triage, not source inspection or proof of safety. Imports may be unused; dynamic dispatch, local/external actions and runtime network calls remain unproven."}


def scan(root):
    root = Path(root)
    if not root.is_dir() or root.is_symlink() or git(root, "rev-parse", "HEAD").decode().strip() != PINNED:
        raise ValueError("not pinned main checkout")
    paths = {}
    for record in git(root, "ls-tree", "-rz", PINNED).split(b"\0"):
        if record:
            header, raw_path = record.split(b"\t", 1)
            mode, kind, sha = header.split()
            if kind == b"blob":
                paths[raw_path.decode()] = sha.decode()
    cache = {}
    def load(p):
        if p not in paths:
            return None
        if p not in cache:
            raw = git(root, "cat-file", "blob", paths[p])
            if len(raw) > 1_000_000 or hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest() != paths[p]:
                raise ValueError("pinned blob size or hash mismatch")
            cache[p] = raw
        return cache[p]
    workflows = {p: load(p) for p in paths if re.fullmatch(r"\.github/workflows/[^/]+\.ya?ml", p)}
    return inspect(workflows, paths, load)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pinned-checkout", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    result = scan(args.pinned_checkout)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    print("T12_TRANSITIVE_SCAN "+json.dumps({k:v for k,v in result.items() if k!="rows"}, ensure_ascii=False))
    for row in result["rows"]:
        if row["racelist_candidate_chains"]:
            print("RACELIST_POTENTIAL "+json.dumps({"workflow":row["workflow"],"chains":row["racelist_candidate_chains"][:10]},ensure_ascii=False))


if __name__ == "__main__":
    main()

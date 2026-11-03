"""Independently re-audit same-day scheduled original T12 archives; read only."""
import io
import json
import os
import re
import tempfile
import zipfile
from pathlib import Path, PurePosixPath
from urllib.parse import quote
from urllib.request import Request, urlopen

from scripts.audit_three_official_t12_originals import audit_three_originals
from scripts.inspect_joint_t12_archive import load_archive

RACE = "202611030212"
DAY = "20261103"
WORKFLOW = "official-three-original-t12-observation.yml"
EXPECTED_SLOTS_JST = ("15:20", "15:25", "15:30", "15:40", "15:48", "15:50", "15:51")
FILES = {"card": ("racelist.html", "manifest.json"),
         "before": ("beforeinfo.json", "manifest.json"),
         "odds": ("original.html", "manifest.json")}


def audit_artifact(raw, run_id, auditor=audit_three_originals):
    """Report is not trusted: reconstruct and check original bytes/receipts."""
    if type(run_id) is not int or run_id <= 0:
        raise ValueError("invalid run ID")
    with zipfile.ZipFile(io.BytesIO(raw)) as archive, tempfile.TemporaryDirectory() as temp:
        entries = archive.infolist()
        if len(entries) > 1000 or sum(x.file_size for x in entries) > 10_000_000:
            raise ValueError("unsafe artifact size")
        seen = set()
        for entry in entries:
            name = PurePosixPath(entry.filename)
            if (name.is_absolute() or ".." in name.parts or entry.filename in seen
                    or entry.file_size > 2_000_000):
                raise ValueError("unsafe artifact member")
            seen.add(entry.filename)
        report_name = "reports/three_originals.json"
        if report_name not in seen:
            return {"status": "missing_observation_report", "research_complete": False}
        report = json.loads(archive.read(report_name))
        if (not isinstance(report, dict) or report.get("race_code") != RACE
                or report.get("forecast_usable") is not False
                or report.get("full_t12_source_certified") is not False):
            raise ValueError("contradictory or foreign report")
        if report.get("status") not in ("research_components_complete_by_t12",
                                         "research_components_incomplete"):
            return {"status": report.get("status", "observation_failed"),
                    "research_complete": False}
        missing = []
        roots = {}
        for part, names in FILES.items():
            prefix = f"evidence/observations/{part}{run_id}/{DAY}/{RACE}/"
            roots[part] = Path(temp) / prefix
            for filename in names:
                key = prefix + filename
                if key not in seen:
                    missing.append(key)
                    continue
                dst = roots[part] / filename
                dst.parent.mkdir(parents=True, exist_ok=True)
                dst.write_bytes(archive.read(key))
        if missing:
            return {"status": "source_original_missing",
                    "missing_source_count": len(missing), "research_complete": False}
        independently = auditor(roots["card"], roots["before"], roots["odds"])
        if independently.get("race_code") != RACE:
            raise ValueError("source race mismatch")
        declared = report.get("audit")
        # Do not let the report claim more complete components or different
        # evidence times than the original-source independent result.
        if (not isinstance(declared, dict)
                or declared.get("component_checks") != independently.get("component_checks")
                or declared.get("missing_components") != independently.get("missing_components")
                or any(declared.get(k) != independently.get(k) for k in (
                    "cutoff_jst", "racelist_received_jst",
                    "beforeinfo_received_jst", "odds_received_jst"))):
            raise ValueError("report disagrees with independent originals")
        return {
            "status": "independent_originals_reaudited",
            "research_complete": independently["all_research_components_observed_by_t12"],
            "missing_components": independently["missing_components"],
            "received_jst": {
                "racelist": independently["racelist_received_jst"],
                "beforeinfo": independently["beforeinfo_received_jst"],
                "odds": independently["odds_received_jst"],
            },
            "full_t12_source_certified": False,
            "forecast_usable": False,
        }


def review_runs(runs, artifacts_for_run, get_zip, audit=audit_artifact):
    if not isinstance(runs, list) or len(runs) > 100:
        raise ValueError("invalid run inventory")
    findings = []
    ids = set()
    for run in runs:
        rid = run.get("id")
        if (type(rid) is not int or rid <= 0 or rid in ids
                or run.get("event") != "schedule"
                or not isinstance(run.get("created_at"), str)
                or not run["created_at"].startswith("2026-11-03T")):
            raise ValueError("invalid scheduled run identity")
        ids.add(rid)
        outcome = {"run_id": rid, "run_conclusion": run.get("conclusion"),
                   "source_status": "unverified", "research_complete": False}
        try:
            artifacts = artifacts_for_run(rid)
            if not isinstance(artifacts, list):
                raise ValueError("invalid artifacts list")
            matches = [a for a in artifacts if
                       a.get("name") == f"official-three-originals-{rid}"
                       and a.get("expired") is False]
            if len(matches) != 1:
                outcome["source_status"] = "missing_or_ambiguous_artifact"
            else:
                aid = matches[0].get("id")
                if type(aid) is not int or aid <= 0:
                    raise ValueError("invalid artifact ID")
                examined = audit(get_zip(aid), rid)
                outcome.update({"source_status": examined["status"],
                                "research_complete": examined["research_complete"],
                                "missing_components": examined.get("missing_components", []),
                                "received_jst": examined.get("received_jst")})
        except (ValueError, KeyError, OSError, TypeError, UnicodeError, EOFError,
                zipfile.BadZipFile, zipfile.LargeZipFile) as err:
            outcome["source_status"] = "independent_audit_unresolved"
            outcome["error_type"] = type(err).__name__
        findings.append(outcome)
    return {
        "race_code": RACE,
        "scope": "only scheduled workflow runs on 2026-11-03 UTC; not all historical races",
        "expected_schedule_count": len(EXPECTED_SLOTS_JST),
        "expected_jst_schedule": list(EXPECTED_SLOTS_JST),
        "observed_scheduled_runs": len(findings),
        "independent_originals_reaudited": sum(
            x["source_status"] == "independent_originals_reaudited" for x in findings),
        "research_complete_by_t12": sum(x["research_complete"] is True for x in findings),
        "missing_or_unverified_runs": sum(
            x["source_status"] != "independent_originals_reaudited" for x in findings),
        "all_scheduled_slots_proven": False,
        "full_t12_source_certified": False,
        "forecast_usable": False,
        "run_findings": findings,
    }


def github_request(url, token):
    request = Request(url, headers={"Authorization": "Bearer " + token,
                                  "Accept": "application/vnd.github+json",
                                  "X-GitHub-Api-Version": "2022-11-28"})
    with urlopen(request, timeout=25) as response:
        return json.load(response)


def collect(repo, token):
    if (not token or not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo)):
        raise ValueError("missing GitHub access or repository")
    base = "https://api.github.com/repos/" + repo
    runs_json = github_request(
        base + "/actions/workflows/" + WORKFLOW
        + "/runs?event=schedule&created=2026-11-03&per_page=100", token)
    runs = runs_json.get("workflow_runs")
    if not isinstance(runs, list) or runs_json.get("total_count") != len(runs):
        raise ValueError("run enumeration incomplete; cannot infer missing observations")
    def artifacts_for_run(rid):
        response = github_request(
            base + f"/actions/runs/{rid}/artifacts?per_page=100", token)
        artifacts = response.get("artifacts")
        if not isinstance(artifacts, list) or response.get("total_count") != len(artifacts):
            raise ValueError("artifact inventory incomplete")
        return artifacts
    return review_runs(runs, artifacts_for_run,
                       lambda aid: load_archive(repo, token, aid))


def markdown(result):
    lines = ["## 戸田12R｜T−12直前・保存原本の独立再監査", "",
             f"- 予定実行: {result['expected_schedule_count']}回（15:20、15:25、15:30、15:40、15:48、15:50、15:51 JST）",
             f"- 実行記録: {result['observed_scheduled_runs']}件（UTC当日のスケジュール実行）",
             f"- 原本3種類を独立再監査: {result['independent_originals_reaudited']}件",
             f"- 研究用T−12充足: {result['research_complete_by_t12']}件",
             f"- 未検証／不足Artifact: {result['missing_or_unverified_runs']}件",
             "- 注意：個々の予定時刻どおりの実行は未保証。時刻は原本受信時刻で判定。",
             "- 最終進入・正式予想への使用: **未認証**", "",
             "| Actions run | 原本監査結果 | 不足項目 |",
             "|---|---|---|"]
    for row in result["run_findings"]:
        lines.append(f"| {row['run_id']} | {row['source_status']} | "
                     + ", ".join(row.get("missing_components", [])) + " |")
    if not result["run_findings"]:
        lines.append("| 記録なし | 未確認（0件を成功・失敗率と解釈しない） | - |")
    return "\n".join(lines) + "\n"


def main():
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--repo", required=True)
    p.add_argument("--output", default="reports/t12_scheduled_reaudit.json")
    args = p.parse_args()
    result = collect(args.repo, os.environ.get("GITHUB_TOKEN"))
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(markdown(result))
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with Path(summary).open("a") as file:
            file.write(markdown(result))


if __name__ == "__main__":
    main()

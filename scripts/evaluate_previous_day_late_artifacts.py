"""Fetch immutable late research candidates from prior Actions artifacts for next-day evaluation.

Only whitelisted candidate JSON paths are extracted. Never manufacture predictions.
"""
import io, json, os, re, sys, zipfile
from datetime import datetime, timedelta
from pathlib import Path
from urllib.request import Request, urlopen
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from research_model import JST

CODE=re.compile(r"^[0-9]{12}\.json$")

def extract_candidates(blob, day, destination):
    count=0
    with zipfile.ZipFile(io.BytesIO(blob)) as archive:
        for member in archive.infolist():
            parts=Path(member.filename).parts
            if (member.is_dir() or len(parts)!=3
                    or parts[:2]!=("late_research_candidates",day)
                    or not CODE.fullmatch(parts[2]) or not parts[2].startswith(day)
                    or member.file_size>20000):
                continue
            raw=archive.read(member)
            candidate=json.loads(raw)
            code=parts[2][:-5]
            if (not isinstance(candidate,dict) or candidate.get("race_code")!=code
                    or candidate.get("research_only") is not True
                    or candidate.get("status")!="research_candidate_unvalidated"):
                continue
            dest=Path(destination)/day/parts[2]
            dest.parent.mkdir(parents=True,exist_ok=True)
            try:
                with dest.open("xb") as file:
                    file.write(raw)
                count+=1
            except FileExistsError:
                if dest.read_bytes()!=raw:
                    raise ValueError("conflicting immutable prediction for "+code)
    return count

def retrieve(day, root, repository, token, fetch=None):
    if not re.fullmatch(r"[0-9]{8}",day) or not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+",repository):
        raise ValueError("invalid date or repository")
    fetch=fetch or (lambda url: urlopen(Request(url,headers={
        "Authorization":"Bearer "+token,"Accept":"application/vnd.github+json",
        "X-GitHub-Api-Version":"2022-11-28","User-Agent":"BOAT-EDGE-CLEAN-research"}),timeout=20).read())
    scanned=0
    recovered=0
    dated_archives=0
    page_limit=20
    coverage_truncated=False
    for page in range(1,page_limit+1):
        response=json.loads(fetch(f"https://api.github.com/repos/{repository}/actions/artifacts?per_page=100&page={page}"))
        artifacts=response.get("artifacts",[])
        for item in artifacts:
            if (not item.get("expired") and item.get("name","").startswith("independent-late-preview-")
                    and item.get("archive_download_url")):
                scanned+=1
                before=recovered
                recovered+=extract_candidates(fetch(item["archive_download_url"]),day,root)
                dated_archives+=int(recovered>before)
        if len(artifacts)<100:
            break
        if page==page_limit:
            coverage_truncated=True
    return {"day":day,"scanned_artifacts":scanned,"artifacts_with_imported_candidates":dated_archives,
            "imported_immutable_candidates":recovered,
            "coverage_status":"incomplete_artifact_scan" if coverage_truncated else (
                "candidate_found" if recovered else "no_prior_day_candidate_found"),
            "artifact_scan_complete":not coverage_truncated}

if __name__=="__main__":
    from scripts.evaluate_late_research_topn import evaluate
    import argparse
    parser=argparse.ArgumentParser(description="Recheck preserved prospective late evidence")
    parser.add_argument("--days-ago",type=int,choices=(1,2,3),default=1)
    args=parser.parse_args()
    day=(datetime.now(JST)-timedelta(days=args.days_ago)).strftime("%Y%m%d")
    repository=os.environ["GITHUB_REPOSITORY"]
    token=os.environ["GITHUB_TOKEN"]
    root=Path("late_research_candidates")
    collected=retrieve(day,root,repository,token)
    result=evaluate(day,root,Path("."))
    # Expose the exact bottleneck; never imply absent late picks are losses.
    rejected=result.get("rejected",{})
    diagnosis={
        "missing_prospective_candidates":collected["imported_immutable_candidates"]==0,
        "candidate_records_without_early_or_result":rejected.get("missing_early_or_result",0),
        "candidate_records_outside_cutoff":rejected.get("outside_cutoff",0),
        "candidate_records_invalid_provenance":rejected.get("invalid_provenance",0),
        "ready_for_accuracy_comparison":result["paired_races"]>0,
    }
    report={"artifact_recovery":collected,"paired_evaluation":result,"diagnosis":diagnosis}
    Path("late_research_report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(report,ensure_ascii=False))

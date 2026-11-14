"""Fetch immutable late research candidates from prior Actions artifacts for next-day evaluation.

Only whitelisted candidate JSON paths are extracted. Never manufacture predictions.
"""
import io, json, os, re, sys, zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlsplit, quote
from urllib.request import Request, HTTPRedirectHandler, build_opener
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from research_model import JST

CODE=re.compile(r"^[0-9]{12}\.json$")

class _DiscardCrossHostAuth(HTTPRedirectHandler):
    """GitHub's artifact ZIP redirects to an HTTPS blob host with its own signed URL."""
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        redirected=super().redirect_request(req,fp,code,msg,headers,newurl)
        if redirected is not None:
            origin=urlsplit(req.full_url)
            destination=urlsplit(redirected.full_url)
            if destination.scheme!="https":
                raise ValueError("insecure_github_artifact_redirect")
            if (origin.scheme,origin.netloc)!=(destination.scheme,destination.netloc):
                # Do not leak GitHub's bearer token to the signed blob URL.
                for header in tuple(redirected.headers):
                    if header.lower() in ("authorization","x-github-api-version"):
                        redirected.remove_header(header)
        return redirected


def _github_fetch(url,token):
    parsed=urlsplit(url)
    if parsed.scheme!="https" or parsed.hostname!="api.github.com" or parsed.port is not None:
        raise ValueError("untrusted_github_api_url")
    request=Request(url,headers={
        "Authorization":"Bearer "+token,"Accept":"application/vnd.github+json",
        "X-GitHub-Api-Version":"2022-11-28","User-Agent":"BOAT-EDGE-CLEAN-research"})
    with build_opener(_DiscardCrossHostAuth()).open(request,timeout=20) as response:
        return response.read()

def extract_candidates(blob, day, destination, present=None):
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
            if present is not None:
                present.add(code)
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
    """Search the actual source workflow for a JST day, not all repository artifacts.

    A bounded *workflow-specific* 48-hour run window covers midnight-delayed
    uploads without silently cutting off a busy repository's artifact list.
    Run creation, a successful job, and a downloaded research candidate are
    never evidence of a verified T-12/first-commit forecast.
    """
    if not re.fullmatch(r"[0-9]{8}",day) or not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+",repository):
        raise ValueError("invalid date or repository")
    start=datetime.strptime(day,"%Y%m%d").replace(tzinfo=JST)
    stop=start+timedelta(days=2)
    begin_utc=start.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    end_utc=(stop-timedelta(seconds=1)).astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    created=quote(begin_utc+".."+end_utc,safe=".")
    fetch=fetch or (lambda url:_github_fetch(url,token))
    scanned=0
    recovered=0
    dated_archives=0
    eligible_runs=0
    run_pages=0
    expired=0
    # This is 20 pages of ONE relevant workflow, not 20 pages of all artifacts.
    page_limit=20
    coverage_truncated=False
    seen_runs=set()
    for page in range(1,page_limit+1):
        url=(f"https://api.github.com/repos/{repository}/actions/workflows/"
             f"research-live-preview-evidence.yml/runs?per_page=100&page={page}&created={created}")
        result=json.loads(fetch(url))
        runs=result.get("workflow_runs") if isinstance(result,dict) else None
        if not isinstance(runs,list) or len(runs)>100:
            raise ValueError("invalid_source_workflow_run_inventory")
        run_pages+=1
        for run in runs:
            if not isinstance(run,dict):
                raise ValueError("invalid_source_workflow_run")
            # PRs are tests, not independently scheduled observations.
            if (run.get("event") not in ("schedule","workflow_dispatch")
                    or run.get("head_branch")!="main"
                    or (run.get("head_repository") or {}).get("full_name")!=repository):
                continue
            run_id=run.get("id")
            if type(run_id) is not int or run_id<=0:
                raise ValueError("invalid_source_workflow_run_id")
            if run_id in seen_runs:
                continue
            seen_runs.add(run_id)
            try:
                run_at=datetime.fromisoformat(run["created_at"].replace("Z","+00:00"))
            except (KeyError,TypeError,ValueError,AttributeError) as exc:
                raise ValueError("invalid_source_workflow_run_timestamp") from exc
            if run_at.utcoffset() is None or not start<=run_at.astimezone(JST)<stop:
                raise ValueError("source_workflow_run_outside_search_window")
            eligible_runs+=1
            artifacts_payload=json.loads(fetch(
                f"https://api.github.com/repos/{repository}/actions/runs/{run_id}/artifacts?per_page=100"))
            archives=artifacts_payload.get("artifacts") if isinstance(artifacts_payload,dict) else None
            if not isinstance(archives,list) or len(archives)>100 or artifacts_payload.get("total_count",len(archives))>100:
                raise ValueError("incomplete_source_run_artifact_inventory")
            for item in archives:
                if not isinstance(item,dict):
                    raise ValueError("invalid_source_run_artifact")
                if item.get("name")!=f"independent-late-preview-{run_id}":
                    continue
                if item.get("expired"):
                    expired+=1
                    continue
                artifact_id=item.get("id")
                if type(artifact_id) is not int or artifact_id<=0:
                    raise ValueError("invalid_source_artifact_id")
                expected=f"https://api.github.com/repos/{repository}/actions/artifacts/{artifact_id}/zip"
                if item.get("archive_download_url")!=expected:
                    raise ValueError("untrusted_artifact_archive_url")
                scanned+=1
                contained=set()
                recovered+=extract_candidates(fetch(expected),day,root,contained)
                dated_archives+=int(bool(contained))
        if len(runs)<100:
            break
        if page==page_limit:
            coverage_truncated=True
    complete=not coverage_truncated and expired==0
    coverage=("incomplete_source_workflow_scan" if coverage_truncated else
              "expired_source_artifacts_unverifiable" if expired else
              "candidate_found" if recovered else "no_prior_day_candidate_found")
    return {"day":day,"scanned_artifacts":scanned,
            "artifacts_with_imported_candidates":dated_archives,
            "imported_immutable_candidates":recovered,
            "source_workflow":"research-live-preview-evidence.yml",
            "workflow_run_window_start_jst":start.isoformat(),
            "workflow_run_window_end_exclusive_jst":stop.isoformat(),
            "workflow_run_pages_scanned":run_pages,
            "trusted_source_runs":eligible_runs,
            "expired_source_artifacts":expired,
            "run_inventory_complete":not coverage_truncated,
            "coverage_status":coverage,
            "artifact_scan_complete":complete}

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

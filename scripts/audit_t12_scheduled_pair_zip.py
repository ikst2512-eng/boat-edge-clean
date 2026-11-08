"""Read-only replay of actual 'independent-late-preview' scheduled Actions ZIPs.

This format has official_joint_evidence/batch_report.json and raw originals
under observations/{before,odds}_run<run-id>/<day>/<race>/. It is distinct
from the historical reports/joint_N.json research archive format.
The self-reported batch 'pair_complete' flag is NEVER enough: replay the
original SHA/URL/timestamps/6-boat/120-odds audit from the stored raw bytes.
"""
import argparse
import hashlib
import io
import json
import re
import tempfile
import zipfile
from datetime import datetime, timedelta
from pathlib import Path, PurePosixPath
from urllib.parse import urlencode

HEX = re.compile(r"[a-f0-9]{64}\Z")
RACE = re.compile(r"20[0-9]{10}\Z")
RUN = re.compile(r"[1-9][0-9]{7,17}\Z")
REPORT = "official_joint_evidence/batch_report.json"
JST = timedelta(hours=9)


def _source(archive, members, prefix, filename, race, *, odds=False):
    original_name = prefix + filename
    manifest_name = prefix + "manifest.json"
    exists = original_name in members
    if exists != (manifest_name in members):
        raise ValueError("partial original and manifest pair")
    if not exists:
        return None
    raw = archive.read(original_name)
    manifest = json.loads(archive.read(manifest_name))
    if not isinstance(manifest, dict) or manifest.get("race_code") != race:
        raise ValueError("original manifest race identity mismatch")
    if (type(manifest.get("bytes")) is not int
            or manifest["bytes"] != len(raw)
            or hashlib.sha256(raw).hexdigest() != manifest.get("sha256")):
        raise ValueError("source original SHA/length invalid")
    if manifest.get("status") != ("official_odds_observed_research_only"
                                  if odds else "official_json_observed_not_t12_certified"):
        raise ValueError("unsuccessful original source status")
    day, venue, number = race[:8], race[8:10], str(int(race[10:]))
    params = urlencode({"hd": day, "jcd": venue, "rno": number})
    url = ("https://www.boatrace.jp/owpc/pc/race/odds3t?" + params
           if odds else "https://www.boatrace.jp/owsp/sp/spdata?type=beforeinfo&" + params)
    if manifest.get("official_url" if odds else "url") != url:
        raise ValueError("nonofficial or mismatched original source URL")
    started = datetime.fromisoformat(manifest["request_started_at_jst"])
    received = datetime.fromisoformat(manifest["received_at_jst"])
    if (started.utcoffset() != JST or received.utcoffset() != JST
            or received < started or any(
                t.strftime("%Y%m%d") != day for t in (started, received))):
        raise ValueError("bad original source receipt chronology")
    return {"original": raw, "manifest": manifest, "received": received,
            "filename": filename}


def replay(raw_zip, run_id, expected_zip_sha256, *, auditor=None):
    if (type(raw_zip) is not bytes or not raw_zip or len(raw_zip) > 20_000_000
            or type(run_id) is not int or not RUN.fullmatch(str(run_id))
            or type(expected_zip_sha256) is not str
            or not HEX.fullmatch(expected_zip_sha256)):
        raise ValueError("invalid immutable Actions ZIP identity")
    if hashlib.sha256(raw_zip).hexdigest() != expected_zip_sha256:
        raise ValueError("Actions artifact ZIP digest mismatch")
    if auditor is None:
        from scripts.audit_joint_official_receipts import audit_pair
        auditor = audit_pair
    with zipfile.ZipFile(io.BytesIO(raw_zip)) as archive:
        entries = archive.infolist()
        if (len(entries) > 2000 or sum(e.file_size for e in entries) > 20_000_000
                or any(e.file_size > 2_000_000 for e in entries)):
            raise ValueError("unsafe archive dimensions")
        names = []
        for e in entries:
            name = PurePosixPath(e.filename)
            if (name.is_absolute() or ".." in name.parts
                    or "\\" in e.filename
                    or e.external_attr >> 16 & 0o170000 == 0o120000):
                raise ValueError("unsafe archive member")
            names.append(e.filename)
        if len(set(names)) != len(names):
            raise ValueError("duplicate archive member")
        if archive.testzip() is not None:
            raise ValueError("corrupt original Actions ZIP")
        members = set(names)
        if REPORT not in members:
            raise ValueError("original scheduled batch report missing")
        report = json.loads(archive.read(REPORT))
        if (not isinstance(report, dict)
                or report.get("event") != "schedule"
                or report.get("formal") is not False
                or report.get("forecast_usable") is not False
                or report.get("full_t12_source_certified") is not False):
            raise ValueError("report is not an authentic nonformal schedule observation")
        day = report.get("date")
        if not isinstance(day, str) or not re.fullmatch(r"20[0-9]{6}", day):
            raise ValueError("invalid observed race day")
        checked_at = datetime.fromisoformat(report["checked_at_jst"])
        if checked_at.utcoffset() != JST or checked_at.strftime("%Y%m%d") != day:
            raise ValueError("wrong scheduled report day/offset")
        observations = report.get("observations")
        if not isinstance(observations, list):
            raise ValueError("observations missing")
        if (type(report.get("eligible_candidates")) is not int
                or report["eligible_candidates"] != len(observations)
                or len(observations) > 2):
            raise ValueError("candidate count not reconciled")
        saved_before = saved_odds = complete = 0
        rows = []
        seen = set()
        for item in observations:
            race = item.get("race_code") if isinstance(item, dict) else None
            if (not isinstance(race, str) or not RACE.fullmatch(race)
                    or race[:8] != day or int(race[8:10]) not in range(1, 25)
                    or int(race[10:]) not in range(1, 13) or race in seen
                    or item.get("forecast_usable") is not False):
                raise ValueError("invalid original race candidate")
            seen.add(race)
            prefix = "official_joint_evidence/observations/"
            a = prefix + f"before_run{run_id}/{day}/{race}/"
            b = prefix + f"odds_run{run_id}/{day}/{race}/"
            before = _source(archive, members, a, "beforeinfo.json", race)
            odds = _source(archive, members, b, "original.html", race, odds=True)
            if odds and not before:
                raise ValueError("orphan official odds without beforeinfo original")
            saved_before += before is not None
            saved_odds += odds is not None
            row = {
                "race_code": race, "reported_status": item.get("status"),
                "official_beforeinfo_original_replayed": before is not None,
                "official_odds_original_replayed": odds is not None,
                "two_originals_complete_by_t12": False,
                "official_racelist_original_replayed": False,
                "formal": False,
            }
            if before:
                source = json.loads(before["original"])
                main = source.get("maindata")
                if (not isinstance(main, dict) or str(main.get("hd")) != day
                        or str(main.get("jcd")).zfill(2) != race[8:10]
                        or str(main.get("rno")) != str(int(race[10:]))):
                    raise ValueError("original beforeinfo body identity mismatch")
                from scripts.inspect_official_beforeinfo_json import inspect
                contents = inspect(source)
                cutoff = datetime.fromisoformat(
                    f"{day[:4]}-{day[4:6]}-{day[6:8]}T"
                    + contents["deadline_display"] + ":00+09:00") - timedelta(minutes=12)
                row.update({
                    "official_t12_cutoff_jst": cutoff.isoformat(),
                    "beforeinfo_received_jst": before["received"].isoformat(),
                    "exhibition_time_observed_boats": contents["exhibition_time_observed_boats"],
                    "start_exhibition_six_valid_rows": contents["start_exhibition_six_valid_rows"],
                })
            if before and odds:
                from pathlib import Path
                with tempfile.TemporaryDirectory() as temp:
                    before_dir, odds_dir = Path(temp) / "before", Path(temp) / "odds"
                    before_dir.mkdir(); odds_dir.mkdir()
                    for folder, pair in ((before_dir, before), (odds_dir, odds)):
                        (folder / pair["filename"]).write_bytes(pair["original"])
                        (folder / "manifest.json").write_text(
                            json.dumps(pair["manifest"]), encoding="utf-8")
                    audited = auditor(before_dir, odds_dir)
                if audited.get("race_code") != race:
                    raise ValueError("real official pair re-audit race identity mismatch")
                if (audited.get("originals_hash_verified") is not True
                        or audited.get("full_t12_source_certified") is not False
                        or audited.get("forecast_usable") is not False):
                    raise ValueError("independent pair auditor did not fail-closed")
                declared = item.get("joint_audit")
                for field in ("race_code", "cutoff_jst",
                              "before_received_jst", "odds_received_jst",
                              "both_complete_before_t12", "component_checks",
                              "missing_components"):
                    if (not isinstance(declared, dict)
                            or declared.get(field) != audited.get(field)):
                        raise ValueError("reported pair success disagrees with replayed originals")
                is_complete = audited.get("both_complete_before_t12") is True
                if item.get("status") != ("pair_complete" if is_complete else "pair_not_ready"):
                    raise ValueError("reported pair status disagrees with original replay")
                row["two_originals_complete_by_t12"] = is_complete
                row["official_odds_120_verified"] = audited.get("odds_120_complete") is True
                row["last_source_received_jst"] = max(
                    before["received"], odds["received"]).isoformat()
                complete += is_complete
            elif item.get("status") in ("pair_complete", "pair_not_ready"):
                raise ValueError("claimed pair status without both original source files")
            rows.append(row)
        expected = (("beforeinfo_originals_saved", saved_before),
                    ("official_odds_originals_saved", saved_odds),
                    ("complete_pairs_before_t12", complete))
        if any(type(report.get(k)) is not int or report[k] != v for k, v in expected):
            raise ValueError("batch source counts disagree with original ZIP")
        if (report.get("status") == "no_pre_t12_candidate") != (len(observations) == 0):
            raise ValueError("empty scheduled run not classified as no-op")
        return {
            "schema": "T12_ACTUAL_SCHEDULED_SOURCE_PAIR_ZIP_REPLAY_V1",
            "run_id": run_id, "day_jst": day,
            "artifact_sha256": expected_zip_sha256,
            "original_beforeinfo_count": saved_before,
            "original_odds_count": saved_odds,
            "two_original_complete_race_count": complete,
            "candidate_count": len(rows),
            "race_rows": rows,
            "status": ("no_pre_t12_candidate" if not rows else
                       "source_pairs_independently_replayed_nonformal"),
            "official_racelist_originals_verified": 0,
            "model_original_input_consumption_verified": False,
            "independent_first_git_remote_receipt_verified": False,
            "final_entry_verified": False,
            "full_t12_source_certified": False,
            "formal": False,
            "t12_eligible": False,
            "accuracy_scoring_allowed": False,
        }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--zip", required=True)
    parser.add_argument("--run-id", required=True, type=int)
    parser.add_argument("--expected-zip-sha256", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    output = replay(Path(args.zip).read_bytes(), args.run_id,
                    args.expected_zip_sha256)
    file = Path(args.output)
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8")
    print("T12_ACTUAL_OFFICIAL_PAIR_ZIP_REPLAY=" + json.dumps(
        {k: v for k, v in output.items() if k != "race_rows"}, ensure_ascii=False))


if __name__ == "__main__":
    main()

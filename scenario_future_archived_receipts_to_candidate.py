"""#1710: saved official 3-original receipts -> pinned four-mode candidate.

One-shot / explicit operator action. NO collector, no Cron, no results reader,
no model calibration, no automatic publication. Only the already-existing #1713
receipt format and #1710 frozen study are accepted. CLI defaults to dry-run.
"""
import argparse
import base64
from datetime import datetime, timedelta, timezone
import hashlib
import importlib
import importlib.util
import json
import os
from pathlib import Path
import sys

from scripts.audit_three_official_t12_originals import audit_three_originals
from scripts.inspect_official_racelist_registrations import inspect_six_registrations
from server import parse_official_odds_table
from scenario_official_racelist_rates import extract_six_official_racelist_rates
from scenario_future_three_original_gateway import run_future_triple_experiment
from scenario_future_local_candidate_handoff import (
    PROTOCOL_PATH, RESEARCH_ONLY_LEDGER_BRANCH,
    prepare_local_candidate, publish_local_candidate_write_once,
    require_registered_study_and_unchanged_model, _git_blob_sha1,
)
from scenario_future_github_research_adapter import GitHubOnlyCreateWire

JST=timezone(timedelta(hours=9))
FILES={"racelist":"racelist.html","beforeinfo":"beforeinfo.json","odds120":"original.html"}
RECEIPT_URL_KEYS={"racelist":"official_url","beforeinfo":"url","odds120":"official_url"}
PINNED_1693_PREFLIGHT_SHA1="88caa6ee3b324df58e60397d74055a075a8de6a9"


def _json_unique(pairs):
    result={}
    for key,value in pairs:
        if key in result:
            raise ValueError("receipt_duplicate_json_key")
        result[key]=value
    return result


def _jst(value):
    if type(value) is not datetime or value.utcoffset()!=timedelta(hours=9):
        raise ValueError("runner_clock_requires_aware_JST")
    return value


def _load_receipt(path,filename):
    folder=Path(path)
    raw_path=folder/filename
    meta_path=folder/"manifest.json"
    if (folder.is_symlink() or raw_path.is_symlink() or meta_path.is_symlink()
            or not raw_path.is_file() or not meta_path.is_file()
            or not 0<raw_path.stat().st_size<=1_000_000
            or not 0<meta_path.stat().st_size<=30_000):
        raise ValueError("original_receipt_missing_symlink_or_oversize")
    raw=raw_path.read_bytes()
    manifest=json.loads(meta_path.read_text(encoding="utf-8"),
                        object_pairs_hook=_json_unique,
                        parse_constant=lambda _: (_ for _ in ()).throw(ValueError("nonfinite_receipt")))
    if (type(manifest) is not dict
            or manifest.get("sha256")!=hashlib.sha256(raw).hexdigest()
            or manifest.get("bytes")!=len(raw)):
        raise ValueError("official_receipt_raw_hash_or_manifest_mismatch")
    return raw,manifest


def build_archive_bundle(card_dir,before_dir,odds_dir,generated_at_jst,
                         *,auditor=audit_three_originals,
                         before_parser=None,card_parser=inspect_six_registrations,
                         odds_parser=parse_official_odds_table):
    """Reuse existing official receipt auditors and source parsers; no HTTP fetch.

    before_parser is the exact Git-blob-pinned #1693 _beforeinfo_features,
    not the synthetic fixture callback.
    """
    if not callable(before_parser) or not callable(auditor):
        raise ValueError("pinned_raw_beforeinfo_parser_and_auditor_required")
    audit=auditor(card_dir,before_dir,odds_dir)
    if (type(audit) is not dict or audit.get("all_research_components_observed_by_t12") is not True
            or audit.get("three_originals_hash_verified") is not True
            or audit.get("missing_components")!=[]
            or audit.get("forecast_usable") is not False
            or audit.get("t12_eligible") is not False):
        raise ValueError("three_official_T12_originals_incomplete")
    code=audit.get("race_code")
    if type(code) is not str or len(code)!=12 or not code.isdigit() or code[:8]<"20261111":
        raise ValueError("not_a_future_race")
    dirs={"racelist":card_dir,"beforeinfo":before_dir,"odds120":odds_dir}
    raw={}
    manifests={}
    for kind in FILES:
        raw[kind],manifests[kind]=_load_receipt(dirs[kind],FILES[kind])
        if manifests[kind].get("race_code")!=code:
            raise ValueError("cross_race_archived_manifest")
    before=before_parser(raw["beforeinfo"],code)
    card=card_parser(raw["racelist"])
    if (type(before) is not dict or type(card) is not dict
            or card.get("six_racers_verified") is not True
            or before.get("deadline_display")!=audit["official_deadline_jst"][11:16]):
        raise ValueError("official_raw_reparse_incomplete")
    registrations=[card["registrations_by_lane"][str(i)] for i in range(1,7)]
    if (registrations!=before["beforeinfo_registration_ids"]
            or audit["registrations_by_lane"]!={str(i):reg for i,reg in enumerate(registrations,1)}):
        raise ValueError("official_raw_registration_ids_differ")
    actual_odds=odds_parser(raw["odds120"].decode("utf-8",errors="replace"))
    if type(actual_odds) is not dict or len(actual_odds)!=120:
        raise ValueError("official_120_odds_not_parsed")
    expected_names={"beforeinfo_registration_ids","exhibition_courses",
                    "exhibition_times","exhibition_st","exhibition_tilts","deadline_display"}
    if set(before)!=expected_names:
        raise ValueError("unexpected_official_beforeinfo_parser_fields")
    hashes={kind:hashlib.sha256(raw[kind]).hexdigest() for kind in FILES}
    norm={
        "race_code":code,
        "source_sha256":hashes,
        "racelist_registration_ids":registrations,
        **{key:before[key] for key in expected_names-{"deadline_display"}},
        "odds_3t":{ticket:float(value) for ticket,value in actual_odds.items()},
    }
    originals={}
    for kind in FILES:
        metadata=manifests[kind]
        source_url=metadata.get(RECEIPT_URL_KEYS[kind])
        if type(source_url) is not str or not source_url.startswith("https://www.boatrace.jp/"):
            raise ValueError("missing_official_exact_source_URL")
        originals[kind]={
            "raw_base64":base64.b64encode(raw[kind]).decode("ascii"),
            "sha256":hashes[kind],
            "source_url":source_url,
            "received_at_jst":metadata.get("received_at_jst"),
        }
    deadline=audit["official_deadline_jst"]
    if (type(generated_at_jst) is not str
            or datetime.fromisoformat(generated_at_jst).utcoffset()!=timedelta(hours=9)
            or generated_at_jst[:10]!=deadline[:10]
            or not datetime.fromisoformat(generated_at_jst) <
                   datetime.fromisoformat(deadline)-timedelta(minutes=12)):
        raise ValueError("candidate_generated_after_T12_or_wrong_day")
    source={
        "schema":"FOUR_MODE_FUTURE_OFFICIAL_INPUT_LINEAGE_PREFLIGHT_V1",
        "race_code":code,"deadline_jst":deadline,
        "originals":originals,"normalized_source_claim":norm,
    }
    candidate={
        "race_code":code,"deadline_jst":deadline,
        "generated_at_jst":generated_at_jst,
        "consumed_source_sha256":hashes,
        "consumed_normalized_claim_sha256":hashlib.sha256(json.dumps(
            norm,sort_keys=True,ensure_ascii=False,
            separators=(",",":"),allow_nan=False).encode("utf-8")).hexdigest(),
        "formal":False,
    }
    return audit,source,candidate


def _pinned_imports(folder1693,folder1698,protocol):
    """Refuse unpinned parser before importing any external draft modules."""
    paths={
        "four_mode_official_future_lineage_preflight":
            (Path(folder1693)/"four_mode_official_future_lineage_preflight.py",
             PINNED_1693_PREFLIGHT_SHA1),
        "four_mode_official_raw_semantic_replay":
            (Path(folder1693)/"four_mode_official_raw_semantic_replay.py",
             protocol["pinned_external_code"]["1693_semantic_replay_code_blob_sha1"]),
        "position_sensitive_conditioned_lab":
            (Path(folder1698)/"position_sensitive_conditioned_lab.py",
             protocol["pinned_external_code"]["1698_conditional_code_blob_sha1"]),
    }
    for name,(path,pinned_sha) in paths.items():
        if (path.is_symlink() or not path.is_file()
                or not 0<path.stat().st_size<=100_000
                or _git_blob_sha1(path.read_bytes())!=pinned_sha):
            raise ValueError("unpinned_external_model_or_parser:"+name)
        if name in sys.modules:
            raise ValueError("external_model_already_loaded_ambiguous:"+name)
    loaded={}
    for name,(path,_) in paths.items():
        spec=importlib.util.spec_from_file_location(name,str(path))
        if spec is None or spec.loader is None:
            raise ValueError("pinned_external_module_load_unavailable:"+name)
        module=importlib.util.module_from_spec(spec)
        sys.modules[name]=module
        spec.loader.exec_module(module)
        loaded[name]=module
    return (loaded["four_mode_official_raw_semantic_replay"].replay,
            loaded["four_mode_official_raw_semantic_replay"]._beforeinfo_features,
            loaded["position_sensitive_conditioned_lab"].experimental_conditional_board)


def _require_actual_pinned_publish_parsers(
    raw_replay_callback, raw_before_parser, conditional_callback,
    auditor, card_parser, odds_parser, protocol,
):
    """Allow real research PUT only from the exact independently reviewed code.

    Synthetic or injected parser callbacks are useful for tests, but their
    result must NEVER be written into the immutable future-race ledger.
    """
    if (auditor is not audit_three_originals
            or card_parser is not inspect_six_registrations
            or odds_parser is not parse_official_odds_table):
        raise ValueError("publish_requires_real_official_auditor_and_parsers")
    pins=(
        (raw_replay_callback,"four_mode_official_raw_semantic_replay",
         "replay",protocol["pinned_external_code"]["1693_semantic_replay_code_blob_sha1"]),
        (raw_before_parser,"four_mode_official_raw_semantic_replay",
         "_beforeinfo_features",protocol["pinned_external_code"]["1693_semantic_replay_code_blob_sha1"]),
        (conditional_callback,"position_sensitive_conditioned_lab",
         "experimental_conditional_board",
         protocol["pinned_external_code"]["1698_conditional_code_blob_sha1"]),
    )
    for func,mod,name,sha in pins:
        if (getattr(func,"__module__",None)!=mod
                or getattr(func,"__name__",None)!=name
                or not hasattr(func,"__code__")):
            raise ValueError("publish_requires_exact_pinned_math_and_raw_parser")
        file=Path(func.__code__.co_filename)
        if (file.is_symlink() or not file.is_file()
                or not 0<file.stat().st_size<=100_000
                or _git_blob_sha1(file.read_bytes())!=sha):
            raise ValueError("publish_pinned_external_blob_changed:"+name)
    return True


def run_observed_archives(
    card_dir,before_dir,odds_dir, clock,
    raw_replay_callback, raw_before_parser, conditional_callback,
    *,publish=False,token=None,wire=None,auditor=audit_three_originals,
    card_parser=inspect_six_registrations,odds_parser=parse_official_odds_table,
):
    """One race, result blind. Validated source->4mode->frozen bytes->optional Git.

    Return does NOT attest independent original HTTP origins, first-add time
    or accuracy. Even a real write to GitHub cannot grant formal cohort credit.
    """
    if (type(publish) is not bool or not callable(clock)
            or not callable(raw_replay_callback)
            or not callable(raw_before_parser)
            or not callable(conditional_callback)):
        raise ValueError("invalid_operator_or_model_callbacks")
    protocol=json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"),
                        object_pairs_hook=_json_unique)
    require_registered_study_and_unchanged_model(protocol)
    if publish:
        _require_actual_pinned_publish_parsers(
            raw_replay_callback,raw_before_parser,conditional_callback,
            auditor,card_parser,odds_parser,protocol)
    generated=_jst(clock()).isoformat()
    audit,source,candidate=build_archive_bundle(
        card_dir,before_dir,odds_dir,generated,
        auditor=auditor,before_parser=raw_before_parser,
        card_parser=card_parser,odds_parser=odds_parser)
    from scenario_official_racelist_rates import extract_six_official_racelist_rates
    html=base64.b64decode(source["originals"]["racelist"]["raw_base64"],validate=True)
    rates=extract_six_official_racelist_rates(html)["national_rates"]
    mode_weights={
        mode:{name:float(weight) for name,weight in values.items()}
        for mode,values in protocol["mode_weights"].items()
    }
    # #1693's full raw semantic replay expects candidate_tickets and
    # candidate_method_sha256 to ALREADY exist. These are actual model outputs,
    # unavailable before the #1710 four-mode calculation. Never manufacture
    # dummy tickets just to satisfy the old preflight. Instead pre-model stage
    # reaudits the same original bytes through the real auditor and parsers,
    # and runs the full pinned #1693 replay AFTER genuine rankings exist.
    def source_only_verified_replay(source_bundle, source_candidate):
        second_audit, second_source, second_candidate=build_archive_bundle(
            card_dir,before_dir,odds_dir,generated,
            auditor=auditor,before_parser=raw_before_parser,
            card_parser=card_parser,odds_parser=odds_parser)
        if (second_audit!=audit or second_source!=source_bundle
                or second_candidate!=source_candidate):
            raise ValueError("pre_model_source_reaudit_drift")
        return {
            "schema":"FOUR_MODE_OFFICIAL_RAW_SEMANTIC_REPLAY_V1",
            "race_code":source_bundle["race_code"],
            "status":"raw_bytes_semantically_reparsed_and_declared_features_match_RESEARCH_ONLY",
            "verified_stages":[
                "preflight_raw_byte_sha_and_clock_structure",
                "official_racelist_six_registration_parser",
                "official_beforeinfo_six_exhibition_start_parser",
                "official_120_odds_html_parser",
                "declared_normalized_features_match_raw_reparse",
            ],
            "formal":False,"model_promotion_allowed":False,
            "raw_official_provenance_independently_attested":False,
            "actual_model_output_independently_replayed":False,
            "first_remote_candidate_acceptance_independently_verified":False,
        }
    gateway=run_future_triple_experiment(
        audit,source,candidate,source_only_verified_replay,rates,
        protocol["scenario_hypotheses"],mode_weights,conditional_callback)
    # Bind the full #1693 provenance replay to the ACTUAL #1710 generated
    # ranked tickets and the preregistered on-disk Git model source identity.
    # A model-derived candidate cannot be supplied before that model runs.
    actual_candidate=dict(candidate)
    actual_candidate["candidate_tickets"]={
        mode:[ticket["combo"] for ticket in
              gateway["research_mode_tickets"][mode]["tickets"]]
        for mode in ("narrow","hit","balance","hole")
    }
    actual_candidate["candidate_method_sha256"]=hashlib.sha256(
        json.dumps({
            "method_git_blob_sha1":protocol["method_git_blob_sha1"],
            "pinned_external_code":protocol["pinned_external_code"],
        },sort_keys=True,separators=(",",":"),ensure_ascii=False).encode("utf-8")
    ).hexdigest()
    full_replay=raw_replay_callback(source,actual_candidate)
    required_stages={
        "preflight_raw_byte_sha_and_clock_structure",
        "official_racelist_six_registration_parser",
        "official_beforeinfo_six_exhibition_start_parser",
        "official_120_odds_html_parser",
        "declared_normalized_features_match_raw_reparse",
    }
    if (type(full_replay) is not dict
            or full_replay.get("schema")!="FOUR_MODE_OFFICIAL_RAW_SEMANTIC_REPLAY_V1"
            or full_replay.get("race_code")!=audit["race_code"]
            or full_replay.get("status")!=
                "raw_bytes_semantically_reparsed_and_declared_features_match_RESEARCH_ONLY"
            or type(full_replay.get("verified_stages")) is not list
            or not required_stages.issubset(full_replay["verified_stages"])
            or full_replay.get("formal") is not False
            or full_replay.get("model_promotion_allowed") is not False
            or full_replay.get("actual_model_output_independently_replayed") is not False
            or full_replay.get("raw_official_provenance_independently_attested") is not False
            or full_replay.get("first_remote_candidate_acceptance_independently_verified") is not False):
        raise ValueError("pinned_complete_postmodel_semantic_replay_not_verified")
    frozen=_jst(clock()).isoformat()
    prepared=prepare_local_candidate(gateway,protocol,generated,frozen)
    # Report the *actual age of each archived source* at the local
    # generation clock, not just a boolean "before T-12" flag. Past evidence
    # proved a several-hour-old afternoon source could be added to a Git
    # ledger in the evening. This is diagnostic only: the 2026-11-10 frozen
    # study admission conditions and model scores are NOT changed here.
    generated_clock=datetime.fromisoformat(generated)
    cutoff_clock=datetime.fromisoformat(audit["cutoff_jst"])
    receipt_by_kind={
        "racelist":audit["racelist_received_jst"],
        "beforeinfo":audit["beforeinfo_received_jst"],
        "odds120":audit["odds_received_jst"],
    }
    source_age_at_generation_seconds={}
    source_age_before_t12_seconds={}
    for kind,stamp in receipt_by_kind.items():
        observed=datetime.fromisoformat(stamp)
        if (observed.utcoffset()!=timedelta(hours=9)
                or observed>generated_clock or observed>=cutoff_clock):
            raise ValueError("source_receipt_drift_or_after_T12")
        source_age_at_generation_seconds[kind]=round(
            (generated_clock-observed).total_seconds(),3)
        source_age_before_t12_seconds[kind]=round(
            (cutoff_clock-observed).total_seconds(),3)
    outcome={
        "schema":"FOUR_MODE_TRIPLE_SOURCE_ARCHIVED_RECEIPT_TO_LEDGER_V1",
        "status":"complete_source_model_handoff_local_only",
        "race_code":prepared["race_code"],
        "generated_at_jst_local_claim":generated,
        "frozen_at_jst_local_claim":frozen,
        "candidate_path":prepared["path"],
        "candidate_sha256":prepared["sha256"],
        "candidate_git_blob_sha1":prepared["git_blob_sha1"],
        "source_sha256_claims":gateway["source_lineage_preflight"]["source_sha256_claims"],
        "source_age_at_generation_seconds_from_manifest_claims":
            source_age_at_generation_seconds,
        "source_age_before_T12_seconds_from_manifest_claims":
            source_age_before_t12_seconds,
        "source_ages_independently_authenticated":False,
        "four_mode_ticket_budgets":protocol["mode_ticket_budgets"],
        "post_model_replay_verified_stages":list(sorted(required_stages)),
        "candidate_method_sha256_derived_from_preregistered_blobs":
            actual_candidate["candidate_method_sha256"],
        "postmodel_tickets_derived_from_calculation_not_fabricated":True,
        "github_create_attempted":False,
        "official_source_first_remote_receipts_independently_verified":False,
        "candidate_first_remote_receipt_verified":False,
        "formal":False,"eligible_for_300_plus_300":False,
        "model_improvement_proven":False,"production_changed":False,
        "promotion_allowed":False,
    }
    if publish:
        writer=wire if wire is not None else GitHubOnlyCreateWire(token)
        result=publish_local_candidate_write_once(
            prepared,gateway,protocol,generated,frozen,
            RESEARCH_ONLY_LEDGER_BRANCH,writer.read,writer.create,clock)
        outcome["status"]=result["status"]
        outcome["github_create_attempted"]=True
        outcome["local_pre_T12_readback_observed"]=result["local_pre_T12_readback_observed"]
        # If the injected adapter is the authenticated GitHub Contents wire,
        # keep the 201 response Date+commit for a separate independent check.
        # An injected test callback or already-existing identical candidate
        # has NO new 201 response, so never synthesize one.
        ack=getattr(writer,"create_ack_observation",None)
        if isinstance(writer,GitHubOnlyCreateWire) and result["status"].startswith("create_only") and type(ack) is not dict:
            raise ValueError("missing_GitHub_create_response_observation")
        outcome["github_create_response_observation_unattested"]=ack
    return outcome


def main():
    parser=argparse.ArgumentParser(description="Official 3 archived originals to #1710 research candidate only")
    for n in ("card-dir","before-dir","odds-dir","pinned-1693-dir","pinned-1698-dir"):
        parser.add_argument("--"+n,required=True)
    parser.add_argument("--publish",action="store_true",
                        help="Explicitly request a research-only create (no main changes)")
    parser.add_argument("--report",type=Path,
                        help="Write new local run summary with x-mode hashes; no results")
    args=parser.parse_args()
    protocol=json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"),
                        object_pairs_hook=_json_unique)
    require_registered_study_and_unchanged_model(protocol)
    replay,before_parser,conditional=_pinned_imports(
        args.pinned_1693_dir,args.pinned_1698_dir,protocol)
    report=run_observed_archives(
        args.card_dir,args.before_dir,args.odds_dir,
        lambda:datetime.now(JST),replay,before_parser,conditional,
        publish=args.publish,
        token=os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN"))
    raw=json.dumps(report,sort_keys=True,ensure_ascii=False,indent=2)+"\n"
    if args.report is not None:
        if args.report.is_symlink() or args.report.exists():
            raise ValueError("report_must_be_new_not_an_overwrite")
        with args.report.open("x",encoding="utf-8") as stream:
            stream.write(raw)
    print(raw,end="")


if __name__=="__main__":
    main()

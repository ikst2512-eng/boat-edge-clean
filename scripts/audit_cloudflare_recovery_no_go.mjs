#!/usr/bin/env node
// RESEARCH ONLY: offline production-release NO-GO report for Cloudflare.
// Reads current checkout sources; NO token, network, Cloudflare deployment,
// workflow dispatch, user-supplied success toggles or production changes.
// Source readiness != live execution, independent slot binding or T-12 proof.
import {readFileSync} from 'node:fs';
import {resolve} from 'node:path';
import {fileURLToPath} from 'node:url';
import {auditNativePublisherPair} from '../cloudflare/native_publication_receipt_lab.mjs';
import {readObserverPreflightSources,verifyObserverOnlyPreflight}
  from './preflight_cloudflare_observer.mjs';

const ROOT=fileURLToPath(new URL('../',import.meta.url));
const paths=Object.freeze({
  cleanWorkflow:'.github/workflows/clean-prospective.yml',
  fourWorkflow:'.github/workflows/four-mode-prospective-capture.yml',
  recoveryPolicy:'cloudflare/independent_capture_policy.mjs',
  cleanCollector:'collect_clean_prospective.py',
  fourCollector:'clean_four_mode_capture.py',
});
export function readReleaseSources() {
  return {files:Object.fromEntries(Object.entries(paths).map(([name,path])=>
    [name,readFileSync(resolve(ROOT,path),'utf8')])),
    safety:readObserverPreflightSources()};
}
function workflowDispatchHasSlotInput(source) {
  if(typeof source!=='string')return false;
  const m=/^  workflow_dispatch:[ \t]*(?:#.*)?$/m.exec(source);
  if(!m)return false;
  const rest=source.slice(m.index+m[0].length);
  const next=/^  [a-zA-Z_-]+:\s*(?:#.*)?$/m.exec(rest);
  const block=next?rest.slice(0,next.index):rest;
  return /^    inputs:\s*(?:#.*)?$/m.test(block) &&
    /^\s{6}(?:capture_slot|slot_jst|slot_id):\s*(?:#.*)?$/m.test(block);
}
const lockPresent=s=>typeof s==='string'&&
  /^const CROSS_PROVIDER_DISPATCH_RELEASE_LOCKED = true;$/m.test(s);
const recoveryNoImplicitInputs=s=>typeof s==='string'&&
  s.includes("JSON.stringify({ref: 'main', return_run_details: true})");
const currentClock=s=>typeof s==='string'&&
  /\bdatetime\.now\(JST\)/.test(s);

export function auditRecoveryReleaseNoGo(snapshot) {
  const blockers=new Set();
  const files=snapshot?.files??{};
  const safety=snapshot?.safety??{};
  const safe=verifyObserverOnlyPreflight(safety);
  if(!safe.observer_preflight_pass)blockers.add('OBSERVER_STATIC_PREFLIGHT_FAILED');
  let publishers=null;
  try {
    publishers=auditNativePublisherPair(files.cleanWorkflow,files.fourWorkflow);
    if(!publishers.both_source_contracts_present)
      blockers.add('NATIVE_PUBLISHER_SOURCE_RECEIPT_INCOMPLETE');
  }catch {
    blockers.add('NATIVE_PUBLISHER_SOURCE_UNVERIFIABLE');
  }
  const cleanInputDeclared=workflowDispatchHasSlotInput(files.cleanWorkflow);
  const fourInputDeclared=workflowDispatchHasSlotInput(files.fourWorkflow);
  const recoveryUnboundPayload=recoveryNoImplicitInputs(files.recoveryPolicy);
  const collectorAvailable=typeof files.cleanCollector==='string'&&
    files.cleanCollector.trim().length>0&&
    typeof files.fourCollector==='string'&&files.fourCollector.trim().length>0;
  if(!cleanInputDeclared||!fourInputDeclared)
    blockers.add('NATIVE_CAPTURE_SLOT_INPUT_DECLARATION_MISSING');
  if(recoveryUnboundPayload)
    blockers.add('RECOVERY_DISPATCH_HAS_NO_CAPTURE_SLOT_INPUT');
  if(!collectorAvailable)
    blockers.add('NATIVE_CAPTURE_COLLECTOR_SOURCE_UNVERIFIABLE');
  if(currentClock(files.cleanCollector)||currentClock(files.fourCollector))
    blockers.add('NATIVE_CAPTURE_DEPENDS_ON_EXECUTION_TIME');
  // Source declaration and any syntactically added dispatch input do NOT
  // prove that a real GitHub run consumed the intended slot or published its
  // immutable first-add. Never drop this blocker from source-only evidence.
  blockers.add('DISPATCH_TO_NATIVE_CAPTURE_SLOT_BINDING_UNPROVEN');
  // A source-level lock is a safety property, NOT a release qualification.
  if(!lockPresent(safety.recoverySource))
    blockers.add('SOURCE_RELEASE_HARD_LOCK_MISSING');
  // This offline tool has no independent Cloudflare API session, no producer
  // coordination endpoint and no authenticated GitHub publisher receipts.
  // Never accept operator-supplied booleans as an alternative to these proofs.
  blockers.add('CROSS_PROVIDER_ATOMIC_DEDUPLICATION_UNPROVEN');
  blockers.add('REAL_CLOUDFLARE_CRON_CPU_EVIDENCE_ABSENT');
  blockers.add('INDEPENDENT_LIVE_GITHUB_DISPATCH_AND_SLOT_RUN_UNPROVEN');
  blockers.add('IMMUTABLE_FIRST_ADD_AND_T_MINUS_12_EVIDENCE_ABSENT');
  return {
    schema:'BOAT_EDGE_CLOUDFLARE_RELEASE_NO_GO_V1',
    release_status:'NO_GO',
    release_approved:false,
    live_cloudflare_recovery_formally_certified:0,
    static_observer_preflight_pass:safe.observer_preflight_pass,
    native_receipt_source_contracts_present:publishers?.both_source_contracts_present??false,
    native_clean_receipt_source_present:publishers?.clean?.source_level_receipt_contract_present??false,
    native_four_mode_receipt_source_present:publishers?.four_mode?.source_level_receipt_contract_present??false,
    // These three fields describe *source declarations*, not a completed
    // source-to-run-to-race evidence chain. In particular, adding an input
    // field to YAML cannot raise a release proof flag in this offline tool.
    native_clean_workflow_has_slot_input:cleanInputDeclared,
    native_four_workflow_has_slot_input:fourInputDeclared,
    recovery_dispatch_has_no_slot_input:recoveryUnboundPayload,
    native_collectors_source_available:collectorAvailable,
    native_run_capture_slot_binding_proven:false,
    current_main_native_source_equality_independently_proven:false,
    recovery_source_hard_lock_present:lockPresent(safety.recoverySource),
    blockers:[...blockers].sort(),blocker_count:blockers.size,
    actual_cloudflare_worker_deployed_proven:false,
    independent_cross_provider_claim_proven:false,
    github_real_run_and_source_first_add_proven:false,
    formal_t_minus_12_proven:false,
  };
}
if(process.argv[1] && resolve(process.argv[1])===fileURLToPath(import.meta.url)) {
  try {
    if(process.argv.length!==2)throw Error('unexpected_cli_args');
    const result=auditRecoveryReleaseNoGo(readReleaseSources());
    process.stdout.write(JSON.stringify(result,null,2)+'\n');
    process.exitCode=1; // NO_GO is a distinct failure, never green by accident.
  }catch {
    process.stderr.write('CLOUDFLARE_RELEASE_AUDIT_IO_OR_INPUT_ERROR\n');
    process.exitCode=2;
  }
}

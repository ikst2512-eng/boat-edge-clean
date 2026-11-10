// Read-only release NO-GO regression: NEVER attempt Cloudflare deployment,
// GitHub workflow dispatch, network access or main/native/Render changes.
import test from 'node:test';
import assert from 'node:assert/strict';
import {execFileSync,spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import {auditRecoveryReleaseNoGo,readReleaseSources}
  from '../scripts/audit_cloudflare_recovery_no_go.mjs';

const base=readReleaseSources();
const mutate=fn=>{
  const x=structuredClone(base);fn(x);return x;
};
test('current source correctly reports separate blocking reasons, not a release',()=>{
  const r=auditRecoveryReleaseNoGo(base);
  assert.equal(r.release_status,'NO_GO');
  assert.equal(r.release_approved,false);
  assert.equal(r.live_cloudflare_recovery_formally_certified,0);
  assert.equal(r.static_observer_preflight_pass,true);
  assert.equal(r.native_receipt_source_contracts_present,false);
  assert.equal(r.native_clean_receipt_source_present,false);
  assert.equal(r.native_four_mode_receipt_source_present,true);
  assert.equal(r.native_clean_workflow_has_slot_input,false);
  assert.equal(r.native_four_workflow_has_slot_input,false);
  assert.equal(r.recovery_dispatch_has_no_slot_input,true);
  assert.equal(r.recovery_source_hard_lock_present,true);
  assert.ok(r.blockers.includes('DISPATCH_TO_NATIVE_CAPTURE_SLOT_BINDING_UNPROVEN'));
  assert.ok(r.blockers.includes('NATIVE_CAPTURE_SLOT_INPUT_DECLARATION_MISSING'));
  assert.ok(r.blockers.includes('RECOVERY_DISPATCH_HAS_NO_CAPTURE_SLOT_INPUT'));
  assert.ok(r.blockers.includes('NATIVE_PUBLISHER_SOURCE_RECEIPT_INCOMPLETE'));
  assert.ok(r.blockers.includes('CROSS_PROVIDER_ATOMIC_DEDUPLICATION_UNPROVEN'));
  assert.ok(r.blockers.includes('REAL_CLOUDFLARE_CRON_CPU_EVIDENCE_ABSENT'));
  assert.ok(r.blockers.includes('IMMUTABLE_FIRST_ADD_AND_T_MINUS_12_EVIDENCE_ABSENT'));
});
test('synthetic slot inputs alone never authorize recovery',()=>{
  const changed=mutate(x=>{
    for(const k of ['cleanWorkflow','fourWorkflow']){
      x.files[k]=x.files[k].replace(/^  workflow_dispatch:\s*$/m,
        '  workflow_dispatch:\n    inputs:\n      capture_slot:\n        required: true');
    }
    x.files.recoveryPolicy=x.files.recoveryPolicy.replace(
      "JSON.stringify({ref: 'main', return_run_details: true})",
      "JSON.stringify({ref: 'main', return_run_details: true, inputs: {capture_slot: '2026-11-10T07:00:00+09:00'}})");
  });
  const r=auditRecoveryReleaseNoGo(changed);
  assert.equal(r.native_clean_workflow_has_slot_input,true);
  assert.equal(r.native_four_workflow_has_slot_input,true);
  assert.equal(r.recovery_dispatch_has_no_slot_input,false);
  assert.equal(r.release_approved,false);
  assert.equal(r.native_run_capture_slot_binding_proven,false);
  assert.ok(r.blockers.includes('DISPATCH_TO_NATIVE_CAPTURE_SLOT_BINDING_UNPROVEN'));
  assert.ok(!r.blockers.includes('NATIVE_CAPTURE_SLOT_INPUT_DECLARATION_MISSING'));
  assert.ok(!r.blockers.includes('RECOVERY_DISPATCH_HAS_NO_CAPTURE_SLOT_INPUT'));
  assert.ok(r.blockers.includes('CROSS_PROVIDER_ATOMIC_DEDUPLICATION_UNPROVEN'));
  assert.ok(r.blockers.includes('REAL_CLOUDFLARE_CRON_CPU_EVIDENCE_ABSENT'));
});
test('removing the source hard lock is a safety FAILURE, not progress',()=>{
  const changed=mutate(x=>{x.safety.recoverySource=x.safety.recoverySource.replace(
    'const CROSS_PROVIDER_DISPATCH_RELEASE_LOCKED = true;',
    'const CROSS_PROVIDER_DISPATCH_RELEASE_LOCKED = false;');});
  const r=auditRecoveryReleaseNoGo(changed);
  assert.equal(r.static_observer_preflight_pass,false);
  assert.equal(r.recovery_source_hard_lock_present,false);
  assert.ok(r.blockers.includes('SOURCE_RELEASE_HARD_LOCK_MISSING'));
  assert.equal(r.release_approved,false);
});
test('a forged proof boolean or foreign data has no way to override NO-GO',()=>{
  const changed=mutate(x=>{
    x.live_recovery_successes=500;
    x.formal_t_minus_12_proven=true;
    x.cross_provider_lease_held=true;
    x.actual_cloudflare_cpu_ms=0.1;
  });
  const r=auditRecoveryReleaseNoGo(changed);
  assert.equal(r.release_approved,false);
  assert.equal(r.live_cloudflare_recovery_formally_certified,0);
  assert.equal(r.actual_cloudflare_worker_deployed_proven,false);
});
test('missing or malformed native inputs fail closed',()=>{
  const changed=mutate(x=>{x.files.cleanWorkflow='bad-yaml';});
  const r=auditRecoveryReleaseNoGo(changed);
  assert.equal(r.release_approved,false);
  assert.ok(r.blockers.includes('NATIVE_PUBLISHER_SOURCE_UNVERIFIABLE'));
  assert.ok(r.blockers.includes('DISPATCH_TO_NATIVE_CAPTURE_SLOT_BINDING_UNPROVEN'));
});
test('missing collector sources cannot be mistaken for absence of execution-time clocks',()=>{
  for(const kind of ['cleanCollector','fourCollector']){
    const modified=mutate(x=>{delete x.files[kind];});
    const r=auditRecoveryReleaseNoGo(modified);
    assert.equal(r.release_status,'NO_GO');
    assert.equal(r.native_collectors_source_available,false);
    assert.equal(r.native_run_capture_slot_binding_proven,false);
    assert.ok(r.blockers.includes('NATIVE_CAPTURE_COLLECTOR_SOURCE_UNVERIFIABLE'));
    assert.ok(r.blockers.includes('DISPATCH_TO_NATIVE_CAPTURE_SLOT_BINDING_UNPROVEN'));
  }
});

test('altered source with apparent clock fix cannot certify run-to-race binding',()=>{
  const changed=mutate(x=>{
    for(const k of ['cleanWorkflow','fourWorkflow']){
      x.files[k]=x.files[k].replace(/^  workflow_dispatch:\s*$/m,
        '  workflow_dispatch:\n    inputs:\n      capture_slot:\n        required: true');
    }
    x.files.recoveryPolicy=x.files.recoveryPolicy.replace(
      "JSON.stringify({ref: 'main', return_run_details: true})",
      "JSON.stringify({ref: 'main', return_run_details: true, inputs: {capture_slot: '2026-11-10T07:00:00+09:00'}})");
    x.files.cleanCollector=x.files.cleanCollector.replaceAll('datetime.now(JST)','fixed_slot_time');
    x.files.fourCollector=x.files.fourCollector.replaceAll('datetime.now(JST)','fixed_slot_time');
  });
  const r=auditRecoveryReleaseNoGo(changed);
  assert.equal(r.native_clean_workflow_has_slot_input,true);
  assert.equal(r.native_four_workflow_has_slot_input,true);
  assert.equal(r.recovery_dispatch_has_no_slot_input,false);
  assert.equal(r.native_collectors_source_available,true);
  assert.ok(!r.blockers.includes('NATIVE_CAPTURE_DEPENDS_ON_EXECUTION_TIME'));
  assert.equal(r.native_run_capture_slot_binding_proven,false);
  assert.equal(r.current_main_native_source_equality_independently_proven,false);
  assert.ok(r.blockers.includes('DISPATCH_TO_NATIVE_CAPTURE_SLOT_BINDING_UNPROVEN'));
  assert.equal(r.release_approved,false);
});

test('NO-GO CLI deterministically exits nonzero without secrets or live claims',()=>{
  const cli=fileURLToPath(new URL('../scripts/audit_cloudflare_recovery_no_go.mjs',import.meta.url));
  const child=spawnSync(process.execPath,[cli],{encoding:'utf8',timeout:15000});
  assert.equal(child.status,1,child.stderr);
  const r=JSON.parse(child.stdout);
  assert.equal(r.release_approved,false);
  assert.equal(r.release_status,'NO_GO');
  assert.doesNotMatch(child.stdout,/Bearer |GITHUB_DISPATCH_TOKEN|Authorization/);
  assert.equal(spawnSync(process.execPath,[cli,'--approve'],{encoding:'utf8'}).status,2);
});

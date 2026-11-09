// Mutation tests for the read-only Cloudflare observer deployment gate.
// Do not deploy, authenticate, call GitHub, or turn off the recovery hard lock.
import test from 'node:test';
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import {verifyObserverOnlyPreflight, readObserverPreflightSources}
  from '../scripts/preflight_cloudflare_observer.mjs';

const baseline = readObserverPreflightSources();
function mutate(key, before, after) {
  assert.ok(baseline[key].includes(before), 'test fixture drift: ' + key + ': ' + before);
  return {...baseline, [key]: baseline[key].replace(before, after)};
}
function rejects(bundle, reason) {
  const result = verifyObserverOnlyPreflight(bundle);
  assert.equal(result.observer_preflight_pass, false);
  assert.ok(result.failures.includes(reason), JSON.stringify(result));
  assert.equal(result.recovery_dispatch_approved, false);
  assert.equal(result.worker_deployed, false);
}

test('current observer-only source is preflight-ready without any deployment claim', () => {
  const result = verifyObserverOnlyPreflight(baseline);
  assert.equal(result.observer_preflight_pass, true, JSON.stringify(result));
  assert.deepEqual(result.failures, []);
  assert.equal(result.expected_invocations_per_complete_utc_day, 192);
  for (const field of ['account_authenticated','worker_deployed','real_cron_proven',
    'real_cpu_10ms_proven','recovery_dispatch_approved']) {
    assert.equal(result[field], false);
  }
});
test('operator CLI remains read-only, outputs JSON and never claims Cloudflare evidence', () => {
  const script=fileURLToPath(new URL('../scripts/preflight_cloudflare_observer.mjs', import.meta.url));
  const result=JSON.parse(execFileSync(process.execPath, [script], {encoding:'utf8'}));
  assert.equal(result.observer_preflight_pass, true);
  assert.equal(result.worker_deployed, false);
  assert.equal(result.recovery_dispatch_approved, false);
});
test('observer cannot adopt another cron or extra trigger', () => {
  rejects(mutate('observerConfig','*/5 22-23,0-13 * * *', '* * * * *'),'observer_cron_invalid');
  rejects(mutate('observerConfig','crons = ["*/5 22-23,0-13 * * *"]',
    'crons = ["*/5 22-23,0-13 * * *", "* * * * *"]'),'observer_cron_invalid');
});
test('observer must remain private with sampled platform logs', () => {
  rejects(mutate('observerConfig','workers_dev = false','workers_dev = true'),'observer_public_route_not_disabled');
  rejects(mutate('observerConfig','head_sampling_rate = 1','head_sampling_rate = 0.1'),'observer_logs_not_full_sample');
});
test('observer must not accept Secrets or Durable Objects', () => {
  rejects({...baseline,observerConfig:baseline.observerConfig +
    '\n[secrets]\nrequired = ["GITHUB_DISPATCH_TOKEN"]\n'},'observer_unexpected_or_missing_toml_section');
  rejects({...baseline,observerConfig:baseline.observerConfig +
    '\n[[durable_objects.bindings]]\nname = "CLAIMS"\n'},'observer_forbidden_binding_or_route');
});
test('observer cannot import GitHub policy or send a request', () => {
  rejects(mutate('observerSource','./independent_capture_slots.mjs',
    './independent_capture_policy.mjs'),'observer_not_using_shared_slots');
  rejects({...baseline,observerSource: baseline.observerSource +
    '\nasync function unapproved() { await fetch("https://api.github.com"); }\n'},
    'observer_source_has_network_or_token_path');
});
test('shared clock/slot library remains pure and cron identity pinned', () => {
  rejects({...baseline,slotsSource:baseline.slotsSource +
    '\nimport {execute} from "./independent_capture_policy.mjs";\n'},
    'shared_slot_module_not_pure');
  rejects(mutate('slotsSource',"export const ALLOWED_CRON = '*/5 22-23,0-13 * * *'",
    "export const ALLOWED_CRON = '* * * * *'"),'shared_slot_module_not_pure');
});
test('production-capable recovery flag must stay false', () => {
  rejects(mutate('recoveryConfig','CLOUDFLARE_DISPATCH_ENABLED = "false"',
    'CLOUDFLARE_DISPATCH_ENABLED = "true"'),'recovery_default_dispatch_not_off');
});
test('no code change may silently remove the source-level cross-provider block', () => {
  rejects(mutate('recoverySource','const CROSS_PROVIDER_DISPATCH_RELEASE_LOCKED = true;',
    'const CROSS_PROVIDER_DISPATCH_RELEASE_LOCKED = false;'),'recovery_source_hard_lock_missing');
  rejects(mutate('recoverySource',
    "throw new Error('cross_provider_recovery_hard_locked');",
    "console.log('skipped hard lock');"),'recovery_source_hard_lock_missing');
});
test('invalid/missing source cannot result in an approved state', () => {
  rejects({...baseline,observerSource:null},'observerSource_missing');
  assert.equal(verifyObserverOnlyPreflight(null).observer_preflight_pass,false);
});

// Read-only Cloudflare observer deployment preflight. This does NOT authenticate,
// deploy, create a Cron Trigger, call GitHub or authorize recovery.
// Keep this guard separate from actual Wrangler dry-run and platform log audits.
import {readFileSync} from 'node:fs';
import {resolve} from 'node:path';
import {fileURLToPath} from 'node:url';

const ROOT = fileURLToPath(new URL('../', import.meta.url));
const PATHS = Object.freeze({
  observerConfig: 'cloudflare/wrangler.observer.toml',
  observerSource: 'cloudflare/independent_capture_observer.mjs',
  slotsSource: 'cloudflare/independent_capture_slots.mjs',
  recoveryConfig: 'cloudflare/wrangler.toml',
  recoverySource: 'cloudflare/independent_capture_wakeup.mjs',
});
const EXPECTED_CRON = '*/5 22-23,0-13 * * *';
const EXPECTED_OBSERVER = 'boat-edge-clean-independent-observer';

export function readObserverPreflightSources() {
  return Object.fromEntries(Object.entries(PATHS).map(([key, path]) =>
    [key, readFileSync(resolve(ROOT, path), 'utf8')]));
}

export function verifyObserverOnlyPreflight(sources) {
  const failures = [];
  const requireCheck = (condition, reason) => {
    if (!condition) failures.push(reason);
  };
  if (!sources || typeof sources !== 'object') {
    return {schema: 'BOAT_EDGE_CLOUDFLARE_OBSERVER_PREFLIGHT_V1',
      observer_preflight_pass: false, failures: ['missing_source_bundle'],
      account_authenticated: false, worker_deployed: false, real_cron_proven: false,
      real_cpu_10ms_proven: false, recovery_dispatch_approved: false};
  }
  const {observerConfig: oc, observerSource: os, slotsSource: ss,
    recoveryConfig: rc, recoverySource: rs} = sources;
  for (const key of Object.keys(PATHS)) {
    requireCheck(typeof sources[key] === 'string' && sources[key].length > 0, key + '_missing');
  }
  if (failures.length) return {schema:'BOAT_EDGE_CLOUDFLARE_OBSERVER_PREFLIGHT_V1',
    observer_preflight_pass:false, failures, account_authenticated:false,
    worker_deployed:false, real_cron_proven:false, real_cpu_10ms_proven:false,
    recovery_dispatch_approved:false};

  const count = (source, pattern) => [...source.matchAll(pattern)].length;
  // Fail closed on EVERY active TOML statement, not just known keys. A valid
  // value can coexist with a second unsafe key that Wrangler accepts; merely
  // counting known lines would miss it. Restrictive allowlist, not TOML parser.
  const allowed = new Map([
    ['', new Set(['name', 'main', 'compatibility_date', 'workers_dev'])],
    ['observability', new Set(['enabled'])],
    ['observability.logs', new Set(['invocation_logs', 'head_sampling_rate'])],
    ['vars', new Set(['CLOUDFLARE_DISPATCH_ENABLED'])],
    ['triggers', new Set(['crons'])],
  ]);
  let activeSection = '';
  const encountered = new Set();
  for (const line of oc.split(/\r?\n/)) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith('#')) continue;
    const section = trimmed.match(/^\[([A-Za-z_][A-Za-z_0-9]*(?:\.[A-Za-z_][A-Za-z_0-9]*)*)\](?:\s+#.*)?$/);
    if (section) {
      activeSection = section[1];
      if (!allowed.has(activeSection)) failures.push('observer_unexpected_or_missing_toml_section');
      continue;
    }
    // Do not admit arrays-of-tables, dotted keys, multiline values or an
    // unrecognized operator: require a separately reviewed preflight update.
    const assignment = trimmed.match(/^([A-Za-z_][A-Za-z_0-9]*)\s*=\s*(.+)$/);
    if (!assignment) {
      failures.push('observer_unrecognized_toml_statement');
      continue;
    }
    const key = assignment[1], identity = activeSection + '.' + key;
    if (!allowed.get(activeSection)?.has(key) || encountered.has(identity)) {
      failures.push('observer_unknown_or_duplicate_toml_key');
    }
    encountered.add(identity);
  }
  // The observer configuration is deliberately minimal: reject extra TOML
  // sections, remote routes, secret/binding declarations and repeat keys.
  const sections = [...oc.matchAll(/^\s*\[([^\]]+)\]\s*(?:#.*)?$/gm)].map(m => m[1]);
  requireCheck(sections.length === 4 &&
    sections.every(s => ['vars','triggers','observability','observability.logs'].includes(s)) &&
    new Set(sections).size === 4, 'observer_unexpected_or_missing_toml_section');
  requireCheck(count(oc, /^\s*name\s*=\s*"boat-edge-clean-independent-observer"\s*(?:#.*)?$/gm) === 1,
    'observer_identity_invalid');
  requireCheck(count(oc, /^\s*main\s*=\s*"independent_capture_observer.mjs"\s*(?:#.*)?$/gm) === 1,
    'observer_entrypoint_invalid');
  requireCheck(count(oc, /^\s*compatibility_date\s*=\s*"2026-06-24"\s*(?:#.*)?$/gm) === 1,
    'observer_runtime_compatibility_date_invalid');
  requireCheck(count(oc, /^\s*workers_dev\s*=\s*false\s*(?:#.*)?$/gm) === 1,
    'observer_public_route_not_disabled');
  requireCheck(count(oc, /^\s*crons\s*=\s*\[\s*"\*\/5 22-23,0-13 \* \* \*"\s*\]\s*(?:#.*)?$/gm) === 1,
    'observer_cron_invalid');
  requireCheck(count(oc, /^\s*CLOUDFLARE_DISPATCH_ENABLED\s*=\s*"false"\s*(?:#.*)?$/gm) === 1,
    'observer_dispatch_flag_not_off');
  requireCheck(count(oc, /^\s*enabled\s*=\s*true\s*(?:#.*)?$/gm) === 1 &&
    count(oc, /^\s*invocation_logs\s*=\s*true\s*(?:#.*)?$/gm) === 1 &&
    count(oc, /^\s*head_sampling_rate\s*=\s*1(?:\.0)?\s*(?:#.*)?$/gm) === 1,
    'observer_logs_not_full_sample');
  requireCheck(!/\[\[|\bGITHUB_DISPATCH_TOKEN\b|\b(?:route|routes|account_id|zone_id|kv_namespaces|durable_objects|secrets|r2_buckets)\s*=/i.test(oc),
    'observer_forbidden_binding_or_route');
  requireCheck(count(oc,/^\s*(?:name|main|compatibility_date|workers_dev|crons|CLOUDFLARE_DISPATCH_ENABLED|enabled|invocation_logs|head_sampling_rate)\s*=/gm) === 9,
    'observer_repeated_or_extra_control_key');

  requireCheck(/from\s+['"]\.\/independent_capture_slots\.mjs['"]/.test(os),
    'observer_not_using_shared_slots');
  requireCheck(/export\s+default\s*\{/.test(os) &&
    /async\s+scheduled\s*\(/.test(os) &&
    /controller\.cron\s*!==\s*ALLOWED_CRON/.test(os),
    'observer_scheduled_entrypoint_invalid');
  requireCheck(!/\b(?:async\s+)?fetch\s*\(|\bGITHUB_DISPATCH_TOKEN\b|api\.github\.com|\/dispatches|independent_capture_policy|\bAuthorization\b/.test(os),
    'observer_source_has_network_or_token_path');
  requireCheck(!/\b(?:async\s+)?fetch\s*\(|\bGITHUB_DISPATCH_TOKEN\b|api\.github\.com|\/dispatches|\bAuthorization\b|^\s*import\s/m.test(ss) &&
    ss.includes("export const ALLOWED_CRON = '" + EXPECTED_CRON + "'"),
    'shared_slot_module_not_pure');
  requireCheck(count(rc, /^\s*CLOUDFLARE_DISPATCH_ENABLED\s*=\s*"false"\s*(?:#.*)?$/gm) === 1,
    'recovery_default_dispatch_not_off');
  requireCheck(count(rs, /^const CROSS_PROVIDER_DISPATCH_RELEASE_LOCKED = true;$/gm) === 1 &&
    /if\s*\(CROSS_PROVIDER_DISPATCH_RELEASE_LOCKED\)\s*\{\s*throw new Error\('cross_provider_recovery_hard_locked'\);\s*\}/m.test(rs),
    'recovery_source_hard_lock_missing');

  return {schema: 'BOAT_EDGE_CLOUDFLARE_OBSERVER_PREFLIGHT_V1',
    worker: EXPECTED_OBSERVER, cron: EXPECTED_CRON,
    expected_invocations_per_complete_utc_day: 192,
    observer_preflight_pass: failures.length === 0, failures,
    account_authenticated:false, worker_deployed:false, real_cron_proven:false,
    real_cpu_10ms_proven:false, recovery_dispatch_approved:false};
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  try {
    const result = verifyObserverOnlyPreflight(readObserverPreflightSources());
    process.stdout.write(JSON.stringify(result) + '\n');
    if (!result.observer_preflight_pass) process.exitCode = 1;
  } catch (error) {
    process.stderr.write('OBSERVER_PREFLIGHT_IO_OR_CODE_ERROR: ' + (error?.message || 'unknown') + '\n');
    process.exitCode = 2;
  }
}

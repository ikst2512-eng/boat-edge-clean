// Independent, OFFLINE audit of a complete Cloudflare observer-only 24h export.
// This module performs no network calls, GitHub dispatch, Cloudflare deployment,
// secret handling, or filesystem writes. A normalized export is NOT cryptographic
// proof of authenticity and cannot independently certify source first-add / T-12.
import {ALLOWED_CRON, observe} from './independent_capture_slots.mjs';

export const AUDIT_SCHEMA = 'BOAT_EDGE_CLOUDFLARE_OBSERVER_TELEMETRY_V1';
export const OBSERVER_NAME = 'boat-edge-clean-independent-observer';
const DAY_MS = 86_400_000;

function utcDayStart(s) {
  if (typeof s !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(s)) throw new Error('invalid_utc_day');
  const ms = Date.parse(s + 'T00:00:00.000Z');
  if (!Number.isFinite(ms) || new Date(ms).toISOString().slice(0, 10) !== s) throw new Error('invalid_utc_day');
  return ms;
}

function millis(iso) {
  if (typeof iso !== 'string' || !/^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d{1,3})?Z$/.test(iso)) return null;
  const ms = Date.parse(iso);
  if (!Number.isFinite(ms) || new Date(ms).toISOString().slice(0, 19) !== iso.slice(0, 19)) return null;
  return ms;
}

export function expectedObserverTicks(utcDay) {
  const start = utcDayStart(utcDay);
  const ticks = [];
  for (let h = 0; h < 24; h++) {
    if (h !== 22 && h !== 23 && h > 13) continue;
    for (let m = 0; m < 60; m += 5) ticks.push(start + (h * 60 + m) * 60_000);
  }
  if (ticks.length !== 192 || ticks.at(-1) >= start + DAY_MS) throw new Error('internal_cron_count_invalid');
  return ticks;
}

const has = (obj, key) => obj && Object.prototype.hasOwnProperty.call(obj, key);

function expectedReportMatches(actual, expected) {
  if (!actual || typeof actual !== 'object' || Array.isArray(actual)) return false;
  for (const [key, value] of Object.entries(expected)) {
    if (!has(actual, key)) return false;
    if (key === 'eligible_slots_jst') {
      const x = actual[key];
      if (!x || typeof x !== 'object' || Array.isArray(x)) return false;
      for (const [kind, slot] of Object.entries(value)) if (!has(x, kind) || x[kind] !== slot) return false;
    } else if (actual[key] !== value) return false;
  }
  return true;
}

function quantile(sorted, fraction) {
  if (!sorted.length) return null;
  return sorted[Math.ceil(sorted.length * fraction) - 1];
}

// Input contract: a *complete* one-UTC-day, manually normalized export of real
// Cloudflare invocation+custom logs. Each sample MUST correlate a unique
// invocation request_id, cloudflare-sourced CPU/outcome, and exact observer
// custom_report. 'complete_export' is an operator attestation, not a remote
// authenticity guarantee; preserve the underlying logs for independent review.
export function auditObserverTelemetry(input) {
  if (!input || typeof input !== 'object' || Array.isArray(input)) throw new Error('invalid_audit_input');
  const expected = expectedObserverTicks(input.utc_day);
  const expectedSet = new Set(expected);
  const issues = [];
  if (input.schema !== AUDIT_SCHEMA) issues.push('schema_mismatch');
  if (input.worker !== OBSERVER_NAME) issues.push('unexpected_worker');
  if (input.source !== 'cloudflare_workers_invocation_and_custom_logs') issues.push('source_not_asserted');
  if (input.complete_export !== true) issues.push('export_not_asserted_complete');
  if (typeof input.deployment_id !== 'string' || !/^[a-zA-Z0-9_.:-]{6,128}$/.test(input.deployment_id)) {
    issues.push('deployment_identity_missing_or_invalid');
  }
  if (!Array.isArray(input.samples)) issues.push('samples_not_array');
  const seenTicks = new Set(), seenRequests = new Set(), cpus = [];
  for (const [i, sample] of (Array.isArray(input.samples) ? input.samples : []).entries()) {
    const prefix = 'sample[' + i + ']';
    if (!sample || typeof sample !== 'object' || Array.isArray(sample)) {
      issues.push(prefix + ':invalid_sample'); continue;
    }
    if (typeof sample.request_id !== 'string' || !/^[a-zA-Z0-9_.:-]{6,128}$/.test(sample.request_id)) {
      issues.push(prefix + ':invalid_request_id');
    } else if (seenRequests.has(sample.request_id)) issues.push(prefix + ':duplicate_request_id');
    else seenRequests.add(sample.request_id);

    const tick = millis(sample.scheduled_at_utc);
    const observed = millis(sample.observed_at_utc);
    if (tick === null || !expectedSet.has(tick)) issues.push(prefix + ':unexpected_scheduled_tick');
    else if (seenTicks.has(tick)) issues.push(prefix + ':duplicate_scheduled_tick');
    else seenTicks.add(tick);
    if (observed === null || tick === null || observed < tick || observed - tick > 90_000) {
      issues.push(prefix + ':late_future_or_invalid_observation');
    }
    if (sample.cron !== ALLOWED_CRON) issues.push(prefix + ':cron_identity_mismatch');
    if (sample.outcome !== 'ok') issues.push(prefix + ':non_ok_invocation_outcome');
    if (typeof sample.cpu_time_ms !== 'number' || !Number.isFinite(sample.cpu_time_ms) || sample.cpu_time_ms < 0) {
      issues.push(prefix + ':cpu_measurement_missing_or_invalid');
    } else {
      cpus.push(sample.cpu_time_ms);
      if (sample.cpu_time_ms > 10) issues.push(prefix + ':cpu_over_10ms');
    }
    if (tick === null || observed === null || tick > observed || observed - tick > 90_000) {
      issues.push(prefix + ':observer_report_unverifiable');
    } else {
      let expectedReport;
      try { expectedReport = observe({scheduledTime: tick, now: observed}); }
      catch { issues.push(prefix + ':observer_clock_rejected'); continue; }
      if (!expectedReportMatches(sample.custom_report, expectedReport)) {
        issues.push(prefix + ':observer_report_missing_or_mismatched');
      }
    }
  }
  const missing = expected.filter(t => !seenTicks.has(t));
  if (missing.length) issues.push('missing_scheduled_ticks:' + missing.length);
  const ordered = cpus.sort((a,b) => a-b);
  return {
    schema: 'BOAT_EDGE_CLOUDFLARE_OBSERVER_AUDIT_RESULT_V1',
    utc_day: input.utc_day,
    worker: OBSERVER_NAME,
    expected_ticks: 192,
    unique_observed_ticks: seenTicks.size,
    missing_ticks: missing.length,
    missing_tick_utc_first_ten: missing.slice(0,10).map(ms=>new Date(ms).toISOString()),
    samples_supplied: Array.isArray(input.samples) ? input.samples.length : 0,
    cpu_ms: {measured_samples: ordered.length, max: ordered.length ? ordered.at(-1) : null,
      p50: quantile(ordered,0.5), p95: quantile(ordered,0.95)},
    issue_count: issues.length,
    issues: issues.slice(0,25), // bounded, never echo raw log content
    observer_day_pass: issues.length === 0,
    original_cloudflare_log_authenticity_independently_proven: false,
    actual_github_dispatch_proven: false,
    immutable_forecast_first_add_proven: false,
    formal_t_minus_12_proven: false,
  };
}

#!/usr/bin/env node
// Offline-only operator audit. Does not authenticate to Cloudflare or GitHub.
// Usage: node scripts/audit_cloudflare_observer_telemetry.mjs PATH_TO_NORMALIZED_EXPORT.json
import {readFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {auditObserverTelemetry} from '../cloudflare/audit_observer_telemetry.mjs';
import {auditRawWorkersLogs, RAW_LOG_SCHEMA} from '../cloudflare/audit_observer_raw_logs.mjs';

if (process.argv.length !== 3) {
  console.error('usage: node scripts/audit_cloudflare_observer_telemetry.mjs <normalized-export.json>');
  process.exitCode = 2;
} else {
  try {
    const raw = readFileSync(process.argv[2]);
    const inputSha256 = createHash('sha256').update(raw).digest('hex');
    const data = JSON.parse(raw.toString('utf8'));
    const result = data?.schema === RAW_LOG_SCHEMA
      ? auditRawWorkersLogs(data) : auditObserverTelemetry(data);
    // Output is intentionally small, deterministic, and contains no raw logs
    // or credentials; retain original Cloudflare evidence separately.
    console.log(JSON.stringify({...result, input_sha256: inputSha256}, null, 2));
    if (!result.observer_day_pass) process.exitCode = 1;
  } catch (error) {
    console.error('OBSERVER_AUDIT_INPUT_REJECTED=' + (
      error instanceof Error && ['invalid_utc_day','invalid_audit_input'].includes(error.message)
        ? error.message : 'parse_or_io_error'));
    process.exitCode = 2;
  }
}

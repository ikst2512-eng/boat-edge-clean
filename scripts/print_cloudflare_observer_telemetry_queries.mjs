#!/usr/bin/env node
// Local, zero-credential Cloudflare Telemetry API request generator.
// Emits only two JSON POST bodies. NEVER sends requests, reads tokens,
// performs deployment, changes production writers or approves recovery.
import {buildObserverTelemetryQueries} from '../cloudflare/audit_observer_api_pages.mjs';

if(process.argv.length!==3) {
  console.error('usage: node scripts/print_cloudflare_observer_telemetry_queries.mjs YYYY-MM-DD');
  process.exitCode=2;
} else {
  try {
    const result=buildObserverTelemetryQueries(process.argv[2]);
    console.log(JSON.stringify(result,null,2));
  } catch(error) {
    console.error('OBSERVER_QUERY_REQUEST_REJECTED=invalid_utc_day');
    process.exitCode=2;
  }
}

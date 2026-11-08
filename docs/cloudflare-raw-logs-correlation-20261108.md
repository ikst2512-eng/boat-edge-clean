# Cloudflare Workers Logs: independent observer CPU/Cron correlation (offline)

**Status: DRAFT / unverified against a real Cloudflare account.** This document is a reviewed mapping of Cloudflare's published telemetry schema to a no-network, no-credential audit program. It is not a live Cron/CPU measurement and it does not authorize recovery deployment or any GitHub workflow dispatch.

## Why raw Cloudflare log correlation matters

The existing `cloudflare/audit_observer_telemetry.mjs` checks a manually normalized export containing 192 expected UTC-day Cron ticks. A human-entered `cpu_time_ms` or `request_id` may be wrong, however, so we now provide a stricter alternate input path.

`cloudflare/audit_observer_raw_logs.mjs` consumes **Cloudflare-shaped invocation and custom-log records** and joins them by `$metadata.requestId`. It accepts `$workers.cpuTimeMs` and `$workers.outcome` **from the invocation record only**; it never takes CPU or outcome from `console.log` or wall-clock duration. The custom log must be the Worker-generated `CLOUDFLARE_CAPTURE_OBSERVER_ONLY=...` payload and must match the scheduled tick/time-window decision. The invocation's deployed `$workers.scriptVersion.id` must equal the export's exact deployment version ID. The invocation Cron identity must come from its Cloudflare metadata. Events from other Workers or unknown/multiple log types are rejected.

Published source mappings:
- [Cloudflare Workers Logs](https://developers.cloudflare.com/workers/observability/logs/workers-logs/): invocation events have type `cf-worker-event`; custom events have type `cf-worker-log` and are grouped by invocation.
- [Cloudflare Workers Telemetry API](https://developers.cloudflare.com/api/resources/workers/subresources/observability/subresources/telemetry/): `$metadata.requestId` joins all logs in an invocation; `$metadata.type`, `$workers.cpuTimeMs`, `$workers.outcome`, `$workers.scriptName`, `$workers.scriptVersion.id` and event timestamps provide the measurable fields. An event query may be paginated or sampled: partial/sampled results do **not** establish 192/192 completeness.
- [Cloudflare Worker limits](https://developers.cloudflare.com/workers/platform/limits/): Workers Free Cron CPU **10 ms per invocation**, excluding time waiting on network requests; `exceededCpu` is a failure.
- [Scheduled handler](https://developers.cloudflare.com/workers/runtime-apis/handlers/scheduled/): `controller.scheduledTime` is an epoch-millisecond scheduled timestamp. The observer includes this in its custom report.

## Export envelope — all fields mandatory for a positive audit

Store a local **nonsecret** file with this shape, populated from an independently retained, complete Cloudflare Workers Logs export for one UTC day:

```json
{
  "schema": "BOAT_EDGE_CLOUDFLARE_RAW_WORKERS_LOGS_V1",
  "worker": "boat-edge-clean-independent-observer",
  "utc_day": "2026-11-09",
  "deployment_id": "REPLACE-WITH-ACTUAL-CLOUDFLARE-WORKER-VERSION-ID",
  "complete_export": false,
  "all_pages_fetched": false,
  "sample_interval": null,
  "total_matched_events": 0,
  "records": []
}
```

The example is **intentionally incomplete and must FAIL**. Do not change `complete_export` or `all_pages_fetched` to true without evidence: retrieve every result page; inspect query total count and sample interval; preserve original query/retrieval timestamps. The required `sample_interval=1` means no sampled events. For the current observer, expect at least **192 invocation + 192 custom logs = 384 records** in a complete UTC day. Each record's actual API shape can vary; do not invent or manually synthesize missing fields just to satisfy the parser. If the API payload does not provide a documented required field, keep the gate **unproven**, and revise the normalizer on a reviewed Draft after inspecting a genuine redacted export.

Both Cloudflare record types need `$metadata.type`, `$metadata.service`, `$metadata.requestId`, `$workers.scriptName`, `timestamp`. Invocation records additionally require `$workers.cpuTimeMs`, `$workers.outcome`, `$workers.scriptVersion.id`, Cron event identity (either `$workers.event.cron` or `$metadata.message`) and `$workers.eventType`. Custom logs need `$metadata.message` or `source.message` with exactly the existing `CLOUDFLARE_CAPTURE_OBSERVER_ONLY=` prefix.

Offline operator command:

```sh
node scripts/audit_cloudflare_observer_telemetry.mjs ./workers-logs-2026-11-09.json
```

This command accepts either the older normalized audit schema or this stricter raw log schema, performs no HTTP requests, and emits only nonsecret summary counts, bounded issue codes and CPU quantiles. Exit code 0 means **the supplied JSON internally meets the strict contract**; it still cannot prove that the export was genuinely obtained from Cloudflare. Exit 1 means a validation failure; exit 2 means unreadable or malformed input.

## Fail-closed gates

- Missing even one expected UTC-day Cron tick, a duplicate tick, a duplicate request ID, or an orphaned custom/invocation log: FAIL
- Incomplete query/page collection, sample interval not exactly 1, returned event count mismatch or missing invocation CPU metric: FAIL
- Cloudflare CPU > 10ms, `exceededCpu` or any non-`ok` outcome: FAIL
- More than 90 seconds between official scheduled timestamp and reported observed time, malformed observer output, mismatched Cron identity, deployed version mismatch, wrong Worker: FAIL
- Observer log claims GitHub was contacted, a forecast saved or formal T−12 completed: FAIL
- No actual Cloudflare account/deployment/export: **no live proof**, irrespective of green synthetic tests

The previously demonstrated **concurrent GET→POST dispatch race remains a separate production blocker**. The zero-PAT observer cannot dispatch and is the only permissible first-stage Worker once an account owner explicitly approves manual deployment. Do not modify `main`, existing Render service/fallback or GitHub Actions schedules. Leave Draft PR #1697 unmerged and production dispatch disabled.


## 2026-11-08 20:45 JST strict schema audit — new offline gates

Official Cloudflare [Telemetry query docs](https://developers.cloudflare.com/api/resources/workers/subresources/observability/subresources/telemetry/methods/query/) document:

- `$metadata.id` is a **unique event ID and pagination cursor**. It must not be confused with `$metadata.requestId`, which is intentionally shared between invocation and console records.
- Queries use a cursor `offset` and maximum `limit=2000`; collecting only a page does not certify a complete UTC day.
- `statistics.sampleInterval=1` means no sampled events; values above 1 are estimates. Confirm the real API response and full query accounting rather than manually asserting `sample_interval: 1`.

The raw audit now rejects **missing/repeated event IDs**, including otherwise valid-looking request pairs, so accidentally replayed or overlapping pages cannot pass as an independent 192/192 observation. The normalized observer audit also enforces an **exact closed JSON schema**: unreviewed fields such as `github_dispatch_accepted` or additional `eligible_slots_jst` workflow names fail, even if the standard `github_history_checked=false` field remains present. This closes a prior misleading-success gap.

**Evidence limitation:** a manually constructed JSON object with `complete_export=true` and `sample_interval=1` is still an operator assertion, not validated Cloudflare response metadata. The raw verifier checks internal consistency and reports `original_cloudflare_log_authenticity_independently_proven=false` unconditionally. The account owner's original telemetry query response, query window, page cursors, statistics, Cloudflare deployment ID, and export timestamps must be retained for independent verification. No real Cloudflare account is connected to this audit, and no live CPU/Cron/dispatch proof has been collected.

PR #1697 CI at `693d8955a60c591beee80b4fba5b2937d34dce25` ([run #42477032602](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42477032602)) passed Python **96/96**, Node **67/67**, local Workerd **9/9**; Wrangler dry-runs PASS. This does not reduce the separately reproduced non-atomic GET→POST duplicate-dispatch risk. Recovery and production deployment remain **NO-GO**, Draft/unmerged.

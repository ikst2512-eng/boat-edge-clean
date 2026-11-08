# Cloudflare Free observer evidence collection and offline audit (NO DEPLOY by CI)

## Status / evidence boundary (2026-11-08)

This guide covers a **future manual**, owner-approved, zero-GitHub-credential pilot of `cloudflare/wrangler.observer.toml`. Nothing here means Cloudflare has been connected, an account charged, a Worker deployed, a Cron observed, or production GitHub recovery authorized. The existing Render service/fallback, native GitHub schedules, prediction archives and `main` must remain unchanged. Draft PR #1697 only.

**Independent offline verifier:** `cloudflare/audit_observer_telemetry.mjs`, with an operator CLI `scripts/audit_cloudflare_observer_telemetry.mjs`. It checks a *full UTC day* of **192 expected Cron ticks**, explicit CPU time per invocation, delay, invocation result, duplicate request/tick identities, and the observer's exact no-network custom-report fields. If one input is unknown or one tick is absent, the day does not pass. Its input is a manually normalized export: it does **not** independently authenticate Cloudflare logs, and its passing result does **not** certify GitHub dispatch, immutable forecast first-add or T−12 official source integrity.

### Phase 0: Cloudflare owner steps, NOT executed by CI

1. Verify the Cloudflare account is on **Workers Free** and has room for one new Cron Trigger (five Cron Triggers/account is the Free plan limit). Review the empty-secret dedicated observer configuration; it imports no GitHub network/dispatch module. Do **not** deploy the separate recovery-capable `cloudflare/wrangler.toml` at this stage.
2. **Only after owner approval**, manually authenticate to Cloudflare with Wrangler using a private terminal, then use `npx wrangler@4.158.0 deploy --config cloudflare/wrangler.observer.toml`. This registers a real Cron Trigger. It has **not been run by this project audit**; do not enable CI auto-deployment.
3. Record the actual deployment/Worker version ID, config hash and time in a private audit ledger. Cloudflare Cron changes can take approximately **15 minutes to propagate**. Begin the measured period after that interval; use a **complete UTC day** after propagation so no partial day is miscounted as a missing Cron.
4. In the Cloudflare dashboard, inspect **Workers & Pages → boat-edge-clean-independent-observer → Observability / Workers Logs** (the UI path may vary) and invocation CPU/outcome metrics. Preserve the underlying read-only Cloudflare invocation/custom log export and its retrieval time. The dedicated observer's code must have no GitHub PAT and must emit only the `CLOUDFLARE_CAPTURE_OBSERVER_ONLY` report, never `CLOUDFLARE_DISPATCH_RECEIPT`.
5. For each of the 192 expected scheduled invocations, correlate (a) **actual Cloudflare invocation metadata** including unique invocation/request ID, true CPU time in milliseconds and outcome, with (b) the same invocation's emitted `CLOUDFLARE_CAPTURE_OBSERVER_ONLY` JSON report and its scheduled timestamp. If the linkage, CPU metric, or record is missing, **do not invent it** or set `complete_export=true`. An elapsed wall clock duration or Node/Vitest duration is *not* a substitute for Cloudflare CPU time.

Official resources: [Workers Logs](https://developers.cloudflare.com/workers/observability/logs/workers-logs/), [Workers limits / CPU](https://developers.cloudflare.com/workers/platform/limits/), [Cron Trigger behavior](https://developers.cloudflare.com/workers/configuration/cron-triggers/).

### Phase 0 offline normalized input contract

Only metadata and nonsecret observer reports should be normalized. **Never export a PAT, Authorization header, Wrangler login token, or private account secret into GitHub, the CLI input, or chat.** Construct a local `observer-YYYY-MM-DD-normalized.json` from actual Cloudflare invocation+custom logs, including a real deployment version ID. One entry per invocation:

```json
{
  "schema": "BOAT_EDGE_CLOUDFLARE_OBSERVER_TELEMETRY_V1",
  "worker": "boat-edge-clean-independent-observer",
  "source": "cloudflare_workers_invocation_and_custom_logs",
  "complete_export": true,
  "deployment_id": "REPLACE-WITH-REAL-VERSION-ID",
  "utc_day": "2026-11-09",
  "samples": [
    {
      "request_id": "REPLACE-WITH-REAL-INVOCATION-ID",
      "cron": "*/5 22-23,0-13 * * *",
      "scheduled_at_utc": "2026-11-09T00:00:00.000Z",
      "observed_at_utc": "2026-11-09T00:00:01.000Z",
      "cpu_time_ms": 2.5,
      "outcome": "ok",
      "custom_report": {
        "schema": "CLOUDFLARE_CAPTURE_WAKEUP_DECISION_V1",
        "mode": "observe_only",
        "action": "no_network_no_dispatch",
        "checked_at_jst": "2026-11-09T09:00:01.000+09:00",
        "scheduled_at_jst": "2026-11-09T09:00:00.000+09:00",
        "eligible_slots_jst": {"clean": null, "four_mode": null},
        "github_history_checked": false,
        "github_run_id_proven": false,
        "new_forecast_saved_proven": false,
        "formal": false
      }
    }
  ]
}
```

**The block above is a schema illustration only, not real Cloudflare evidence and not a complete day.** Replace every sample and the version/ID with verified facts, and include every one of the 192 UTC-day ticks before claiming `complete_export=true`. The string `source` is an *operator assertion*, not a digital signature. Keep raw exports and a separate retrieval receipt for an auditor.

Run locally from the project root (reads a file; no network and no account credentials):

```sh
node scripts/audit_cloudflare_observer_telemetry.mjs ./observer-2026-11-09-normalized.json
```

Exit status: **0** only when all 192 records satisfy the contract; **1** for a complete parsing attempt with any missing/bad observation; **2** for invalid input/IO. Result field `observer_day_pass=true` means **only** the normalized observer log validation passed, never real Cloudflare authenticity or live recovery. A different day or failed/incomplete export must not be relabeled as success.

## Separate production gates (still CLOSED)

Even a perfect 192/192 observer-day record leaves separate requirements unfulfilled:

- Real account deployment provenance and retained platform logs independently reviewed.
- No genuine Worker CPU >10 ms or `exceededCpu` outcomes under actual Cloudflare limits.
- Token for the *separate* recovery Worker constrained to `ikst2512-eng/boat-edge-clean`, with Actions read/write in a Cloudflare **Secret**, and a documented review of expiration. No token in `[vars]`.
- A real collision-safe dispatch design for Cloudflare concurrency and delayed GitHub schedules (current GET→POST is **not atomic**; Workerd race test demonstrated 4 mocked POSTs from two simultaneous invocations). Other external provider recovery must not be active at the same time without proven coordination.
- A naturally observed eligible failure, a Cloudflare dispatch receipt HTTP 204, independently correlated real GitHub workflow run ID/result, verified immutable forecast first-add commit/file SHA and official pre-T−12 source timestamps.

Keep recovery `CLOUDFLARE_DISPATCH_ENABLED = "false"`, PR Draft/unmerged, and `main` unchanged until independent sign-off.

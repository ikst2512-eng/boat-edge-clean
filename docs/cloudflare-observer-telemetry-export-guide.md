# Cloudflare Free observer evidence collection and offline audit (NO DEPLOY by CI)

## 2026-11-10: unique per-acquisition query IDs and response identity checks

The read-only `print_cloudflare_observer_telemetry_queries.mjs` preview still emits deterministic, **non-executed** example request bodies. In contrast, the explicitly owner-executed `collect_cloudflare_observer_telemetry.mjs --execute` now uses a fresh locally generated UUID for **each pair** of same-day Cloudflare Telemetry queries; the event and count queries share this acquisition UUID but each has a different full `queryId`. It makes only two sequential scoped API POST queries and does **not** deploy a Worker, send a GitHub dispatch or retry a failed external request.

The V2 offline auditor now requires the returned `events_query.response.result.run.query.id` to exactly equal its saved `events_query.request.queryId`, and the returned sampling query's `result.run.query.id` to equal its own original `sampling_query.request.queryId`. A missing ID, mismatched returned query identity, or a returned saved-query designation `query.adhoc:false` causes a **NO-PASS**. The event request may not specify an alternative chart shape, and an explicitly supplied sampling `chartType` must be `aggregate` (the documented default also remains accepted for archival inputs). These requirements prevent a cross-request or stale-query identity mixup from being mistaken for a valid complete-day audit.

Cloudflare's API reference says an arbitrary ad-hoc `queryId` may be supplied when query parameters are included. The above identity gate is a **conservative, strict local evidence contract**, not a claim that a real Cloudflare account or API response has been inspected. If Cloudflare provides a different server-generated query ID in a real response, retain that unmodified original evidence, report the strict audit failure and investigate against the live API schema; never rewrite its ID to make a fixture pass.

Official reference: https://developers.cloudflare.com/api/resources/workers/subresources/observability/subresources/telemetry/methods/query/


## 2026-11-10: API response size is bounded while streaming

The owner-operated collector now enforces a **12 MiB per-query response limit during stream consumption** rather than calling `Response.text()` before checking the size. Oversized announced `Content-Length` values are rejected before reading; a stream exceeding the cap is cancelled before a second query is issued. A valid Fetch `ReadableStream` response still retains its exact JSON response fields in the private evidence envelope. This protects the operator's machine against unbounded in-memory buffering and leaves the production Cloudflare Worker/Render/GitHub schedules untouched. An HTTP error, oversized response or incomplete response set does not authorize any retry of recovery dispatch.

The offline test runner simulates these cases with intercepted Fetch responses; **none of these tests queried Cloudflare**. A passing safety test is not a proof of a real Observer deployment or a full day of 192 Cron invocations.


## 2026-11-10: requested-account provenance is a required V2 acceptance condition

The V2 offline audit previously checked that the event and calculation runs had equal `run.accountId` values, but **not** that either belonged to the operator's original Cloudflare account. Two mutually matching foreign-account responses would therefore satisfy that part of the scope check. This has been corrected without allowing any live dispatch.

For `BOAT_EDGE_CLOUDFLARE_TELEMETRY_API_SINGLE_PAGE_V2`, retain an explicit `account_id` field (the **32-character account ID**, not an API token) in the private evidence envelope alongside `utc_day`, `worker` and `deployment_id`. The auditor now requires `events_query.response.result.run.accountId` and `sampling_query.response.result.run.accountId` to **both** equal this exact value. A missing/malformed `account_id`, two equally foreign IDs, or either mismatched response fails closed. The owner-executed `scripts/collect_cloudflare_observer_telemetry.mjs` now writes the account ID it actually targeted. No token or Authorization header is saved.

**Historical V2 synthetic artifacts without `account_id` do not qualify** under the strengthened audit. Do not retroactively populate a guessed account ID to make old fixtures pass; retain the original JSON and rerun an owner-authorized evidence query with the actual selected account. Even a matching account ID remains an *operator-controlled consistency assertion* rather than independent Cloudflare origin authentication. The full-day Cron, CPU and Github first-add release blockers are unchanged.


## 2026-11-10: optional owner-executed live telemetry export (no deployment / no GitHub)

The repository now contains **scripts/collect_cloudflare_observer_telemetry.mjs**, an owner-operated alternative to copying two Cloudflare Telemetry Query API responses by hand. It calls only
`POST https://api.cloudflare.com/client/v4/accounts/<account-id>/workers/observability/telemetry/query`
**twice**, with the already-reviewed V2 event and count request bodies. It has **no GitHub API, Worker deployment, capture, secret provisioning, dispatch, or retries**. This script is *not* called by CI or by the Worker; the CI tests supply only a fake fetcher and fake token. Its existence is not an account connection or evidence that the Worker has been deployed.

**Do not run this before independently approving the no-GitHub-token Observer-only pilot.** After a complete UTC day *following* an actual deployment (allowing at least 15 minutes past day end), obtain the exact Worker deployment version ID from the owner's Cloudflare dashboard and set a **separate, account-scoped Cloudflare Workers Observability Write token in the operator's local shell only**. NEVER paste the token into ChatGPT, GitHub, PR comments, evidence JSON, files or deployed Worker configuration. The following is an example for an **already completed** day; replace the date, deployment version and private absolute path. The export path MUST be outside the Git checkout:

```sh
# Set your account ID in your own local shell, not in repository files.
export CLOUDFLARE_ACCOUNT_ID="your-32-character-account-id"
# Type a token in your private terminal (no echo); never put it in a command history.
printf 'Cloudflare observability token (private input): '
read -r -s CLOUDFLARE_OBSERVABILITY_TOKEN
printf '\n'
export CLOUDFLARE_OBSERVABILITY_TOKEN
umask 077

node scripts/collect_cloudflare_observer_telemetry.mjs --execute \
  2026-11-09 ACTUAL_DEPLOYMENT_VERSION_ID \
  /absolute/private-folder/observer-2026-11-09.json

unset CLOUDFLARE_OBSERVABILITY_TOKEN
node scripts/audit_cloudflare_observer_telemetry.mjs \
  /absolute/private-folder/observer-2026-11-09.json
```

The CLI refuses absent `--execute`, incomplete UTC days, missing/invalid credentials or deployment identity, non-absolute paths, and any output inside the checkout. It writes a new **0600** JSON file with `wx` (no overwrite), retaining the *original responses*, **without** headers/token, and prints a small SHA256 receipt and local audit status; the parent directory must also be private. Even on an API response that is syntactically valid but incomplete, the evidence remains available for investigation while the command exits nonzero. If either HTTP request fails, it fails without retrying or emitting the response body. Do not upload the potentially sensitive raw logs to a public issue/PR.

The script reports `independently_authenticated_origin:false` and `cloudflare_deployment_independently_proven:false` because merely running the owner-controlled client does not provide an independent cryptographic attestation, nor a live platform CPU/cron proof on its own. **Local audit PASS and a saved 384-event envelope are not evidence of a recovered GitHub workflow or an on-time first-add.** The existing recovery release interlock stays hard-locked, and main/Render/native schedules remain untouched.


## 2026-11-09: operator-ready request generator and independent ABR gate (Draft-only)

Run from the repository root, without any Cloudflare or GitHub credentials:

```sh
node scripts/print_cloudflare_observer_telemetry_queries.mjs 2026-11-10
```

The command prints exactly two deterministic, secret-free **request bodies** for the same complete UTC day: a 2,000-limit event query and a separate unsampled COUNT calculation query. Both are scoped to the dedicated Observer service and the `cloudflare-workers` dataset. The generator **does not authenticate, send HTTP, create a Cron, deploy a Worker or assert that the query ran**. Supply the JSON request bodies through an **owner-controlled authenticated Cloudflare API client** only after actual deployment and account approval. Keep Cloudflare API credentials outside GitHub, ChatGPT and exported evidence. The published telemetry query endpoint currently lists the **Workers Observability Write** API-token permission; use the narrowest account-scoped token available and avoid global API keys. A Cloudflare API token for reading logs is separate from any GitHub dispatch PAT and must not be added to the Worker.

The V2 auditor also now examines **query-time Adaptive Bit Rate sampling** (`result.statistics.abr_level` and `result.run.statistics.abr_level`), *separately* from the stored-event ingestion `sampleInterval`. The Cloudflare API documentation states an omitted ABR level means 1. Any present non-1 value causes `api_adaptive_query_sampling_not_exact`, even if 384 rows and a synthetic `sampleInterval:1` aggregate appear. Dry/compare queries are rejected, and the **server-returned effective** COUNT calculation must be COUNT—not a different calculation hidden behind an accepted request.

A positive V2 audit still means **only the operator-supplied JSON is internally consistent**. It does not authenticate API responses, prove real Cloudflare deployment/CPU <=10ms or allow GitHub rescue. Actual 192/192 invocations and raw logs are still missing. The previous V1 samples remain for historical research only, not acceptance.

Official reference: https://developers.cloudflare.com/api/resources/workers/subresources/observability/subresources/telemetry/methods/query/


## 2026-11-09: Cloudflare Telemetry query V2 uses the documented API contract

**Correction to the historical V1 synthetic examples below:** The real Cloudflare POST /accounts/{account_id}/workers/observability/telemetry/query body uses top-level queryId, timeframe and limit, but **nested parameters.view, parameters.datasets and parameters.filters (an array)**. It returns result.run.status, result.run.timeframe and result.run.query.parameters, plus result.events or result.calculations. The old mock-only V1 wrapper incorrectly placed view and filters at the root and collapsed the raw response. V1 is superseded; do not manufacture missing fields from an old JSON example.

Cloudflare publishes two different limits: the request's top-level limit allows up to **2000 events**, enough for the expected 384 records in one response; parameters.limit is a separate option limited to **100**. The suggestion that a 384-event retrieval necessarily needs four pages was incorrect and is superseded.

The direct API path now accepts only **BOAT_EDGE_CLOUDFLARE_TELEMETRY_API_SINGLE_PAGE_V2**. Offline CLI: node scripts/audit_cloudflare_observer_telemetry.mjs <actual-api-evidence.json>. This file retains the exact request and API JSON response under events_query.request / events_query.response and sampling_query.request / sampling_query.response. The synthetic fixture in tests/cloudflare_capture_wakeup.test.mjs (syntheticApiTelemetryDay) illustrates required structure; it is NOT Cloudflare evidence.

Strict V2 acceptance:
- Both original POST request bodies have distinct nonempty queryId, the exact full UTC-day timeframe, datasets ["cloudflare-workers"], and exactly one array service filter: [{"kind":"filter","key":"$metadata.service","value":"boat-edge-clean-independent-observer","type":"string","operation":"eq"}].
- Event query: top-level limit 2000, no cursor, nested parameters.view "events". Sampling query: nested parameters.view "calculations" with exactly one count calculation and the identical Worker/dataset filter.
- Responses: success true, errors [], result.run.status "COMPLETED", matching run.timeframe and server-echoed run.query.parameters service filter and view; same nonempty accountId on two different run IDs.
- Exactly 384 stored events (192 invocations and 192 custom log records), each dataset "cloudflare-workers", and one matched aggregate with count 384 and sampleInterval 1. Downstream raw correlation also requires CPU, Worker version, request IDs, timestamps and no duplicates.

**Proof limit:** This is an offline consistency check of operator-supplied JSON, not independent Cloudflare origin authentication, successful deployment, actual Cron/CPU or any rescue. No token or Authorization header should ever be included in evidence sent to this audit or a PR. A V2 synthetic PASS never approves GitHub dispatch. The historical V1 mock examples remain research artifacts but are **not a supported production evidence format**.

Cloudflare API documentation: https://developers.cloudflare.com/api/resources/workers/subresources/observability/subresources/telemetry/methods/query/


## 2026-11-09: observer logs and query-scope acceptance update (Draft only)

The dedicated zero-credential `cloudflare/wrangler.observer.toml` uses the documented Workers Logs layout: `[observability]` with `enabled = true`, and `[observability.logs]` with `invocation_logs = true` and `head_sampling_rate = 1`. The PR-only source preflight now rejects missing invocation logs, a non-one sampling rate, unexpected tables/keys and altered Cron identity. Wrangler `deploy --dry-run` and synthetic/local Workerd checks **do not prove** live logging has started.

For `BOAT_EDGE_CLOUDFLARE_TELEMETRY_API_SINGLE_PAGE_V1` input, preserve the **actual request filters** for BOTH the events query and the independent calculations query. The API wrapper now requires the **same exact scoped leaf** for each:

```json
{"kind":"filter","key":"$metadata.service","value":"boat-edge-clean-independent-observer","type":"string","operation":"eq"}
```

Previously, two identical but unrestricted/foreign-worker filter objects could satisfy the equality check. A filtered 384-record synthetic envelope cannot prove that Cloudflare's sampling calculation applied to the correct Worker unless both queries match this exact scope. Unexpected filter groups or extra predicates fail closed pending independent review. The source's `api_query_structure_pass` asserts only the operator-provided request/response structure, **never authenticates the Cloudflare API response** or confirms actual Free-plan CPU.

Official documentation: https://developers.cloudflare.com/workers/observability/query-builder/ and https://developers.cloudflare.com/api/resources/workers/subresources/observability/subresources/telemetry/methods/query/ .


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

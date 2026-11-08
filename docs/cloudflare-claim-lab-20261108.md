# Research-only SQLite at-most-one dispatch claim — Cloudflare Free

**2026-11-08 JST. NOT deployed, NOT wired to capture, NO external Github calls.** This is a completely separate SQLite-backed Durable Object research lab under Draft PR #1697, **not** a production patch to Render, main, GitHub capture, observer or active recovery Worker.

## Why the existing GET→POST is unsafe

The currently dormant recovery Worker performs four GitHub history GETs and may issue two dispatch POSTs. Real local Workerd test reproduces **two simultaneous invocations** making **four POSTs** from independently empty histories. Delayed native GitHub `schedule` can also arrive after the Cloudflare check. GitHub workflow-level `concurrency` protects *running* jobs but does not atomically coordinate *external dispatch requests*. CLEAN currently has default `queue:single`, potentially replacing a pending original scheduled capture; four-mode has `queue:max`, allowing multiple pending requests. Neither is an external exactly-once protocol. [GitHub concurrency reference](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/control-workflow-concurrency).

## Research result and exact scope

- Code: `cloudflare/claim_lab_only.mjs` exports SQLite-backed `CaptureClaimResearch` plus a **403-only** HTTP handler, with **NO Cron, GitHub client, PAT, public routes, scheduled() or external fetch**.
- Explicit separate configuration `cloudflare/wrangler.claim-lab.toml` has `workers_dev=false`, `[triggers] crons=[]`, `[[durable_objects.bindings]]` and `new_sqlite_classes` for Workers Free. The *two real production-capable/observer configs* are unchanged and have no binding to this lab.
- Local Workerd tests: `cloudflare/test/claim_lab.spec.mjs`, run separately via `npm run test:claim-lab` with `vitest.claim-lab.config.mjs` and a **read-only** PR token. Tests exercise **32 concurrent reservations to one deterministic object**, and require exactly one claim success, plus restart-like fresh stub reads, invalid slot rejection, independent time/workflow keys, loss of response, irreversible claim retention and one-time reported-run-ID recording. Tests use *Cloudflare's real local Workerd SQLite implementation*, not a JavaScript Map.
- SQL `PRIMARY KEY(kind,slot_ms)` + `INSERT ... ON CONFLICT DO NOTHING RETURNING` performs selection in **one atomic statement**. All calls to a *single deterministic Durable Object ID* share a single database; **different object names do not share any lock**. There is no expiry, reset, force-retry or blind release. A timeout/204/unknown after winning a claim blocks further claims indefinitely until an independent manual reconciliation protocol exists. The fail-closed behavior may reduce coverage; this is deliberate and needs evidence.
- An optional `reportRunId()` records only one GitHub-provided ID; it never claims GitHub completed, prediction was saved, or T-12 source was formally certified.

Cloudflare sources: [Durable Objects Free plan](https://developers.cloudflare.com/durable-objects/), [SQLite transactional storage](https://developers.cloudflare.com/durable-objects/api/sqlite-storage-api/), [Workerd tests](https://developers.cloudflare.com/durable-objects/examples/testing-with-durable-objects/) and [limits](https://developers.cloudflare.com/durable-objects/platform/limits/).

## What this does NOT solve

The above proves **at-most-one claim winner inside one Cloudflare Durable Object** under *local Workerd simulated concurrency*. It does **NOT** prove exactly-once external Github workflow dispatch or first-add publication. Failure windows remain:

1. Cloudflare may reserve, then never send a POST: permanently blocked slot, a missed rescue.
2. Cloudflare may POST, then lose the GitHub response: reservation cannot be safely released or retried; status is ambiguous.
3. Native Github `schedule` and independent Render/other fallback **do not consult the DO**, so their run can still race with a claimed Cloudflare slot.
4. Even a 200 `return_run_details:true` response only reports a run ID; it is not completion, new Git first-add, or independent official T−12 proof.
5. Multiple Cloudflare instances using **different object IDs**, or deploying from separate accounts/namespaces, bypass the shared claim entirely.
6. Free quotas, actual CPU 10ms for scheduled Worker, DO CPU/storage/billing, platform availability and production invocation behavior are still **unmeasured**.

## Production NO-GO / proposal for owner review

- **DO NOT DEPLOY THIS LAB** as production recovery. It has no access endpoint to actuate rescue and must not be retrofitted into production without a separate reviewed design.
- Before any active Cloudflare recovery, require a cross-provider coordination contract that includes delayed native GitHub schedules and any Render rescue path, **or** a documented independent end-to-end publication idempotency proof with acceptable loss/cancellation behavior. This requires review with collection teams; **never modify their live workflows from this research PR**.
- Candidate architecture A: each authorized publisher and wakeup obtains one shared per-workflow/per-slot reservation with a durable state machine and independently auditable result mapping. This requires changes to original GitHub workflows, which are *outside the scope* of PR #1697.
- Candidate architecture B: explicitly tolerate extra runs while proving immutable per-race first-add / safe Git conflict handling, and independently test that rescue cannot cancel or displace required schedules. This is presently **unproven** for CLEAN `queue:single`.
- Phase 0 stays the no-token, no-GitHub observer only. Require actual Cloudflare account deployment, 192-tick live Cron/CPU log audit, PAT least privilege only for a future separately approved live recovery Worker, and a verified real run ID→result→first-add→T−12 chain.
- Keep existing production Render/GitHub schedules/main untouched; leave PR #1697 **Draft/unmerged**, no auto-merge or deployment.

**Evidence semantics:** Green CI for the claim lab is limited to research evidence about local DO atomic reservations; it is **not** a green production backup certificate, a live Cloudflare CPU reading or an official recovery count.


## Claimant ownership hardening (2026-11-08, research only)

An additional security/integrity gap was found **inside the lab**: the original `reportRunId(kind, slotMs, runId)` permitted **any caller with access to that Durable Object binding** to set the reported GitHub run ID for someone else's existing claim. This did not create a public HTTP interface, but in a future multi-caller integration could corrupt the provenance ledger or falsely attribute a returned run ID.

The **lab only** now issues `claim_token: crypto.randomUUID()` to the **one winning** `reserve()` caller and stores that UUID **in the same atomic SQLite INSERT** as the unique `(kind, slot_ms)` row. A losing caller receives no token. Updating a run ID requires `reportRunId(kind, slotMs, claimToken, runId)`, with a strict UUIDv4 format guard and atomic `WHERE claim_token=? AND reported_run_id IS NULL` condition. The token is not present in `inspect()`, and attempted cross-slot, cross-workflow, cross-object or unauthenticated updates are refused. No token is logged or committed in CI output. If the winning process loses its token or a response is ambiguous, the run ID remains unreported and the claim remains **irreversible**; it is not treated as safe to retry.

New actual-local-Workerd tests verify that **32 concurrent reserve calls still have one winner**, losers never see claim tokens, a different caller cannot assign a run ID, and tokens cannot mutate another workflow-slot or differently named Durable Object. These tests strengthen attribution **only for Cloudflare callers using one shared object**. The single Durable Object **is not wired to the recovery Worker** and no native GitHub `schedule` or Render path consults it. The tests do **not** establish an end-to-end, cross-provider exactly-once protocol.

**Operational caution:** The UUID is an internal bearer capability—not a GitHub PAT—and should never be included in public logs, audit JSON, web responses, PR comments or UI. The research schema now has an extra `claim_token TEXT NOT NULL` column. Because the lab has **never been deployed**, no live migration is needed. If an existing Cloudflare namespace or production schema is later introduced, do not change its SQLite schema without explicit versioned migration review. All live recovery NO-GO gates remain in force.

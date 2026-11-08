# Cloudflare Workers Free independent backup — operational acceptance audit (2026-11-08 JST)

**Status: NO-GO for production recovery; Draft PR #1697 only.** Do not merge to `main`, enable auto-merge, deploy from CI, disable native GitHub schedules, or change the existing Render service/fallback. This document is a test/acceptance record, **not** a deployment instruction or proof of Cloudflare account access.

## Evidence independently verified before this document

- PR #1697 is Draft and unmerged. At original audit head `20d8ae44dffa7ef8787fc14e2b4806d67164bde6`, PR CI [#42465217073](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42465217073) completed successfully. `pr-policy-tests` passed 96 existing Python tests and 42/42 offline Node tests; `cloudflare-workerd-integration` passed 7/7 local Workerd Vitest tests. Operational `watchdog` was skipped for the PR. GitHub read-only test job logs show `Contents: read`. Both Wrangler 4.158.0 dry-runs passed. Observer compiled-bundle scanner: `OBSERVER_BUNDLE_NO_GITHUB_NETWORK_CODE_PASS`. This is **offline/CI evidence only**.
- Main source capture workflows remain `.github/workflows/clean-prospective.yml` and `.github/workflows/four-mode-prospective-capture.yml`. Both have workflow-level concurrency configuration, but this **does not prove exactly-once publication** across a delayed original schedule, another external provider, or concurrent Cloudflare invocations.
- Cloudflare account/secret binding, live scheduled events, real CPU, GitHub 204 response, independently correlated run ID, and a newly created immutable forecast file **have no observed receipts here**. Do not convert absent observations into positive results.

## Free-plan capacity calculation (configured design, NOT measured usage)

| Limit / property | Free ceiling per Cloudflare official docs | Current design | Gate |
| --- | --- | --- | --- |
| Cron CPU | 10 ms per scheduled invocation | not measured in Cloudflare | **OPEN** |
| External subrequests | 50 per invocation | max 4 history GET + 2 workflow POST = 6 in a dual-eligible tick | Configuration / local tests only |
| Daily invocations | 100,000 requests/day account allowance | UTC `*/5 22-23,0-13 * * *` = 16 hours × 12 = 192 Cron ticks/Worker/day | Check account's other Workers |
| Cron Triggers | 5/account | observer has 1; recovery Worker has 1; use **only one scheduled pilot** at a time | Check account's existing triggers |
| Workers Logs Free | 200,000 log events/day, 3-day retention (as of 2026-11-08) | observer samples all invocations; save an externally timestamped audit summary within retention | **OPEN** |

The 119 original daily capture slots are **63 CLEAN + 56 four-mode**, not 119 separate Cloudflare Cron triggers. During eligible ticks, the code asks GitHub for at most 30 `schedule` + 30 `workflow_dispatch` records per workflow, and stops rather than speculating on truncated history. HTTP waiting time is excluded from CPU consumption, but JSON parsing/policy processing is not. **No fixed number of low-cost API calls proves CPU <=10 ms.**

Official sources: [Workers limits](https://developers.cloudflare.com/workers/platform/limits/); [Cron Triggers](https://developers.cloudflare.com/workers/configuration/cron-triggers/); [Workers Logs](https://developers.cloudflare.com/workers/observability/logs/workers-logs/).

## Acceptance stages — every missing receipt stays OPEN

1. **Phase 0: owner-controlled observer deployment only (OPEN).** With account authentication but no GitHub token, explicitly deploy only `cloudflare/wrangler.observer.toml` after review. Confirm the actual Worker name, exact UTC cron expression, logs, and number of Cron Triggers in the owner's Cloudflare dashboard. Record deployment/version ID and timestamp. Cron changes may take **up to 15 minutes to propagate**; exclude that propagation interval from lateness conclusions. Never count a local Explorer test as a live Cron invocation.
2. **Phase 0: 24-hour Cron/CPU evidence (OPEN).** For a full UTC day after propagation, cross-check scheduled timestamps against actual Cloudflare invocation logs. Record expected 192 configured ticks, actual observed ticks, rejected/stale ticks, exception outcomes, and CPU time for **every sampled invocation** (at minimum maximum, p50, p95, and any `exceededCpu` occurrence). Reject if any verified over-limit termination occurs, if necessary recovery windows are not met, or if the sample is incomplete. Cloudflare's 10ms CPU ceiling is **per invocation**, not daily average.
3. **Phase 1: token and no-dispatch preflight (OPEN).** Use a **fine-grained GitHub PAT**, restricted to `ikst2512-eng/boat-edge-clean` only, with repository **Actions read/write** (GitHub workflow-run GET requires read; dispatch POST requires write). Keep it solely in the *production-capable* Worker `GITHUB_DISPATCH_TOKEN` Secret, never in `[vars]`, logs, chat, artifacts, or this PR. Record only that permissions/expiration were reviewed, **not the PAT value**. Deploy recovery Worker with `CLOUDFLARE_DISPATCH_ENABLED="false"`. Confirm zero GET/POST.
4. **Phase 2: concurrency/idempotency review before opt-in (OPEN).** The code's GitHub GET→POST is **not atomic**. Read-only history checks and workflow-level concurrency do **not guarantee** no duplicate dispatch if an original schedule starts after the check, two Cloudflare ticks overlap, or a Render recovery also runs. Review target workflow publication/idempotency and require an independent cross-provider exactly-once safeguard or documented fail-safe acceptance with evidence. **Never enable paid Render Cron simultaneously** before cross-provider locking is solved. Keep native GitHub schedules intact.
5. **Phase 2: tightly controlled natural-failure recovery (OPEN).** Only after owner approves the risk above, enable the exact string `"true"` through a reviewed explicit deployment. Do **not** create an artificial production outage. On a naturally missing/failed eligible original run, record (a) scheduled original slot, (b) Cloudflare actual timestamp + CPU time + exception status, (c) the four GET histories and their outcome, (d) accepted GitHub **HTTP 204** with per-workflow receipt, (e) separately correlated GitHub `workflow_dispatch` **run ID and result**, (f) immutable forecast **first-add commit/file SHA and timing**. A 204 by itself is neither a workflow success nor a saved/T−12-qualified forecast. Any 401/403/404/429/5xx, missing or malformed history, timeout, token/clock error, expired window, or unexplained duplicate is **failure or inconclusive, never success**.
6. **Final independent sign-off (OPEN).** Compare the new forecast's source/provenance and GitHub first-add evidence with the existing T−12 independent auditor; do not re-label research data as formally certified. Only then consider the backup operational. `main` merge still requires independent manual review and owner approval; this acceptance document never authorizes it.

## Rollback and handover

Disable the Cloudflare production Cron (set `crons = []` and deploy the approved config, or remove the trigger in the appropriate management surface), turn `CLOUDFLARE_DISPATCH_ENABLED` off, and revoke the fine-grained PAT if exposure or incorrect dispatch is suspected. **Commenting out the `crons` key does not remove the trigger.** Verify propagation before declaring rollback effective. Do not alter main GitHub schedules or the existing Render fallback.

GitHub official permissions: [workflow runs require Actions read](https://docs.github.com/en/rest/actions/workflow-runs) and [workflow dispatch requires Actions write](https://docs.github.com/en/rest/actions/workflows). Cloudflare official [Cron propagation and UTC behavior](https://developers.cloudflare.com/workers/configuration/cron-triggers/).

**Non-negotiable:** code success != deployment; real Cron != recovery; HTTP 204 != GitHub run ID; run ID != first-add; first-add != independent formal T−12 certification.

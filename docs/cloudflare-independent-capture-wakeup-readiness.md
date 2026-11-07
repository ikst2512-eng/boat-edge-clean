# Cloudflare Free independent capture wakeup — Draft / not deployed

**Scope:** optional external GitHub Actions wakeup for BOAT EDGE CLEAN. No forecasting, storage, historical mutation, model, odds, UI or existing Render service changes. This is **code-only readiness**, not operational proof.

## Why this path

The Render Cron alternative in `scripts/render_capture_wakeup.py` is preserved unchanged but provisioning returned HTTP 402 (payment information required). Cloudflare Workers Free offers up to five Cron Triggers per account, 100,000 requests per day, 50 subrequests per invocation and **10 ms CPU time per Cron invocation**. Awaited network requests do not count as CPU time, but JSON parsing and policy checks do. GitHub history requests are limited to **30 records per page** (instead of 100) for a lower CPU budget; ambiguous full pages within the last two hours remain **fail-closed**. This reduces risk but does not prove the 10ms CPU limit. We must separately measure actual Worker CPU time, errors and rate limits before accepting Free-tier reliability. Docs: https://developers.cloudflare.com/workers/platform/limits/ and https://developers.cloudflare.com/workers/configuration/cron-triggers/.

## Source and fail-closed safety

- `cloudflare/independent_capture_wakeup.mjs`: one scheduled-only Worker. No HTTP `fetch()` handler, no secret in source or logs. Runs only on UTC cron `*/5 22-23,0-13 * * *`; time-converts to Asia/Tokyo without DST; rejects cron wakeups delayed by more than 90 seconds. Also rejects a GitHub history run whose timestamp is in the future, and **rechecks live wall-clock eligibility immediately before every POST** so a slow API response cannot dispatch after the CLEAN 22:33 JST hard cutoff.
- Only CLEAN `clean-prospective.yml` and four-mode `four-mode-prospective-capture.yml` on the `main` branch. Mirrors the existing Render recovery windows. Every 63 CLEAN and 56 four-mode original daily slots has exactly one eligible five-minute tick, including special 22:28 JST CLEAN → 22:30 wakeup. No GitHub API calls outside eligible slots.
- Separately read `event=schedule` and `event=workflow_dispatch` histories per workflow. Reject unreadable/malformed/ambiguous history. Block active jobs, direct success or unknown conclusions and any same-slot manual dispatch (including a failed one). Require all eligible history checks to succeed before posting to either workflow. POST `workflow_dispatch` only when original scheduled run is absent or explicitly failed; require HTTP 204.
- `workflow_dispatch` acceptance is **not** evidence of forecast saved, original Git first-add, source received before T−12, accurate predictions, or an on-time GitHub schedule. This is a wakeup, not a separate GitHub failure domain or a second data writer.
- Keep the existing GitHub schedules/watchdogs and Render fallback script untouched. Do **not** activate both external recovery schedulers simultaneously unless cross-provider idempotency is independently proven: their separate GET→POST checks are not an atomic lock.

## Tests and continuous integration

Offline: `node --test tests/cloudflare_capture_wakeup.test.mjs` (Node 22). Tests cover all source GitHub crons, 119 daily slots, UTC/JST cutoff, late cron, missing token, two workflows, success/failure/queued/history ambiguity, cross-workflow fetch failure and non-204 POST. A PR CI step in the existing `Four-mode capture schedule watchdog` workflow runs this command; no new GitHub schedule or workflow is created. Additional deterministic cases cover future-dated GitHub rows, smaller history pages, delayed network I/O past 22:33 and partial late-dispatch suppression. **24/24 local Node 22 tests PASS** on the updated PR branch (GitHub PR exact-head CI checked separately).

Existing Render safety suite remains in CI and was not edited. Local Node tests do **not** demonstrate Cloudflare Free CPU 10 ms, production dispatch, daily reliability, actual GitHub first-add, or billing/account readiness.

## Operator steps — **manual, not performed in this PR**

1. Create or connect a Cloudflare account on Workers Free, and check remaining Cron capacity. Review compatibility date, pricing and current Free limits. Do not connect a paid plan implicitly.
2. Create a dedicated fine-grained GitHub PAT restricted to repository `ikst2512-eng/boat-edge-clean` and `Actions: read/write`. Record expiry and rotate as needed. Do not paste it in ChatGPT, commits, PRs, logs or `wrangler.toml`.
3. Use Cloudflare Workers & Pages or Wrangler with config `cloudflare/wrangler.toml`. Configure `GITHUB_DISPATCH_TOKEN` as a **Secret**, not `vars`, before activation. `[secrets] required = ["GITHUB_DISPATCH_TOKEN"]` in `cloudflare/wrangler.toml` makes Wrangler reject deploys without that secret. For initial activation, securely create the secret via the Cloudflare dashboard on a non-cron Worker and then deploy, **or** use a private local secret file with `npx wrangler deploy --secrets-file /secure/path/secrets.json` from `cloudflare/`. Never commit that file. `cloudflare/.gitignore` excludes `.env*`, `.dev.vars*` and Wrangler local state. `npx wrangler secret put GITHUB_DISPATCH_TOKEN` may immediately deploy a new version, so it is **not** a safe inert setup step. Official: https://developers.cloudflare.com/workers/configuration/secrets/.
4. Observe actual **Cron Trigger logs**, CPU-time, successful GET decisions, GitHub dispatch run IDs, and confirmed first-add Git SHA and source receipt before the cutoff for a *new JST day*. Check 429/rate limit or CPU errors; a pass with zero eligible predictions is not a publication success.
5. To roll back, disable/remove the Cloudflare Cron Trigger in its Worker configuration and revoke the GitHub PAT. Existing GitHub scheduled workflows and the unused Render code are unaffected.

**Acceptance:** local unit tests PASS → PR CI PASS → human review → optional main merge under owner control → Cloudflare account/secret/provisioning → live low-CPU triggered checks → independent GitHub first-add/T−12 provenance. This PR is **draft only** and must never be auto-merged.

**2026-11-07 hardening update:** future timestamp fail-closed, deadline revalidation before every dispatch, per_page=30, mandatory secret and local credential exclusion added. Updated 24 offline tests pass. **2026-11-07 research note:** code and offline tests prepared; Cloudflare account is not connected to ChatGPT, no deployment/secret/real trigger/forecast has been made or verified. Render's existing Free web service is unchanged. Formal certification 0.

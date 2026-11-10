# Cloudflare Free independent capture wakeup — Draft / not deployed

## 2026-11-09 CURRENT operator gate — Observer only, recovery HARD LOCKED

This is the **current guidance**, superseding the historical Phase 2 activation wording below. The actual deployment-facing source in `cloudflare/independent_capture_wakeup.mjs` has `CROSS_PROVIDER_DISPATCH_RELEASE_LOCKED = true`. Merely changing `CLOUDFLARE_DISPATCH_ENABLED` to `"true"` or providing a valid GitHub PAT **cannot** unlock recovery: the Worker rejects the request before any GitHub GET or POST. Do not remove the lock in this PR, and do not activate a second recovery scheduler while native GitHub/Render writers lack one independently reviewed cross-provider authority.

The repo now has a **read-only, no-credentials observer preflight**. From the repository root run:

```sh
node --test tests/cloudflare_observer_preflight.test.mjs
node scripts/preflight_cloudflare_observer.mjs
```

The script verifies the dedicated observer name, no public workers.dev route, exact single UTC Cron `*/5 22-23,0-13 * * *`, 100% Workers Logs sampling, no secrets/bindings or GitHub import/fetch path, and continued recovery lock + default OFF. Every active TOML statement must use a known section/key, with no duplicates or unsupported syntax; the tested `compatibility_date=2026-06-24` is pinned. This strictly limited check complements (and does not replace) the compiled Worker code scan or runtime tests. It emits JSON containing `observer_preflight_pass`. A zero exit code is **static source/config eligibility only**, not Cloudflare login, live Cron, real CPU, recovery dispatch or authorization. PR-only CI also runs this gate alongside existing Node/Python/Workerd and the compiled observer no-network-code check.

**Exact-head CI evidence:** [run #42616686554](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42616686554), commit `1456518d795e36acd788ae48c93a7082b2828561`: 102 existing Node tests + 14 preflight mutation tests + 96 existing Python tests + 16 Workerd recovery/Observer tests + 11 isolated claim-lab Workerd all passed (**239/239 total**), plus three Wrangler dry-run builds and observer compiled-code gate. The new Workerd test shows 16 concurrent calls to the **deployment-facing locked handler** emit 0 GitHub GET/POST; the **dormant unlocked policy still reproduces duplicate POST** and MUST NOT be activated. The write-capable watchdog was skipped on PR. **No Cloudflare account, secret, Worker deployment, actual Cron tick, Free CPU sample, real workflow dispatch or recovery was involved.**

**First external step requires owner-controlled approval:** deploy only `cloudflare/wrangler.observer.toml` after a private Cloudflare account/quota review, then retain actual versioned Workers Logs and audit one full UTC day after propagation: 192 unique expected ticks, actual CPU <=10ms for every invocation, no sampled/duplicated/missing logs. Follow `docs/cloudflare-observer-telemetry-export-guide.md` and `docs/cloudflare-raw-logs-correlation-20261108.md`. The observer never sends GitHub requests; completed Phase 0 can **never** be called a recovered race. Real independent Cloudflare rescue proof: **0**. Keep PR Draft/unmerged, no main auto-merge, no Render or native workflow change.


## 2026-11-08: observer Worker contains **no GitHub dispatch code** (build verified)

**Strengthened Phase 0:** The optional pilot `cloudflare/wrangler.observer.toml` now points to a **separate default-only** Worker entrypoint `cloudflare/independent_capture_observer.mjs`, which imports **only** the GitHub-free `cloudflare/independent_capture_slots.mjs` module. Both the observer and production recovery import this *same* pure slot/clock module (63 CLEAN and 56 four-mode daily slots); there is no duplicated schedule logic to drift. The GitHub-facing recovery API, history validation, token handling and `workflow_dispatch` stay exclusively in `cloudflare/independent_capture_policy.mjs` and the production entrypoint. The observer has no HTTP handler, no `fetch()` calls, no PAT binding and no recovery-code import. Even injecting both a string `CLOUDFLARE_DISPATCH_ENABLED="true"` and a **fake** token into the observer's scheduled handler cannot make it contact GitHub.

**Verified compiled output, not just source comments:** GitHub CI builds the observer with `wrangler@4.158.0 deploy --dry-run --config cloudflare/wrangler.observer.toml` and scans the **actual emitted JavaScript bundle**. It fails if it contains `api.github.com`, `GITHUB_DISPATCH_TOKEN`, `/dispatches` or `Authorization`. This rules out accidental inclusion of recovery/network code in the observer's built artifact, independently of the environment gate.

**Exact-code PR CI:** [#42460963433](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42460963433) completed **success**; the existing Python policy succeeds, Node **42/42 PASS / 0 fail**, real local Workerd Vitest **7/7 PASS**, production bundle dry-run **11.16 KiB / gzip 3.57 KiB**, observer-only bundle **4.45 KiB / gzip 1.65 KiB**, compiled-bundle scanner `OBSERVER_BUNDLE_NO_GITHUB_NETWORK_CODE_PASS`, and existing local Cron fail-closed checks PASS. The work remains in **Draft PR #1697**, no Cloudflare account integration, no Worker deployment, no GitHub live dispatch, no CPU10ms measurement or first Git-add/T−12 recovery certification.

An earlier attempted bundle test correctly **failed** when the observer imported the GitHub-facing policy, revealing that the bundled output still contained an API URL even though all runtime dispatch tests were passing. The pure scheduling module refactor fixed this; the failed CI attempts remain in the PR history as negative evidence, and the compiled-code gate now prevents that regression.

**Pilot operator action (manual, not executed):** After owner account setup and review, deploy **only** `wrangler.observer.toml`. No GitHub PAT is required for this phase. Its CPU/Cron and logs must be measured in the Cloudflare account before any separately reviewed recovery deployment. The observer config is a separate Worker name and is never a production dispatch switch.


## 2026-11-08 15時台 JST: two-phase **opt-in** activation — default is zero-network observation

This Draft PR now ships **two distinct Wrangler configurations** for safe rollout. **Neither has been deployed; no account, PAT, GitHub dispatch, or billing was used.** The Phase 2 row below is updated to reflect the 2026-11-09 source-level interlock.

| Intended phase | Config | GitHub PAT needed to deploy? | GitHub GET/POST? |
| --- | --- | --- | --- |
| Phase 0: zero-credential monitoring | `cloudflare/wrangler.observer.toml` | **No** | **No; hard off by default** |
| Phase 1: production-capable Worker, still gated off | `cloudflare/wrangler.toml` | **Yes**, required Secret | **No; hard off by default** |
| Phase 2: recovery (currently BLOCKED) | Requires a separate code review to remove the source-level cross-provider hard lock after native/Render publication-idempotency and independent live evidence | Not yet provisioned | **NO** until separately approved release |

The Worker `scheduled()` handler checks the exact cron identity, then checks `CLOUDFLARE_DISPATCH_ENABLED === 'true'`. Every other value (unset, false, "TRUE", number, etc.) takes `observe()`, which checks the trigger clock and calculates the CLEAN/four-mode eligible slots **without reading GitHub, requiring a Secret, issuing a dispatch, or declaring a saved forecast**. The log key is `CLOUDFLARE_CAPTURE_OBSERVER_ONLY` and the result explicitly marks `github_history_checked=false`, `github_run_id_proven=false`, `new_forecast_saved_proven=false`, `formal=false`. A stale or foreign Cron still fails closed.

`wrangler.observer.toml` has a **separate Worker name** (`boat-edge-clean-independent-observer`) and no `[secrets]` declaration. Once a Cloudflare account is available, the **owner**, not this Draft PR, may deploy it explicitly from the repository root:

```sh
npx wrangler@4.158.0 deploy --config cloudflare/wrangler.observer.toml
```

This command would really **deploy** a Worker and register a Cron Trigger; it has **NOT been run** here. It needs Cloudflare account authentication but no GitHub token. Read the resulting local Cloudflare Cron logs and Worker CPU measurements during a new JST day. A future production rollout requires a separately reviewed cross-provider idempotency and publisher contract, live CPU/Cron proof, explicit owner authorization, and a separate code-level removal of `CROSS_PROVIDER_DISPATCH_RELEASE_LOCKED = true`. **Do not merely set the dispatch flag and deploy.** No PAT is required for the Observer phase. Disable the observer Cron when the production Cron begins; this avoids unnecessary Cron duplication and stays within Free-tier limits. Never activate a paid Render Cron and Cloudflare recovery simultaneously without an atomic cross-provider lock.

**Exact-head, deployment-free CI:** [#42456421210](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42456421210) completed **success**. Read-only PR policy test job: **39/39 Node tests PASS** (including zero-token observer entry, false/unset/invalid flag behavior, config separation, and true-only dispatch), production and observer Wrangler 4.158.0 `deploy --dry-run` both PASS. Isolated real Workerd integration job: **6/6 PASS**, including observer without PAT or network, real controlled fake-GitHub 4 GET + 2 POST positive simulation, active-run blocking, and API failure stop. Existing Python tests and scheduled-handler Local Explorer safety gates PASS. Operational `Actions:write` watchdog skipped for PR. These are **mock/local CI**, not live CPU10ms or deployment evidence.

Official references: [Cloudflare secrets](https://developers.cloudflare.com/workers/configuration/secrets/) and [environment variables](https://developers.cloudflare.com/workers/configuration/environment-variables/). Never place a PAT in `[vars]`, chat, git, PR comments or logs. The production `[secrets] required` declaration intentionally prevents accidental deployment without a Secret; it **does not apply** to the separate observer config.


## 2026-11-08: Workerd **positive-path** GitHub mock integration PASS (no real GitHub calls)

The new isolated read-only PR job `cloudflare-workerd-integration` uses Cloudflare's official `@cloudflare/vitest-plugin` to run **four actual Workerd runtime tests** against the production `scheduled()` entrypoint. All outbound `fetch` calls are intercepted by a strict in-process fake GitHub API; the suite passes a clearly fake literal token and **never** uses GitHub repository secrets, Cloudflare authentication, real GitHub networking, or actual `workflow_dispatch`.

[Exact-code PR CI #42443452124](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42443452124): both jobs **completed/success**. Existing watchdog: Python tests PASS, Node **32/32 PASS**, Wrangler 4.158.0 `deploy --dry-run` PASS, local Workerd Local Explorer scheduled invalid/expired trigger tests PASS. Independent unprivileged Workerd integration job: Vitest **4/4 PASS**, test file `cloudflare/test/worker_runtime.test.mjs`, four tests completed in a local Workerd process.

Test outcomes:
1. Valid 07:10 JST recovery tick: **4 GitHub history GETs, then 2 HTTP 204 simulated workflow_dispatches** for CLEAN and four-mode; individual nonsecret audit receipts retained, every formal/first-add flag remains false.
2. Two already-successful source schedules: four history GETs and **zero POSTs**.
3. Third history GET returns HTTP 503: **zero POSTs** and no 204 receipt; fail closed across both workflows.
4. Foreign Cron expression: rejects **before any network access**.

The isolated PR integration job explicitly has `permissions: contents: read`, `actions/checkout@v4` with `persist-credentials:false`, and does not receive the production watchdog job's `Actions:write` token. The first dependency-resolution attempt failed in npm 10 on `edgesOut` (known npm peer-graph bug); the follow-up pins Vitest 4.1.10 and Node 24, and the exact-head CI is green. Dependencies are for tests only, not the deployed Worker; package versions are pinned but transitive npm resolution currently has no committed lockfile, so reproducibility can be improved before merging.

**Scope boundary:** Although the positive scheduled-to-GitHub flow is now independently proven in a real local Workerd process with a mocked API, *real* Cloudflare Cron scheduling, Free-tier CPU usage <= 10ms, actual GitHub 204/run ID, and forecast Git first-add/T−12 source integrity are still **unverified**. Deployment, owner Cloudflare credentials, and the real fine-grained GitHub PAT Secret have not been provided or used. Draft PR only, no automatic main merge, no production Render or GitHub capture changes.


## 2026-11-08: real Workerd scheduled() admission verification — no deployment

The final remaining **local Cron invocation test gap was caused by Wrangler 4.102.0 being too old**, not by the Worker's scheduled handler: Cloudflare [Local Explorer documentation](https://developers.cloudflare.com/workers/local-development/local-explorer/) requires **Wrangler >=4.139.0** for scripted local scheduled events. The PR CI now pins the verified available **Wrangler 4.158.0** for `deploy --dry-run` and the local Workerd / Local Explorer smoke. The actual Worker `compatibility_date` remains `2026-06-24` pending live verification, and the Worker entrypoint remains default-only. No account credentials or real GitHub PAT are provided to CI.

**Exact-head GitHub Actions [#42441409092](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42441409092)** completed **success** on code head `84c30b29835a06807b2feaf47036f8c67cc0029f`. Existing Python policy SUCCESS, **32/32 Node unit tests PASS**, Wrangler 4.158.0 `deploy --dry-run` SUCCESS (10.09 KiB / 3.38 KiB gzip). Real local Workerd, Local Explorer API readiness and **both actual invocations of exported `scheduled()`** through `POST /cdn-cgi/local/explorer/api/local/scheduled?worker=boat-edge-clean-independent-wakeup` passed:

- Foreign ad-hoc cron `* * * * *`: Local Explorer HTTP 200; the Worker emitted the guarded `unexpected_cron_trigger` error, **before any GitHub fetch or token check**. `LOCAL_WORKERD_FOREIGN_CRON_FAIL_CLOSED_PASS`.
- Correct configured cron `*/5 22-23,0-13 * * *` with deliberately expired `scheduled_time=1700000000000`: Local Explorer HTTP 200; the Worker emitted `late_or_future_cron_trigger`, **before token checking or GitHub network**. `LOCAL_WORKERD_ALLOWED_CRON_EXPIRED_CLOCK_FAIL_CLOSED_PASS`.

HTTP 200 here is the response from the **local Explorer test API**, not an accepted GitHub `workflow_dispatch`. These tests prove real local Worker admission and fail-closed behavior; they **do not** prove a live Cloudflare Cron event, authentic GitHub API access, 204 acceptance, a saved forecast, or Free-tier CPU <=10ms. The `GITHUB_DISPATCH_TOKEN` Secret remains unconfigured, and there is no Cloudflare Worker deployment.

Previous unsuccessful 4.102.0 Local Explorer attempts and local runtime boot errors remain in PR CI history as independent negative evidence, with their causes now documented. Continue to keep the PR **Draft**, no automatic main merge, no Render modifications and no cross-provider duplicate-Cron activation.


## 2026-11-08: actual local Workerd startup gate (no account, no deployment)

A new **PR-only, local** Wrangler runtime test found two genuine deployment blockers previously missed by the 31 passing Node tests and `deploy --dry-run`:

1. Local Wrangler 4.102.0 bundles a Workerd server whose newest supported compatibility date is `2026-06-24`. Original config `2026-11-01` could bundle but could **not start**. Pinned `cloudflare/wrangler.toml` to the actually supported `2026-06-24`.
2. Once the date was fixed, Workerd rejected data exports like `export const REPO` on the Worker service entrypoint. Moved named logic/constant exports into `cloudflare/independent_capture_policy.mjs`. The production entrypoint `cloudflare/independent_capture_wakeup.mjs` now exports **only a default object with `scheduled()`**. The Node suite asserts this restriction and now has **32 cases**.

Current code exact-head [GitHub Actions #42391568966](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42391568966) **completed/success**. Verified actual raw job output: existing Python policy PASS, **32 Node tests PASS / 0 fail**, Wrangler 4.102.0 `deploy --dry-run` PASS (`10.09 KiB`, gzip `3.38 KiB`), **real local Workerd startup PASS** (`WORKERD_SCHEDULED_ONLY_BOOT_NO_FETCH_HANDLER_PASS`). The local-only GET deliberately reaches a Worker with **no HTTP fetch handler**, which is correct for a Cron-only Worker; it does not contact GitHub.

Earlier CI tests that attempted local Cron invocation through `/cdn-cgi/local/scheduled` or Local Explorer did not reach `scheduled()` in this Wrangler runner; they only hit the no-fetch-handler error. The final CI **does not claim a live Cron dispatch**. Actual Cloudflare Cron trigger delivery, GitHub live run ID, Free-tier CPU <=10ms, source receipts and Git first-add/T−12 remain **unverified**. Preserve Draft PR, no merge or deployment without owner review and secret setup. Failed intermediate CI attempts are kept as negative evidence, not rewritten as passes.


**Scope:** optional external GitHub Actions wakeup for BOAT EDGE CLEAN. No forecasting, storage, historical mutation, model, odds, UI or existing Render service changes. This is **code-only readiness**, not operational proof.

## Why this path

The Render Cron alternative in `scripts/render_capture_wakeup.py` is preserved unchanged but provisioning returned HTTP 402 (payment information required). Cloudflare Workers Free offers up to five Cron Triggers per account, 100,000 requests per day, 50 subrequests per invocation and **10 ms CPU time per Cron invocation**. Awaited network requests do not count as CPU time, but JSON parsing and policy checks do. GitHub history requests are limited to **30 records per page** (instead of 100) for a lower CPU budget; ambiguous full pages within the last two hours remain **fail-closed**. This reduces risk but does not prove the 10ms CPU limit. We must separately measure actual Worker CPU time, errors and rate limits before accepting Free-tier reliability. Docs: https://developers.cloudflare.com/workers/platform/limits/ and https://developers.cloudflare.com/workers/configuration/cron-triggers/.

## Source and fail-closed safety

- `cloudflare/independent_capture_wakeup.mjs`: one scheduled-only Worker. No HTTP `fetch()` handler, no secret in source or logs. The real Cloudflare `scheduled(controller, env, ctx)` entrypoint also **refuses every trigger whose `controller.cron` string is not exactly `*/5 22-23,0-13 * * *`**. This is independent of the existing scheduled-time allowlist and fails before any GitHub API access. Runs only on UTC cron `*/5 22-23,0-13 * * *`; time-converts to Asia/Tokyo without DST; rejects cron wakeups delayed by more than 90 seconds. Also rejects a GitHub history run whose timestamp is in the future, and **rechecks live wall-clock eligibility immediately before every POST** so a slow API response cannot dispatch after the CLEAN 22:33 JST hard cutoff.
- Only CLEAN `clean-prospective.yml` and four-mode `four-mode-prospective-capture.yml` on the `main` branch. Mirrors the existing Render recovery windows. Every 63 CLEAN and 56 four-mode original daily slots has exactly one eligible five-minute tick, including special 22:28 JST CLEAN → 22:30 wakeup. No GitHub API calls outside eligible slots.
- Separately read `event=schedule` and `event=workflow_dispatch` histories per workflow. Reject unreadable/malformed/ambiguous history. Block active jobs, direct success or unknown conclusions and any same-slot manual dispatch (including a failed one). Require all eligible history checks to succeed before posting to either workflow. POST `workflow_dispatch` only when original scheduled run is absent or explicitly failed; require HTTP 204.
- Each HTTP 204 acknowledgement emits a minimal per-workflow `CLOUDFLARE_DISPATCH_RECEIPT` log record **before proceeding to the second workflow**. It identifies the workflow, original recovery slot and the time the POST was initiated; it contains no token or GitHub run ID. Thus a partial 204-then-error invocation is auditable without falsely claiming both launches succeeded. Four deterministic receipt tests were added.
- `workflow_dispatch` acceptance is **not** evidence of forecast saved, original Git first-add, source received before T−12, accurate predictions, or an on-time GitHub schedule. This is a wakeup, not a separate GitHub failure domain or a second data writer.
- Keep the existing GitHub schedules/watchdogs and Render fallback script untouched. Do **not** activate both external recovery schedulers simultaneously unless cross-provider idempotency is independently proven: their separate GET→POST checks are not an atomic lock.

## Tests and continuous integration

Offline: `node --test tests/cloudflare_capture_wakeup.test.mjs` (Node 22). Tests cover all source GitHub crons, 119 daily slots, UTC/JST cutoff, late cron, missing token, two workflows, success/failure/queued/history ambiguity, cross-workflow fetch failure and non-204 POST. A PR CI step in the existing `Four-mode capture schedule watchdog` workflow runs this command; no new GitHub schedule or workflow is created. Additional deterministic cases cover future-dated GitHub rows, smaller history pages, delayed network I/O past 22:33, partial late-dispatch suppression and individual 204 receipt retention. **28/28 Node 22 tests PASS** in exact-head GitHub PR CI [#42364767503](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42364767503) on 2026-11-07 JST.

**Scheduled-handler integration gate (2026-11-08 JST):** GitHub PR CI [#42390394745](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42390394745), job `128456552012`, finished **success**. Existing Python watchdog policy, **31/31 Node tests** (including three new direct calls to the exported `scheduled()` function covering foreign/missing cron identity with no network; successful mocked 4-GET/2-POST response and redacted per-workflow receipts; missing Secret causing fail-closed with a redacted log) and Wrangler 4.102.0 dry-run bundling all PASS. Actual log: `Total Upload: 10.13 KiB / gzip: 3.40 KiB`, `--dry-run: exiting now.` This is a local simulated scheduled handler invoked in GitHub CI; **no Cloudflare account, live trigger, Worker upload, production GitHub dispatch, CPU10ms or forecast publication is proven**. Cloudflare's official scheduled-handler API documents `controller.cron` as an exact expression string: https://developers.cloudflare.com/workers/runtime-apis/handlers/scheduled/.

**Additional verified Cloudflare compile gate (2026-11-08 JST):** The same existing watchdog workflow now runs a **PR-only** `npx --yes wrangler@4.102.0 deploy --dry-run --config cloudflare/wrangler.toml --outdir /tmp/boat-edge-wakeup-bundle`. GitHub Actions [#42389742715](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42389742715), job `128454618800`, reports `completed/success` for the existing Python policy, 28/28 Node tests and the real Wrangler dry-run bundle. Actual Wrangler log: `wrangler 4.102.0`, `Total Upload: 9.95 KiB / gzip: 3.33 KiB`, `--dry-run: exiting now.` It **compiled without uploading or deploying any Worker**, and no Cloudflare/GitHub PAT was provided. The external GitHub API was not called by the test Worker. This does not test live Cron scheduling, CPU 10ms quota or first-add publication.

Existing Render safety suite remains in CI and was not edited. Local Node tests do **not** demonstrate Cloudflare Free CPU 10 ms, production dispatch, daily reliability, actual GitHub first-add, or billing/account readiness.

## Operator steps — **manual, not performed in this PR**

**Follow the two-phase no-PAT observer rollout above first.** The PAT and required Secret steps below apply only to the production-capable configuration, never to `wrangler.observer.toml`. Do not use the production recovery mode until the observer's live Cron/CPU evidence has been checked and the owner has explicitly approved activation.

1. Create or connect a Cloudflare account on Workers Free, and check remaining Cron capacity. Review compatibility date, pricing and current Free limits. Do not connect a paid plan implicitly.
2. Create a dedicated fine-grained GitHub PAT restricted to repository `ikst2512-eng/boat-edge-clean` and `Actions: read/write`. Record expiry and rotate as needed. Do not paste it in ChatGPT, commits, PRs, logs or `wrangler.toml`.
3. Use Cloudflare Workers & Pages or Wrangler with config `cloudflare/wrangler.toml`. Configure `GITHUB_DISPATCH_TOKEN` as a **Secret**, not `vars`, before activation. `[secrets] required = ["GITHUB_DISPATCH_TOKEN"]` in `cloudflare/wrangler.toml` makes Wrangler reject deploys without that secret. For initial activation, securely create the secret via the Cloudflare dashboard on a non-cron Worker and then deploy, **or** use a private local secret file with `npx wrangler deploy --secrets-file /secure/path/secrets.json` from `cloudflare/`. Never commit that file. `cloudflare/.gitignore` excludes `.env*`, `.dev.vars*` and Wrangler local state. `npx wrangler secret put GITHUB_DISPATCH_TOKEN` may immediately deploy a new version, so it is **not** a safe inert setup step. Official: https://developers.cloudflare.com/workers/configuration/secrets/.
4. Observe actual **Cron Trigger logs**, CPU-time, successful GET decisions, GitHub dispatch run IDs, and confirmed first-add Git SHA and source receipt before the cutoff for a *new JST day*. Check 429/rate limit or CPU errors; a pass with zero eligible predictions is not a publication success.
5. To roll back, disable/remove the Cloudflare Cron Trigger in its Worker configuration and revoke the GitHub PAT. Existing GitHub scheduled workflows and the unused Render code are unaffected.

**Acceptance:** local unit tests PASS → PR CI PASS → human review → optional main merge under owner control → Cloudflare account/secret/provisioning → live low-CPU triggered checks → independent GitHub first-add/T−12 provenance. This PR is **draft only** and must never be auto-merged.

**2026-11-07 hardening update:** Accepted 204 decisions now generate individual minimal nonsecret receipts; exact-head GitHub CI 28/28 PASS.  future timestamp fail-closed, deadline revalidation before every dispatch, per_page=30, mandatory secret and local credential exclusion added. The newer 31-case direct scheduled-handler and deterministic policy suite passes GitHub PR CI. **2026-11-07 research note:** code and offline tests prepared; Cloudflare account is not connected to ChatGPT, no deployment/secret/real trigger/forecast has been made or verified. Render's existing Free web service is unchanged. Formal certification 0.

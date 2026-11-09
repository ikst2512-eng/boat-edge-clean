# BOAT EDGE CLEAN — Cross-provider recovery release handoff (2026-11-09 JST)

**STATUS: NO-GO. This is an offline, independently testable Draft #1697 research handoff, not production authorization.** No main merge, native capture workflow edit, Render change, Cloudflare deployment, PAT provisioning, Cron activation or real dispatch is made by this document or its tests.

## Exact observed code contracts

Read from this repository's current native GitHub Actions workflows:

| Publisher | Native schedule | Concurrency group | Current pending behavior | Why Cloudflare recovery remains unsafe |
|---|---|---|---|---|
| CLEAN | `.github/workflows/clean-prospective.yml` | `clean-prospective-capture` | `queue: single` (default), `cancel-in-progress: false` | One later `workflow_dispatch` can replace/cancel a pending native `schedule`, even if the prior slot is still running |
| 4-mode | `.github/workflows/four-mode-prospective-capture.yml` | `four-mode-publication` | `queue: max`, `cancel-in-progress: false` | Native and rescue executions can both queue for the same slot; queue length 100 can reject new ones |

Official [GitHub concurrency reference](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/control-workflow-concurrency): `single` replaces an existing pending job; `max` admits up to 100 pending jobs, then cancels additional jobs. Concurrency serializes **workflow execution**, not **external dispatch generation** or **immutable first-add publication**.

## New executable counterexample: policy's complete GET snapshot is not a lock

The offline Node integration tests run the **real** `cloudflare/independent_capture_policy.mjs::execute()` with intercepted (never real) GitHub API calls:

1. At a valid 07:10 JST rescue tick, GitHub returns exactly four complete, internally consistent empty schedule/manual history pages for CLEAN and 4-mode (`total_count === 0`).
2. **After the fourth GET, before the first POST**, an original native CLEAN schedule can become pending. The rescue policy has no atomic GitHub reservation and cannot observe an event that happened after its history snapshot.
3. If the native CLEAN schedule became pending first and a Cloudflare POST followed, `queue:single` may **cancel the original**. In the reverse arrival order, the later native schedule may **cancel the rescue**. Both are possible under the official queue rule; the tests simulate that documented behavior, not a real GitHub incident.
4. With 4-mode's `queue:max`, both native and Cloudflare work can remain pending. **Two runs != one published forecast.** If the queue already has 100 pending runs, the newer request is canceled instead.
5. Simulating `queue:max` for CLEAN as a *counterfactual* eliminates the specific single-pending replacement at low backlog, but retains both duplicate pending executions and the 100-pending capacity limit. It **does not** independently prove a safe recovery or an on-time T−12 publication.

Tests cannot supply a real-native-event timestamp, on-time CPU reading, or immutable Git commit: no such claims should appear in a GO report. The claim-lab's 32 simultaneous Cloudflare-only reservations / one winner proof does not coordinate native GitHub schedules or external Render fallback, so it cannot close this cross-provider race.

## Required work split (no ownership crossover)

**Native publisher / schedule owner (separate reviewed Draft, NOT this PR):**
- Decide whether CLEAN should adopt `queue:max` to prevent one specific pending-run replacement mode. Prove it doesn't inadvertently let old scheduled work run after a source deadline, increase unbounded backlog, or alter original first-add semantics. A queue-max patch alone is **never** a sufficient go-live gate.
- Enumerate all actual original GitHub schedule/manual and Render-triggered fallback writers. For each workflow, prove that a rerun for the same slot cannot overwrite previously committed prospective predictions or produce a false first-add. Validate both orderings (native→recovery and recovery→native) and overlapping execution.
- Provide independent checks of status `queued/pending/in_progress/waiting/completed/cancelled`, resulting commit trees, immutable path SHAs, cutoff timestamps and `T-12` original data receipts.
- If coordinated at-most-once execution is required, define a **single authority all providers actually consult**, not only a Cloudflare Durable Object. Specify authentication, lost ACK/204/timeout handling, atomic claim point, recovery policy, token scoping and rollback. Do not add automatic releases/retries that could duplicate external POSTs.

**Cloudflare observer / research owner (this Draft PR only):**
- Keep the zero-secret standalone observer Worker separate; it has no GitHub API or PAT code.
- Retain offline exact-day 192/192 Cron and platform CPU per-invocation audit with original log retrieval provenance. Local Workerd / Wrangler green tests are not Free-plan 10ms CPU measurements.
- Continue fail-closed recovery-policy read-only tests: full 30-row GitHub first page or mismatched `total_count` => no dispatch; visibly active native main run at *any age* => no dispatch; delayed native schedules *not yet created* remain unobservable.
- Keep the SQLite claim lab separate and inert (no Cron, no GitHub or network, no production binding). Claimant-only UUID protects the lab's run-ID attribution but does not solve outside-provider idempotency.
- Do not set `CLOUDFLARE_DISPATCH_ENABLED="true"`, register the secret, or enable any recovery-capable Worker until independent production release sign-off.

**Independent acceptance auditor:**
- Demand actual Cloudflare account/version, 24h post-propagation scheduled logs and platform `cpuTimeMs` <=10 for every claimed Free-plan invocation, no lost/duplicate ticks, no mixed deployment IDs or sampled exports.
- Demand a verified GitHub `workflow_dispatch` HTTP 200 with `return_run_details:true`; independently correlate actual run ID, repository, branch, event, conclusion and created/cutoff chronology. A 200 alone is not an executed/successful capture; 204/timeout without run ID is **ambiguous**, not permission to retry.
- Demand first-add Git publication SHA and per-race pre-T−12 official source records for the same evidence chain. Separate 4-mode/CLEAN metrics and real vs simulated counts.

## GO / NO-GO decision

**NO-GO is mandatory if any of these lacks independent evidence:** (1) live Cloudflare Free CPU+Cron, (2) all cross-provider write paths and duplicate/delayed-schedule behavior, (3) validated non-overwriting immutable Git first-add and cutoff semantics under concurrent native/recovery execution, (4) real returned run ID and independent Git run outcome, (5) official pre-T−12 source receipt, and (6) authorized rollback/activation approval.

**Current independent recovery formal successes: 0.** GitHub API history checks, SQLite reservation, `queue:max`, green CI, a mocked 200 run ID and manually normalized observer logs **must not be counted as real coverage**. The safer sequence is **Observer-only Cloudflare Free → full-day CPU/Cron evidence → publisher-owned concurrency/idempotency fixes on separate Drafts → replay tests → independently authorized recovery pilot → real first-add/T−12 audit**.

This document is a *testable engineering handoff*; it does not represent a deployed or running backup.


## 2026-11-09 — native capture-slot attribution gap: run ID != requested slot

Read-only inspection of current repo source (no native workflow changes):

- `.github/workflows/clean-prospective.yml` and `.github/workflows/four-mode-prospective-capture.yml` declare `workflow_dispatch:` **without any `inputs`**. Cloudflare's dispatch body is exactly `{"ref":"main","return_run_details":true}`—it does not name an original capture slot.
- CLEAN executes `python collect_clean_prospective.py` with no `--date`; `collect(day=None)` selects today's JST date from `datetime.now(JST)`.
- Four-mode executes `python clean_four_mode_capture.py`; `collect(...,now=None,...)` also resolves the JST date using the execution-time clock. It collects whatever live, cutoff-safe candidates exist when its runner actually executes, **not an immutable snapshot of the earlier Cloudflare recovery decision time**.
- The Worker infers `slot_jst` from the Cron tick and GitHub histories. This is a **decision-time label**, not proof that the actual GitHub run carried that slot identifier to the publisher or that a given cutoff's original forecast was generated.

The Draft recovery policy now always emits `github_execution_slot_bound_proven:false` beside each HTTP-200 `github_run_id_reported` in both the summary and immutable-safe receipt. No test, synthetic GitHub 200, successful SQLite DO reservation or server-created run ID may turn this true. Node tests directly assert both native YAML `workflow_dispatch` declarations and both collectors' use of live time; Workerd mocked API tests assert the receipt still carries `false`. If native owners modify these contracts, the static tests are intended to trigger review, **not silently reclassify an old HTTP 200 as proof**.

**Why it matters:** GitHub `schedule` events can be delayed or dropped under high load; workflow-level `queue:single` may replace a pending CLEAN native capture, while `queue:max` can delay a four-mode job. A GitHub 200 response and run ID do not establish that the desired earlier slot was actually served before any per-race T−12 cutoff. Official source: [GitHub scheduled workflow delay/drop guidance](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows) and [concurrency queue behavior](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/control-workflow-concurrency).

**Publisher-owned options (not implemented in this PR):**
1. Add a versioned optional `workflow_dispatch` input such as a validated `requested_slot_jst` and immutable source/cutoff provenance; explicitly separate it from the *actual execution time*. Native owner must decide whether a delayed run can legitimately capture **still-future eligible races**, rather than backdating source receipts or publishing an expired slot. This alone does not guarantee publication before T−12, prevent duplicate writes or coordinate with Render.
2. Alternatively retain live-time collectors without a slot input, but independently reconcile **each real GitHub run ID → generated forecast path → server-confirmed first-add commit SHA → original source receipts/cutoff**. Only those per-race facts may prove an on-time saved forecast; no strict one-slot-to-one-run claim is made.

Until such independent publication evidence exists, the operational state remains **NO-GO**, and `github_execution_slot_bound_proven:false` is mandatory. Research testing only; PR #1697 Draft/unmerged, observer-only first-stage, no Cloudflare deployment, no main/Render/native Actions modification, no real GitHub POST.

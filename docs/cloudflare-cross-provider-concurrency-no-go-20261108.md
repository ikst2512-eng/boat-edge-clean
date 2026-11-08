# Cloudflare × native GitHub Actions: independent release NO-GO evidence

**2026-11-08 JST. Research-only. DO NOT DEPLOY OR ENABLE RESCUE.**
Scope: Draft PR #1697, no main/Render/native scheduled workflow modifications and no actual GitHub dispatch.

## Verified inputs vs simulated effects

The repository's current original capture workflow configuration, read from the **same PR head**:

| Capture | Native workflow | Shared schedule/dispatch concurrency group | Queue policy | In-progress cancellation |
|---|---|---|---|---|
| CLEAN | `.github/workflows/clean-prospective.yml` | `clean-prospective-capture` | **`single` (default)** | `false` |
| Four mode | `.github/workflows/four-mode-prospective-capture.yml` | `four-mode-publication` | **`max`** | `false` |

Official GitHub semantics: With default `queue: single`, **a new pending run cancels/replaces the previous pending run in the same group**. With `queue: max`, up to **100** pending runs can wait, and a further run is canceled when the queue is full. Neither mode guarantees **exactly one external POST** or a successful pre-deadline capture. [GitHub official concurrency docs](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/control-workflow-concurrency) and [May 7 2026 change](https://github.blog/changelog/2026-05-07-github-actions-concurrency-groups-now-allow-larger-queues/).

**These are source-verified rules, not an observed production incident.** The new `cloudflare/cross_provider_queue_lab.mjs` runs an **offline deterministic queue-rule simulator**, with six Node regression tests in `tests/cloudflare_capture_wakeup.test.mjs`. Tests also read the *actual workflow YAML* and must fail if the concurrency assumptions change. This lab makes no fetch, GET, POST or scheduled API calls, reads no secrets, and is not imported by either live-capable Worker entrypoint.

## Minimal counterexamples reproduced by the simulator

1. **CLEAN original schedule displacement:** Existing prior CLEAN capture is running; the next original `schedule` run is pending; Cloudflare rescue `workflow_dispatch` arrives in the **same GitHub concurrency group**. In default `queue:single`, the newer rescue **cancels the pending original schedule**, even with `cancel-in-progress:false`. This is a possible chronology, not proof it has occurred.
2. **Durable Object alone does not fix CLEAN:** Even if **32 parallel Cloudflare invocations** become exactly one winning DO reservation, that one Cloudflare dispatch can still replace the existing pending **native** schedule; native GitHub does not acquire Cloudflare's DO lock.
3. **Four-mode queue:max is not idempotency:** Original native schedule, one Cloudflare DO claimant, and another uncoordinated provider can remain **three separate pending runs**. Serial execution cannot establish exactly-once external calls, one first-add Git commit, or T−12 quality.
4. **Four-mode saturation:** If 100 other requests already occupy the pending queue, a new recovery request is **canceled**. The number is the documented queue capacity, not measured current backlog. It is **not evidence that this actually happened**.

The simulator explicitly outputs `actual_github_run_evidence:false`, `verified_cross_provider_idempotency:false`, `production_dispatch_safe:false` for every case. A green test is **negative proof that this architecture has a possible unsafe interleaving**, not proof that a real attempt failed or that release is now safe.

## Remedy options — separately owned and NOT applied in this PR

**A. Preserve pending native CLEAN schedules:** The capture workflow owner may assess whether `queue:max` for CLEAN is appropriate for the 63 daily slots and existing 6-minute timeout. That would avoid the **specific pending replacement** of `queue:single`, but does **not** prevent duplicate POSTs, backlog, late forecast first-add, or cross-provider collisions. Any change requires capture-team scenario tests on its own Draft and no auto-merge.

**B. Cross-provider idempotent publication:** Require every writer path (native GitHub schedule, Cloudflare, Render fallback and any other third party) to participate in a **single authoritative per-slot or per-race claim**, or prove that concurrent executions cannot replace/displace a required run and that immutable first-add, timing and source checks hold despite duplicates. One isolated Cloudflare SQLite DO is insufficient. Formal agreement needs the original publisher owners. Do not unilaterally edit the active collection workflow.

**C. Maintain shadow observer-only operation until evidence exists:** This remains the safe default. Keep `CLOUDFLARE_DISPATCH_ENABLED = "false"`, empty-key observer separated from the recovery-capable bundle, no PAT or external dispatch, no live deployment in this audit.

## Explicit go/no-go criteria (all necessary)

- The owner of both native workflow schedules and independent Render fallback approves a **documented cross-provider coordination or safe-publication contract**. All production-capable call paths and concurrency groups are enumerated, and pending-run displacement cases have passing independent tests.
- A rollback/failure-mode analysis covers concurrent Cloudflare calls, delayed native schedule arrival, GitHub POST 204 or invalid 200, timeouts, canceled or pending jobs, full `queue:max` backlog, failed Git push, and loss of one claimant token **without blind retries**.
- Owner-controlled **Observer-only** Cloudflare Free deployment and a retained complete day of platform Cron/cpuTimeMs records prove real CPU <=10ms on every invocation and actual scheduled traffic, not synthetic tests. Review exact deployment provenance and original logs.
- Only after safe duplication behavior is demonstrated: least-privilege GitHub token as private Cloudflare Secret, explicitly reviewed live recovery enablement, independently correlated GitHub workflow run IDs/outcomes and immutable forecast first-add SHA, and independently audited official pre-T−12 source evidence.
- Production changes and merge remain **blocked** while any item is unknown; do not convert a model simulation, Workerd mock, HTTP 200, accepted DO claim or passing CI into formal recovery certification.

**This research deliberately does not change `main`, native GitHub workflow YAML, Render, or any live Cloudflare account.**

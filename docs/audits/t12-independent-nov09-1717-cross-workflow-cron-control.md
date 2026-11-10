# 2026-11-09 17:17 JST — same-hours independent controls for sparse T−12 collector schedules

**Scope:** independent read-only T−12 research audit, Draft PR #1694. No production cron, official source fetcher, model, GitHub main, UI, Render, or frozen forecasts changed. **No formal T−12 certification**, and **no formal hit-rate denominator**.

## Why this control was necessary

Previous read-only schedule telemetry showed `.github/workflows/research-live-preview-evidence.yml` has unusually few observed `event=schedule` run creations compared with its declared `*/5 0-12 * * *` UTC 5-minute slots. Those counts alone cannot distinguish a collector-workflow-specific problem from a broader repository/workflow scheduling behavior. They also do not identify any precise missed cron slot, GitHub platform fault, or HTTP attempt.

An independent comparison now takes the **same completed 00:00–12:55 UTC creation-hour window (09:00–21:55 JST)** for three existing workflows with distinct declared cadences. The comparison begins **Nov 6**, *after* known workflow creation/cron changes on Nov 3–5. Current cron definitions are still configuration assumptions for historical events, not independently proven effective scheduler registrations at each run.

## Direct GitHub metadata results — three completed days Nov 6–8

[Exact code-head read-only GitHub CI #42584763159](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42584763159), observed 2026-11-09 17:17 JST, using authenticated, date-scoped `event=schedule` REST queries with strictly validated complete pagination:

| Workflow (common UTC 00–12 window) | Intended slots over Nov 6–8 | GitHub run creations within those hours | Run-creation / nominal ratio | Creations outside same window | All-hour run conclusions |
|---|---:|---:|---:|---:|---|
| `research-live-preview-evidence.yml` official 2-original source collector, each 5 min | **468** | **5** | **1.07%** | 3 | 7 success, 1 failure |
| `entry-course-t12-baseline.yml` independent T−12 baseline collector, each 5 min | **468** | **6** | **1.28%** | 3 | 5 success, 4 failure |
| `clean-prospective.yml` independent CLEAN collector, each 15 min | **156** | **11** | **7.05%** | 6 | 17 success, 0 failure |

Observed within-hour creations, by UTC date:

| UTC/JST race day | Source pair, 5-min | Entry T−12, 5-min | CLEAN, 15-min |
|---|---:|---:|---:|
| Nov 6 | 1 | 2 | 3 |
| Nov 7 | 2 | 2 | 4 |
| Nov 8 | 2 | 2 | 4 |

**Strong finding:** Low `event=schedule` creation counts occur in **at least three distinct workflows**, not just the official source pair collector. **Bounded conclusion:** This is evidence of a *cross-workflow pattern of sparse recorded schedule activations*, **not proof that GitHub's own scheduler caused it**. Each workflow could also have its own event registration/concurrency/operational behavior. A completed green Actions run may capture zero official originals.

There are 463, 462, and 145 **creation-count shortfalls** against the nominal common-hour slots respectively. These are **not** proved missed individual cron slots or raw HTTP failures. The out-of-hours creations could reflect delayed scheduling and are deliberately not re-assigned to any intended slot.

## New reproducible fail-closed audit

Added:

- `scripts/audit_t12_cross_workflow_schedule.py`: read-only authenticated schedule-only GitHub REST inventory; single-page and multi-page consistency verification; immutable full-day scope; exact workflow path identification; no source or model mutations; no claims of actual scheduler root cause, formal forecast eligibility or source HTTP attempts.
- `tests/test_audit_t12_cross_workflow_schedule.py`: 12 cases for common-hour denominators, off-hour classifications, unknown/duplicate run identities, bad GitHub response/pagination, old cron configurations, partial days, security-invalid GitHub repo components, stale clocks and green-run overclaims.
- `.github/workflows/audit-official-pair-schedule-continuity.yml`: reruns the comparison for Nov 6–8 and uploads `reports/t12_cross_workflow_schedule_controls.json` as part of the existing independent audit artifacts.

The first CI caught a **real validation gap** in this new script: `../repo` was structurally allowed by a liberal repository regex. Fixed by explicitly rejecting dot and dot-dot GitHub path components **before calling the API**. Final exact code-head [run #42584763159](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42584763159) **PASS 144/144 tests** (existing 132 + new 12), authenticated real three-day comparison passed and Nov9 original source-vs-forecast raw replays also passed. CI artifact [#13658273946](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42584763159/artifacts/13658273946) includes the newly generated control JSON. The earlier failing run #42584660905 is superseded by the passing head and is not presented as a green run.

## Existing Nov 9 T−12 evidence remains blocked

The same latest CI verified the Nov9 source artifact [#13652131213](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42567310743/artifacts/13652131213): **2 legitimate official two-original pairs** for 宮島10R and びわこ10R, **4 pinned earlier CLEAN/four-mode forecasts**, **0 forecasts generated after final official source receipt**. Neither official racelist original nor model input consumption, independently verified first Git remote acceptance or final race entry were established. The official three-original permanent evidence branch still only had Nov3 as of last independent readback. **Formal T−12 0, denominator undefined.**

## Scoped owner ① handoff

1. Investigate shared event scheduling/activation mechanics across **three** workflows, beginning with GitHub workflow activation/configuration, scheduled actor, queue/concurrency and actual recorded events. **Do not infer GitHub root cause from counts alone.** Correlate with workflow-run and non-schedule fallbacks but never label a fallback `workflow_dispatch` event as a true `schedule`.
2. In owner ①'s independent collector PR, establish actual timely official `racelist` + 6/6 beforeinfo/exhibition + 120/120 odds originals for the *same race*, then a **new** prospectively frozen forecast generated after the last official source arrival and before official T−12. Avoid changing, replaying as new, or backdating existing early CSV forecasts.
3. Independently verify the Git original consumption, initial remote acceptance and final entry. Continue to output `formal=false` until every gate is proven. **Do not merge #1694 automatically or change main.**

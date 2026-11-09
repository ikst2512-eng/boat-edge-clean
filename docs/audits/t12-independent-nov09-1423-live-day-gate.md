# 2026-11-09 14:23 JST — independent LIVE T−12 capture/remote-originals audit

Status: **research-only; formal T−12 certificate 0; formal accuracy denominator undefined.** Read-only audit-only Draft PR #1694. No source capture, cron, model, Render, main or past forecast changed.

## Actual live day, as observed by authenticated GitHub Actions

[Read-only PR CI run #42566970921](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42566970921), exact tested code head `2e2b4e26c9b816e4a4e3e38f68b89453bd2c0704`:

- All audit-only unit tests **122/122 PASS**: 12 schedule + 23 frozen pair chronology + 16 three originals/frozen + 10 external branch presence + **12 same-day blocker checks** (including two new no-collector-start tests) + 16 scheduled pair ZIP + 13 real archived source/forecast + 9 extracted artifact replay + 11 multiday trend.
- Day-in-progress snapshot taken **2026-11-09T05:23:18.269800+00:00 (14:23:18 JST)**. Active collector config `*/5 0-12 * * *` UTC = **09:00–21:55 JST daily**.
- **65 nominal five-minute slots elapsed** as of 14:23 JST (09:00–14:20 inclusive). **0 observed Nov 9 `event=schedule` creations** for `.github/workflows/research-live-preview-evidence.yml`; observed in-hours coverage **0/65 = 0%**. There are 91 *future* nominal 5-minute slots that must **not** be counted as missed.
- New explicit audit reason `no_collector_schedule_run_created_in_declared_hours`, with `collector_no_in_hours_schedule_runs_observed=true`. This **does not attribute 65 source HTTP failures**, nor prove whether GitHub skipped, delayed, cancelled or otherwise failed any exact slot. A private event with no GitHub run creation may not be inferred from this metadata.
- GitHub three-original research branch `research-t12-external-evidence` at pinned SHA `d0ed89f146dff117021c2bc042b20259d6715515` has only `external_three_t12/20261103/`, with **no Nov 9 or Nov 8 day directory**; **0 durable three-original race directories** in that specific branch. This does **not** establish the absence of other temporary artifacts in all Actions runs.
- An observed [Nov 8 UTC late schedule run #42507148015](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42507148015) started at **2026-11-09 02:52 JST** (UTC Nov 8 17:52), outside the collector's declared 09–21:55 JST cron hours. Its own source capture `OFFICIAL_JOINT_BATCH` reports **0 eligible candidates, 0 official beforeinfo originals, 0 official odds originals, 0 complete pairs, status=no_pre_t12_candidate**. The green job is not an official source receipt and is not counted as a Nov 9 UTC in-hours run.

## Eight COMPLETE historical UTC/JST racing days

The same read-only CI independently queried all date-scoped GitHub schedule histories 2026-11-01 through 2026-11-08 **after each day's full nominal cron window elapsed**.

| Metric | Historical Nov 1–8 result |
|---|---:|
| Configured nominal 5-minute slots | **1,248** |
| Observed `event=schedule` run creations, all creation hours | **19** |
| Created within declared UTC 00–12 hours | **11** |
| Created outside declared hours | **8** |
| Successful workflow runs | 18 |
| Failed workflow runs | 1 |
| Observed run-creation to nominal slots | **1.52%** |

**Important:** 1,229 is an invocation-count shortfall, *not* 1,229 proven missed slot identities or HTTP request failures. Off-hours schedule creations might reflect delayed execution; time attribution is not confirmed. The pattern predates the November 4 patch that added the official pair acquisition step. Treat as a recurring activation reliability issue, not verified GitHub or Render root cause.

The CI also re-ran the historical real Actions original-vs-forecast gate, finding across 8 source-pair races from Nov 5–8: **3 independently complete two-official-original races, zero official three-original races; 6 matched immutable CLEAN/V2 forecasts, none generated after the last official original receipt**. These source-pair observations do **not** establish legitimate T−12 predictions; the immutable source link and first GitHub remote acceptance remain missing.

## Audit-side change this turn

Updated `scripts/audit_t12_blocker_join.py` to distinguish **zero observed in-cron-hours scheduled collector runs** from an observed run whose source request failed. Added two fail-closed tests to `tests/test_audit_t12_blocker_join.py` and updated the read-only `.github/workflows/audit-official-pair-schedule-continuity.yml` with additional **current UTC / same JST racing-day** snapshot:

- `reports/official_pair_schedule_live_day.json`
- `reports/official_three_archive_live_day.json`
- `reports/official_t12_live_day_blockers.json`

Historical Nov 8 & multiday audit reports remain separately preserved. The current-day snapshot is **evidence as-of runtime only**, not a claim of later-day completeness or automatic live source ingestion. On GitHub API 403/404/timeout, the audit fails closed; it will not silently promote absent events or originals.

## Prioritized handoff, without crossing ownership boundaries

1. **Collector owner ① (blocker):** Investigate actual `event=schedule` scarcity and off-hours creation. Separate GitHub Actions scheduling delays/omissions, workflow concurrency, disabled workflows, cron trigger mechanics, and true HTTP failures using native GitHub run metadata; do not attribute cause prematurely. Restore independently observable actual capture attempts during race/T−12 windows in collector's own scoped Draft PR.
2. **Collector/model input owner ①:** Obtain and durably publish actual official racelist + six-row beforeinfo/ST/exhibition + complete 120-way odds for one race *before official T−12*, create a new immutable prospective prediction *strictly after* the last original receipt, and preserve evidence of actual consumed raw source bytes.
3. **Independent T−12 auditor:** Replay remote archived originals from exact Git SHA and validate initial independent GitHub receipt and final race entry. Only a full prospective chain can change formal 0. Do not reuse old CSV forecasts or change main.

**Do not merge Draft PR #1694 or promote accuracy denominators.**

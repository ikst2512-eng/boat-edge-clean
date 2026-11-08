# 2026-11-08 ~22:15 JST — completed-day T−12 collector execution history (independent audit)

**Scope:** Draft PR #1694 audit-only work. The official two-original collector's schedule metadata is not official source evidence. Formal T−12 race count remains **0** and the formal accuracy denominator remains **undefined**.

## Authenticated, live GitHub API data

[Exact-head Actions run #42483984223](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42483984223) replayed the entire **2026-11-01 through 2026-11-08** `event=schedule` history for `.github/workflows/research-live-preview-evidence.yml`, using a read-only token. All eight dates' declared 09:00–21:55 JST / UTC 00:00–12:55 five-minute windows were complete. Each day has **156 nominal configured slots**, for **1,248 nominal eight-day slots**. Both the run metadata and each day/pagination boundary were independently checked.

| Racing day (JST) | Created GitHub schedule runs | Created during declared UTC 00–12 hours | Created outside those hours |
|---|---:|---:|---:|
| Nov 1 | 3 | 2 | 1 |
| Nov 2 | 2 | 1 | 1 |
| Nov 3 | 2 | 1 | 1 |
| Nov 4 | 2 | 1 | 1 |
| Nov 5 | 2 | 1 | 1 |
| Nov 6 | 2 | 1 | 1 |
| Nov 7 | 3 | 2 | 1 |
| Nov 8 | 2 | 2 | 0 |
| **8-day total** | **18** | **11** | **7** |

- **Observed run creations / configured slots: 18/1,248 = 1.44%.** The numerical shortfall is **1,230**, which does **NOT** prove 1,230 skipped event triggers, 1,230 HTTP failures or exact missed slot identity.
- **17** recorded schedule runs concluded success, **1** failed (Nov 7), but green runs can be empty. The 20:59 JST [Nov 8 run #42478155155](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42478155155) reported **`eligible_candidates=0`, `beforeinfo_originals_saved=0`, `official_odds_originals_saved=0`, `complete_pairs_before_t12=0`**. Do not equate green Actions success with complete official original acquisition.
- Outside-hours creations on Nov 1–7 could represent delayed scheduled invocations. **Root cause of invocation discrepancy is not established** from run metadata. No source owner or scheduled workflow was modified.
- For **Nov 8 after the configured window closed**, only **2** relevant schedule runs were observed, against 156 nominal slots (1.28% creation/slot ratio). The read-only official-three-original durable branch `research-t12-external-evidence`, pinned to commit `d0ed89f146dff117021c2bc042b20259d6715515`, still had **0** Nov 8 saved race directories.

## Replay of real original source files and immutable forecasts

The same audit CI independently replayed **four** archived official-pair Actions run artifacts (Nov 5–8), validating source originals, manifests and replayed beforeinfo/odds source conditions. The result was:
- **8** race-pair attempts inspected; **3** complete official two-original pairs (Nov 5 びわこ11R, Nov 6 鳴門10R, Nov 8 江戸川9R), **5** incomplete.
- **6** matching historical forecast blobs re-read from **main SHA `6b371040fd2fc4398bfa882e6557c333cc0800c8`**; **0** forecast generations strictly after their same-race official pair receipts. CLEAN source kinds were public CSV; V2 snapshots lacked official beforeinfo. Historical forecasts cannot be retroactively credited with later official source consumption.
- Source original archive reinspection uses authenticated GitHub artifact metadata and **independently replayed extracted original+manifest bytes**. As the CI report explicitly notes, it **did not itself rehash the original ZIP byte stream** (a prior separate download check did). Do not overclaim the CI's ZIP digest verification.
- **Official three-original racelist+beforeinfo+odds linkage: 0 proven**. Independent actual model input consumption, original GitHub first remote acceptance and final entry remain unverified. No formal predictions are promoted.

## New audit safeguards

- `scripts/audit_t12_multiday_schedule_trend.py` independently calls the existing strictly paginated schedule inventory for each of up to 14 fully elapsed UTC racing days; validates event creation hours, counts, unique run IDs, daily scope, full-window observation and source-certification hard-false flags. Rejects unelapsed end dates, forged event times, 403, malformed pagination through the underlying inventory, and claims of verified missing slots.
- `tests/test_audit_t12_multiday_schedule_trend.py`: **11** edge-case tests, including the observed eight-day count fixture, 403, forged 00–12 vs outside-hour run metadata, incomplete day and conflicting totals.
- The read-only PR audit workflow now uploads `reports/official_t12_eight_day_schedule_trend.json` beside existing official pair schedule continuity, three-original archive presence, same-day blockers, and real archived original-to-forecast replay reports.

[Exact code-head CI #42483984223](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42483984223) **PASS 120/120** (12+23+16+10+10+16+13+9+11). Formal source/accuracy gates remain hard false. Other independent prospective accuracy CI can still fail because evidence is unverified; never relabel such failure as success.

## Strict handoff, no duplicate fixes

**Owner ①:** Review historical 18/1248 observed creation-count discrepancy, scheduler conditions, GitHub Actions runtime behaviour and alternative activation sources, **without assuming precise missing slots**. Improve actual prospective official source collection in its own owned Draft PR, with the **third official racelist source** preserved together with six-boat beforeinfo and unique 120-way HTML odds before the *official* T−12 deadline. Generate new model prediction **after** actual source receipts; prove consumed original input bytes, first remote Git receipt and final entry. Do not backfill official status onto previously frozen morning forecasts.

**PR #1694:** Audit code/tests/docs/metadata only; **Draft**, no automatic main integration. Actual formal count **0** until independently verified source-to-model-to-Git first receipt chain exists.

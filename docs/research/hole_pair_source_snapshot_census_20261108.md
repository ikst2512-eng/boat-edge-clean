# Hole pair future cohort — exact immutable-main source snapshot roster (NONFORMAL)

**2026-11-08 JST / Draft PR #1685 / no release / no production integration**

## Why this check was added

The old `HOLE_PAIR_FUTURE_ACTIONS_BATCH_V1` had
`eligible_forecasts_examined`, `frozen_count`, and
`excluded_by_reason` (counts), but no race-code roster for exclusions.
Two different omissions or substitutions can have the same counts, so a
`frozen_count + sum(excluded_counts) = examined` assertion is insufficient
for 300+300 prospective cohort integrity. It would also make later
per-venue and cutoff audit coverage impossible for excluded races.

## Added, gated research-only capture fields

In the *future-only* `workflow_dispatch` frozen artifact, record:

- `source_forecast_codes`: complete sorted 12-digit race IDs from the one explicitly pinned `origin/main` Git snapshot, BEFORE reading results.
- `excluded_race_codes_by_reason`: sorted IDs for each original `freeze()` non-success reason, alongside the previous unchanged `excluded_by_reason` totals.
- `source_snapshot_coverage`: explicit one-to-one membership audit and cutoff-sorted candidate IDs from `research/hole_pair_universe_coverage.py`. Its `source_main_commit` is the captured immutable main commit, not mutable branch label.
- Every ID from that snapshot must appear **exactly once**, either as a frozen original candidate or as an excluded code with an allowed original reason. Extra, missing, conflicting, duplicated, wrong-day, malformed, altered-selector or unpinned-source entries fail the prospective batch step before the JSON artifact is saved.
- No change to fixed method `HOLE_PAIR_NOV06_LOCKED_RESEARCH_V1`, selector hash, Top5 preservation, actual candidate tickets, or per-race freeze timing. This adds audit evidence only, never forces altered picks.

## Limits: snapshot coverage is NOT total-day or formal cohort proof

The source universe is the exact forecast ID listing in *one immutable main commit* inspected by a manually launched job; it does NOT guarantee all originally scheduled races, all 24 venues, or all forecasts captured during the race day. The outer workflow remains **not registered on default main**, so this new artifact format is not yet being created by a real `workflow_dispatch`. No pre-result remote receipt / official six-boat beforeinfo + exhibition / 120 odds + official deadline proof is performed. A passing PR CI is not proof that any future race was captured, nor may excluded/missing races be counted as misses or silently replaced.

The next 300 pilot + untouched next 300 confirmation cohorts remain **not started and 0 formally eligible**. This per-snapshot validator also does **not** certify idempotence across independent, overlapping future dispatch runs: cross-batch first-receipt locking and chronology will need separate authorized verification. Never add the same race twice or allow a later batch to replace a failed first attempt.

## Actual CI evidence

- New unit tests: **15/15** passed, including omission with equal counts, duplicate frozen and exclusion ID, unsupported reason, wrong day/venue/date, corrupted method, missing Git blob, and empty snapshot not proving a whole day.
- [GitHub Actions #42478021402](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42478021402): `success`; existing Python 49, SQLite 9, D1 chain 10, new snapshot census 15, default branch launch 8 all passed; existing Node tests also passed.
- Real candidate freezer and its candidate artifact upload both **skipped** on `pull_request`. Readiness artifact only. Log `DISPATCH_PREREQUISITE False`.
- No main, Render, deployed Cloudflare, collector, frontend, official T−12 collector, or actual betting selector change. No auto-merge, PR remains Draft. Never reuse researched Nov6–8 as prospective confirmation.

**Status: stronger *prospective design validation*, zero new formally verified prospective race records.**

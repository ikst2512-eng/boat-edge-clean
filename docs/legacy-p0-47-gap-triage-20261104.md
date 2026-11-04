# P0 47 source-index gaps: dated triage and source spot-checks (2026-11-04 JST)

Read-only follow-up to Issues #708/#329 and draft PR #1559. Source inventory is the previously pinned legacy tree `f38204105a979aa6ef5293d1b9cad854056faadd`, not a fresh inventory of live heads. No production, prediction, scoring, source, odds or result was altered.

## Exact cohort

From 1,125 P0 legacy-only prediction races, **46** lack the expected `data/site_odds/{race_key}.json` *index reference* and **1** lacks the expected `data/site_prediction_history/{race_key}.json` reference. These groups are disjoint: 47 total gaps; 1,078 have all five standard source categories indexed. Source files may still exist in other locations/history; index absence must not be called actual data loss.

Missing odds-reference counts by date:
- **2026-10-08: 36** races.
- **2026-10-09: 9** races.
- **2026-10-10: 1** race.
- **Oct 11 onward: 0** races in this *specific pinned P0 index*. This is not proof that newer sources have intact cryptographic provenance.

The separate single missing history reference is Naruto 5R `20261008-14-05`.

## Direct-source representative observations

Pinned raw GitHub fetch of missing odds paths for Kiryu 3R `20261008-01-03`, Kiryu 10R `20261008-01-10`: HTTP 404. Source snapshots for six sampled odds-gap races (Kiryu 10R, 20261008-03-08, 20261008-05-06, 20261009-01-04, 20261010-18-06, plus earlier Kiryu 3R) all have `odds_sha256=null`; **this is six sampled cases, not an all-46 statement**. They do not gain a matching odds record by manufacturing one from later prices.

Naruto 5R `20261008-14-05`:
- `data/site_prediction_history/20261008-14-05.json`: direct fetch at pinned tree HTTP **404**, search by race ID did not locate a `site_prediction_history` copy on the current default branch.
- `data/site_prediction_snapshots/20261008-14-05.json`: Git blob `dc4425ba44971d572f0887059ad25321215e4b55`, first_saved_at declared 2026-10-08T01:24:05.911944Z; `SITE_REFERENCE_V122`, lead time 2.9 min. The Git first-add commit itself has NOT been separately verified.
- `data/site_prediction_audit/20261008-14-05.json`: blob `cae2f734d716a723d9820a8a285fba745b6f130d`, `pass=true` as a self-contained SITE audit, but `settlement.available=false` and winner/payout null.
- `data/site_odds/20261008-14-05.json`: blob `7c53df3f87875aaf27c50bc135820bbc99594405`, 120 combination entries, fetched at 2026-10-08T09:53:00+09:00; its cryptographic hash against snapshot has **not** yet been verified in this follow-up.
- `data/site_results/20261008-14-05.json`: blob `bd9c73c8ab88b1ec37c2a905a315654f0d3e5021`, status `trifecta_not_established`, result `null`; **do not infer win/loss/payout**.
- A default-branch keyword search of race ID found snapshot/audit/odds/results but no site history; this does not prove absence in all historical commits/other storage.

## Fail-closed field statuses for next operator run

- Missing index: `NOT_INDEXED`
- Expected path independently returns 404 at pinned tree: `PINNED_PATH_NOT_FOUND`
- Snapshot odds SHA null: `FORECAST_ODDS_HASH_ABSENT`
- Different SHA for same bytes: `SHA_MISMATCH` **only if actually measured correctly using standard crypto**
- Old-site 3T result unavailable: `NO_SETTLEMENT_OR_NO_TRIFECTA`
- Independent durable off-repo original bytes / SHA256 restoration: `NOT_VERIFIED`

A local 47-row `boat_edge_p0_gap_triage_20261104.csv` accompanies this audit; SHA256 `65363e0655b0cbfdf3783c39d7a1314eea7f7cc2da2bd1f054e7fad8598f1781`. The CSV indexes old source blob references only; **no source bytes included**.

No automatic patching or historical score adjustment is permitted. Continue to investigate alternative paths and prior Git commits, then independently back up exact bytes. **DELETE_BLOCKED / LEGACY_WRITER_STOP_BLOCKED.**

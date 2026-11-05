# 2026-11-06 JST — Independent T−12 evidence audit (pre-opening snapshot)

**Scope:** read-only independent inspection of GitHub `main`, original GitHub Actions job logs and the already-connected Render deploy inventory. Evidence at **2026-11-06 03:50 JST**. This is not a forecast or a certification and does not imply full-day completeness.

## Immutable record inventory

At main `71ab5352c98634246a00bfa3c1a2c32b5b92ab09` (tree inspection, not the first 1000 names from a paginated contents listing):

| Tree | 2026-11-05 race JSON | 2026-11-06 race JSON |
| --- | ---: | ---: |
| `prospective_predictions/` | 111 | **0** |
| `four_mode_forecasts/` | 106 | **0** |
| `schedule_snapshots/` | 1 | **0** |

No Nov 6 candidate first-add Git history can be audited, because there are no corresponding Nov 6 original files in this exact main tree. This is **pending pre-opening evidence**, not zero failed races, not a zero-percent success rate, and not proof that a scheduled writer will or will not capture racing-hour data.

## Real scheduled runs — distinguish job success from source success

- [Preview capture schedule #42082749439](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42082749439), GitHub-created **2026-11-05T18:17:08Z = Nov 6 03:17:08 JST**: workflow `completed/success`; job log `capture_source_status=not_yet_expected available=0 unavailable=5 capture_invalid=0 rows=0`; `verified_preview_pair_audit` shows `paired_complete_6boat_stt_tkz=0`, `paired_complete_12min_observable=0`, `t12_evidence_by_race=[]`. The source read did not succeed. Artifact `late-preview-evidence-42082749439` ID `13441736597`, **1,087 bytes**, not an independently re-audited official three-original success.
- [Four-mode capture watchdog #42078433737](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42078433737), **Nov 6 02:49:56 JST**: `completed/success`; the production log verdict at 02:50:06 JST is `FOUR_MODE_WATCHDOG action=no_dispatch capture_hours_jst=false`; CLEAN prospective watchdog also `no_dispatch` / `out_of_hours_or_untrusted_trigger`. A watchdog success is not new forecast storage or T−12 evidence.
- [Live official odds probe #42057471872](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42057471872), **Nov 6 00:41 JST**: `source_status=no_upcoming_race`; races sampled=0, requests=0, 120-way proof=0; `source_unavailable`. It was an out-of-hours diagnostic, not an actual race failure.
- [Real predeadline racecard check #42057361802](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42057361802), **Nov 6 00:40 JST**: failed with `SCHEDULED_LIVE_SAMPLE_OUTSIDE_JST_RACING_WINDOW`. It must not be counted as source-verified or a failed eligible race.

## Persisted historical rejection, unaffected by today's code

- [CLEAN prospective independent accuracy checks #42074151538](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42074151538) original job logs: `audit_clean_post_fix_cohort.py` rejects **111/111 Nov 5 records** with `first_commit_same_second_unverified`; local-first-add passed=0.
- Archive gate in the same run: **1085/1085** candidate files remain rejected: **974** `source_receipt_after_generation` (Oct 28–Nov 4) and **111** `first_commit_same_second_unverified` (Nov 5). Neither is a scored miss.
- Merged [#1690](https://github.com/ikst2512-eng/boat-edge-clean/pull/1690) adds a future capture-only Git post-generation *whole-second* guard. It does **not** prove GitHub's independent initial receipt, repair Nov 5 immutable files, or authorize formal scoring.
- Independent date isolation [Draft #1694](https://github.com/ikst2512-eng/boat-edge-clean/pull/1694) has exact-head [first-add evidence CI #42074150786](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42074150786) `success`, six tests. The separate historical archive gate's expected red state remains meaningful; do not mask it.

## Still absent — per-race official T−12 formal evidence

For a **single same-race code** require all original bytes/manifests, original digest checks, independent receipt timestamps and official source identity: (1) official racelist and six registrations, (2) official beforeinfo with six unique boats, six exhibition times, tilt, six start-exhibition readings and course mapping, (3) official 120-unique-combination trifecta odds, (4) one official deadline yielding T−12, (5) all three HTTP receptions before or at T−12, (6) immutable candidate generated after inputs and first Git-added after generation yet before T−12, and (7) independent initial *remote* receipt evidence. Preserve a separate gate for final entry and formal publication.

As of this snapshot Nov 6: **0 candidates were available to assess**, **0 formally certified**, **success rate not measurable**. Even the existing `scripts/audit_three_official_t12_originals.py` deliberately returns `full_t12_source_certified=false`, `t12_eligible=false`, and `forecast_usable=false` for complete research observations. Do not override those flags.

## Next verification after actual racing-hour first saves

Run `python audit_clean_post_fix_cohort.py --day 20261106` on a full-history checkout, archive its stdout and actual run ID, then check Git first-add-original byte equality, first committer chronology and remote observation **separately** from raw official three-source manifests. Record a per-race PASS / REJECT / UNVERIFIED (with exact failure reason), not a fabricated overall rate. The collector, writer, cron and Render are owned by thread ①, and this independent audit must not duplicate any writer change.

**Change scope of this PR:** audit-only day filter, tests/CI, and this observation report. No `main` writes, model changes, official approval or auto-merge.


## Independent source-capture continuity gap (inspected at ~04:00 JST)

- [`official-three-original-t12-observation.yml`](../../.github/workflows/official-three-original-t12-observation.yml) has **no `schedule` trigger**: only `workflow_dispatch` and code-path `pull_request` (the Nov 3 matrix was retired intentionally to avoid stale live race IDs). It does not automatically collect a Nov 6 triple.
- Dedicated `research-t12-external-evidence` branch exists, but Git tree `external_three_t12/` contains only the **`20261103/`** date at SHA `d0ed89f146dff117021c2bc042b20259d6715515`, last archival commit Nov 3 17:01 JST. No Nov 6 three-original evidence has been remotely archived there at inspection time.
- Render service inventory (workspace `tea-db8svlcs728c73avi3h0`) lists the **`boat-edge-clean` web service only**, not a dedicated recurring Cron Job. The external research runner exists in code, but no configured live external automatic observation was confirmed. New paid recurring infrastructure is not provisioned without operator approval.
- Thus even a later *locally* well-timed Nov 6 CLEAN Git first-add **cannot by itself prove official three-original T−12 coverage**. The capture-owner workflow ① must separately decide a supported race-time evidence collector; this independent audit does **not** add a scheduled writer, dispatch race jobs before official dates are known, or quietly relax source and final-entry gates.

## 04:00 JST — actual PR dry-run of date-scoped evidence

- The existing audit-only workflow now executes the same checkout twice: the original all-post-fix gate **remains failed** for Nov 5's 111 same-second unverified candidates, then a deliberately non-certifying **per-JST-day report** is uploaded, even if there are no current-day candidates. No additional scheduled workflows or production collection calls.
- Exact PR-head [Actions run #42089564003](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42089564003) logs `POST_FIX_CURRENT_JST_DAY` at `day_jst=20261106`, `candidate_count=0`, `status=pending_no_new_capture`, `formal=false`, `remote_first_seen_verified=false` with archived artifact `13444722031`. Distinct immutable archive audit remains red by design; no historical false promotion.
- [CI #42089563834](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42089563834) succeeds; full independent-evaluation unit-test job in #42089564003 executes **43/43 tests successfully** while global original-evidence gates remain deliberately failed.


## 04:05 JST — independently verified day-gate and external-source-archive state

- Current `main` ref `71ab5352c98634246a00bfa3c1a2c32b5b92ab09` remained unchanged at this observation. Its original Git Tree directories `prospective_predictions/`, `four_mode_forecasts/`, `schedule_snapshots/` still have **0 November 6 race files**.
- [PR exact-head run #42089924462](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42089924462), source job `127464966697`: `POST_FIX_CURRENT_JST_DAY {day_jst:20261106, candidate_count:0, status:pending_no_new_capture, formal:false, remote_first_seen_verified:false}`. Separately, cumulative post-fix output retains Nov 5 `first_commit_same_second_unverified:111` and fails the original gate, as intended. The unit-test job passed; [day audit CI #42089924472](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42089924472) passed eight tests at exact head `1a1b76fe6b72fe55818c522acc30faaf4016b4ff`.
- Independent lookup of GitHub branch [`research-t12-external-evidence`](https://github.com/ikst2512-eng/boat-edge-clean/tree/research-t12-external-evidence/external_three_t12) returned commit `d0ed89f146dff117021c2bc042b20259d6715515`. The entire date-directory listing under `external_three_t12/` contains **only `20261103/`**, with no `20261106/`. This is a verified absence **within this evidence branch**, not a claim to have exhausted every ephemeral Actions artifact or external source.
- Independently inspected the current `.github/workflows/official-three-original-t12-observation.yml` triggers: `workflow_dispatch` and `pull_request`, **no `schedule`**. Other separate research workflows may collect subsets, but no automatic authoritative same-race trio-plus-remote-first-receipt result is certified by this observation. Late-preview scheduler's opening-hour capture is not a substitute for official racelist/odds/first remote receipt.
- **Certification:** no newly eligible Nov 6 race at this time; `formal_t12_certified=0`; denominator for a successful first-add rate or prospective accuracy is **undefined**. No collector/cron/Render/model/official certification gate was changed. Source collection work and future race-hour verification remain with separate owner ①.

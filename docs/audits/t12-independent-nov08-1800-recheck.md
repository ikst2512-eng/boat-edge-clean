# 2026-11-08 18:01 JST — independent T−12 race-level recheck (research only)

Scope: independent review of **actual 2026-11-08 Actions artifacts**, race-matched official source originals, frozen main forecasts, and Git commit history. This is a read-only audit on the existing Draft PR #1694. No historical backfill, collector change, forecast change, automatic merge or formal scoring authorization.

## Evidence provenance

- Source-pair collector [run 42450048245](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42450048245), artifact 13604969020, exact ZIP SHA256 `2bda1f350f18d7516ae685fd6a10094915fa00ae6cd8f3f3151b4bef651d2a5c`, 28,283 bytes, ZIP CRC clean. Independently re-read original `beforeinfo.json` and `original.html`, verified byte lengths and all four per-source manifest SHA256 hashes, and parsed the official 20-row odds matrix to 120 distinct possible ordered triples per race. The ZIP has **no original racelist**.
- [Git first commit touching CLEAN frozen Edogawa9](https://github.com/ikst2512-eng/boat-edge-clean/commit/1a6bdf05927e1209666ef9f9a8c16bbc05bbcaa4) has committer time **10:12:32 JST**; [V2 Edogawa9 first commit](https://github.com/ikst2512-eng/boat-edge-clean/commit/b6f7ba14a7be3f40650f06353f415f2721580c7e) has committer time **10:17:15 JST**. Their repository path histories show one commit each. Git commit date does **not** prove initial *remote* GitHub receipt, so independent first-remote gate remains unverified.
- Same-race main frozen files: `prospective_predictions/202611080309.json`, `four_mode_forecasts/202611080309.json`, `prospective_predictions/202611081409.json`, `four_mode_forecasts/202611081409.json`. The CLEAN records self-describe `input_source_kind=public_pre_race_csv`; V2 says `beforeinfo=optional_not_in_snapshot`.
- Latest observed main when this recheck started: `6b371040fd2fc4398bfa882e6557c333cc0800c8`. Existing Draft PR #1694 was `0cc1ca90def54016382e58f759be8d344e314fbe` and Draft/unmerged before this documentation-only commit.

## Race-matched official source-pair gate (JST, Nov 8)

| Race code / race | Official deadline | T−12 | Beforeinfo receipt and six-boat exhibition | Original 3T odds receipt / unique tickets | Frozen CLEAN; V2 generation | Decision |
|---|---|---|---|---|---|---|
| `202611080309` 江戸川9R | 14:30 | 14:18:00 | 14:15:38.139739; time 6/6, tilt 6/6, ST/course 6/6 | 14:15:48.378360; **120/120** | 10:12:31.149675; 10:17:12.313648 | **Two-original pre-T−12 pass**, **formal reject**: both frozen forecasts predate raw official receipt; missing original racelist, frozen-input linkage, final entry, independent first remote receipt |
| `202611081409` 鳴門9R | 14:34 | 14:22:00 | 14:15:56.709439; time **0/6**, tilt 6/6, ST/course **0/6** | 14:16:07.127274; **120/120** | 10:12:31.149675; 10:17:12.549373 | **Two-original reject**: incomplete six-boat exhibition, plus all Edogawa formal blockers |

Raw per-race beforeinfo/odds SHA256:
- 江戸川: `b52b2e8e400ee00676c247007576abd21be4ed64307e0b2cbafa159c51662db5` / `9ce8d53029bd9022743599de1e7f670439d20efad35f52546d8a99f6347a7aab`.
- 鳴門: `53b269e5641c6a4433fcb7ae1ba4efd2d769d01702f560432164f1d3a1ded8a9` / `a2bfb93817d65b473ffcfeb3408469cc325034ba79c474ef108f4dd75369fcc2`.

Note: These are **the two races contained in this observed official-source archive**, not a claim that every Nov 8 race was exhaustively observed.

## Separate Render odds API transport samples: NOT official-original pairs

The following are independently rechecked ZIP JSON artifacts from `CLEAN live official trifecta odds probe`; it samples the Render `/api/odds` JSON API, **not the immutable official boatrace.jp HTML body**. The probe deadlines originate from public pre-race CSV titles and are **not confirmed official**. Its green HTTP 200 + 120 decoded combinations therefore never closes the official T−12 source chain.

| Run / ZIP digest | Race IDs | Actual outcomes | Formal gate |
|---|---|---|---|
| [14:53 manual run 42452500163](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42452500163), artifact 13605904265 SHA256 `6858fc3ab27b8736b365bc00d6a84c6ebc4d86fda5d37cd5d55ac3571448fd81` | `202611081410`, `202611081111`, `202611081201` | 3 independently replayable HTTP 200 JSON responses with exact 120 unique tickets; the first race first timed out once, then received a valid 200; 4 total attempts | **0**, source deadline not official, no 6/6 official beforeinfo or original racelist linked |
| [16:48 manual run 42460271494](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42460271494), artifact 13609670427 SHA256 `33526c9812904d27cbb46be6b9d21bfb263d2d1d2068e9b45e19314b9c8cfa48` | `202611080105`, `202611081905`, `202611081205` | **6/6 requests TimeoutError** (2 per race, HTTP status null), 0 replayable; run failure | **0**; none treated as 403/404/HTTP 200 or a successful official fetch |
| [17:59 workflow_run 42465246175](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42465246175), artifact 13611128531 SHA256 `a8e9f93dae1879e100c8950e8868639ab91c22c1ca24a0c71dcacb320c9b4713` | none | `source_status=fallback_ineligible`; upstream trigger was `pull_request`, collection step **skipped**; workflow conclusion success | **0**; a green skipped job is not a fetch |

ZIP CRC recheck clean for all three. No observed 403/404 in these selected preserved receipts; absence here is not proof that none occurred elsewhere. Any 403, 404, timeout, partial body, 202 pending or skipped step must fail closed.

## Workflow invocation coverage and prioritization

By around 18:01 JST, GitHub REST `actions/runs?event=schedule&created=2026-11-08` returned **31 schedule-event runs across all workflows**; only **one** belonged to the relevant official pair collector (`research-live-preview-evidence.yml`, 14:15 JST). Declared `*/5 0-12 * * *` corresponds to 09:00–21:55 JST. Nominal 09:00–18:00 inclusive = **109 five-minute slots**, so observed collector schedule creations **1/109 = 0.92%** of slots. This is an invocation-count comparison, **not** proof that 108 HTTP requests failed or exact cron slot matching. GitHub delayed/dropped schedule root cause is unverified. The separately dedicated three-original workflow has only `workflow_dispatch` and `pull_request` triggers; no automatic same-race trio observation is established for Nov 8.

Priority, by impact on **formal T−12** rather than green job count:

1. **Structural zero:** no complete same-race official original racelist + beforeinfo 6/6 + original 120 odds, with a new frozen prediction generated *strictly after* all official receipts and before T−12. Existing 10:12/10:17 forecasts cannot be relabelled or backfilled. Collection/forecast lineage remediation: **owner ①**.
2. **Near-total scheduled sample scarcity:** one observed official-pair scheduled activation against 109 nominal slots at this cutoff; prove actual workflow triggering and missed slots before adjusting any cron. **Owner ①**, avoid duplicate schedule/workflow changes.
3. **Operational source quality:** incomplete Naruto exhibition and independent Render odds timeouts. Do not merge Render/UI failures with official boatrace.jp failures without shared-origin evidence. Source collection diagnostics **owner ①**; Render/UI **their separate owner**.
4. **Unproven initial remote persistence:** Git first-add commit timestamps are useful but insufficient independent first GitHub remote acceptance. Add audit-only externally observed receipt and source hash lineage to any future prospectively frozen candidate, **without changing old files**.
5. **Certification gate:** only after all previous conditions and official final entry are demonstrated, verify race/code, original SHA, timestamps and first-add on independently saved source; if any fail, output `formal=false`, `t12_eligible=false`, `accuracy_scoring_allowed=false`.

**Observed results from official pair ZIP:** 2 paired races examined; 1 strictly complete two-original pre-T−12, 1 incomplete exhibition, **0 complete three-original certified forecasts**, and formal accuracy denominator **undefined**. No production path, model, collector, main, historical record or auto-merge setting changed. Draft manual review only.

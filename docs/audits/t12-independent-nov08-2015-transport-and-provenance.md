# 2026-11-08 ~20:14 JST — T−12 source-vs-forecast provenance audit (independent, nonformal)

**Scope:** Follow-up to [18:01 race-level audit](t12-independent-nov08-1800-recheck.md), from real GitHub Actions run logs, saved ZIP bytes and frozen main prediction files. This is audit-only evidence on Draft PR #1694, not a live collector change or a formal accuracy cohort.

## Newly observed runs (all timestamps JST)

| Race code | Source and receipt / diagnostic evidence | 12-minute deadline status | Why it cannot be certified |
|---|---|---|---|
| `202611081210` (住之江10R) | [official-odds **Render API** probe #42472229918](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42472229918) 19:37–19:40: **two TimeoutError**, `http=null`; CSV-derived deadline 19:47 | Nonofficial **CSV** T−12=19:35, already elapsed at scheduled probe start | No valid API odds, let alone original official 120-way HTML / beforeinfo 6/6 / original racelist |
| `202611080111` (桐生11R) | Same probe: **two TimeoutError**; CSV-derived deadline 19:58. [Local racecard diagnostic #42472882460](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42472882460) found CSV six-lane preview at 19:47:17, Render preview timed out | Nonofficial CSV T−12=19:46; 19:47 CSV preview was **after** cutoff | Source families differ and no official 3-original evidence |
| `202611081911` (下関11R) | Same odds probe **two TimeoutError**; CSV-derived deadline 20:07; 19:47:30 local CSV six-lane preview from [diagnostic #42472882460](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42472882460), Render timed out. [T12 research seed #42472909936](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42472909936) reported 1 newly stored **research-only** baseline and `independent_first_seen_verified=false` | Nonofficial CSV T−12=19:55; 19:47 CSV preview ~7m30s early, but not original official beforeinfo | No official beforeinfo SHA/6-boat raw + original 120 HTML + racelist, no input linkage or independently proven first remote save. Main CLEAN/V2 forecast generated ~10:12/10:17 and says public CSV / optional beforeinfo |
| `202611081211` (住之江11R) | [scheduled CSV preview probe #42474841935](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42474841935), at 20:14:17 three CSV sources `tkz`, `stt`, `sui` (129 rows each), adapter printed `VERIFIED_SIX_LANE`; no original official boatrace.jp trio captured by this workflow | Nonofficial CSV deadline 20:16 and T−12=**20:04**; observation **10m17s late for T−12**, although 1m43s before race deadline | Valid **predeadline CSV** evidence is **not** valid *T−12 official* evidence. Morning frozen CLEAN at 10:12 is `public_pre_race_csv` not these later bytes |

**Important distinction:** `SCHEDULED_PREVIEW_VERIFIED=1` / `VERIFIED_SIX_LANE` from #42474841935 refers to **BoatraceCSV** predeadline adapter, not to official boatrace.jp beforeinfo. `RACECARD_OK` from #42472882460 shows six racer names and separate preview status, not archived official 3-source proof. Never promote either to the formal count.

## New operational failure independently replayed

[Run 42472229918](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42472229918), job `128705480220`, saved artifact `13614595043` (ZIP **3,095 bytes**, SHA256 **`df2a3e63dd36c78b67e6c4f02c01fe1ac74af3f0fb127023085dd70accc3cdb2`**, matches GitHub-advertised digest, ZIP CRC clean). Original `live_odds_metrics.json` was re-read directly:

- `202611081210`: 2 × `transport_error:TimeoutError`, HTTP null
- `202611080111`: 2 × `transport_error:TimeoutError`, HTTP null
- `202611081911`: 2 × `transport_error:TimeoutError`, HTTP null
- Overall: **6 attempts, 0 HTTP 200, 0 replayable 120-way odds**, operational verdict `no_valid_200`; scheduled job **failure** as expected.
- `source_status=ok` belongs to the **CSV race schedule provider**. It does **not** mean the official boatrace.jp odds HTML or Render API succeeded. These API timeouts are separate from official-source HTTP 403/404 (not observed in this specific ZIP).

This is separate from [16:48 manual odds timeout](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42460271494), also 3 sampled races × 2 timeouts, and does not invalidate the independently confirmed [14:15 original boatrace.jp Edogawa9 two-source pair](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42450048245).

## Collector schedule and formal decisions

At the snapshot, GitHub returned **41 total repository `schedule` events** created on UTC November 8, but only **1** `research-live-preview-evidence.yml` scheduled official-pair collector invocation (#42450048245 at 14:15 JST). Configured collector frequency `*/5 0-12 * * *` gives **135 elapsed nominal JST slots (09:00–20:10 inclusive)**; this is **1/135 ≈ 0.74% observed invocation count**, not proof 134 HTTP failures or exact slot identity. **No new scheduled pair archive or dispatch of the dedicated official-three-original workflow was observed** in this bounded inventory.

Formal three-source+post-receipt forecast+first Git remote acceptance **0**; formal hit-rate denominator **undefined**. Research 6/6 and local baseline counts are kept distinct.

**Immediate handoff to collector owner ①:** Investigate actual activation deficit first; preserve the same race official `racelist.html` + `beforeinfo.json` + `odds3t original.html` with HTTP 200, 6/6 exhibition/entry data, 120 unique combinations, endpoint/race ID/hash/receipt timestamp. A new frozen prediction must be generated *strictly after* the verified last official source receipt and before official T−12, then independently attest the first Git remote acceptance and final entry. Keep Render transport triage in its assigned lane; do not equate its errors with official upstream failures.

**Audit gate improvement:** Draft-only `scripts/audit_t12_frozen_chronology.py` now identifies `input_source_kind=public_pre_race_csv` explicitly in `missing_requirements`, in addition to the existing official-original source-linkage rejection. It never grants `formal`, `t12_eligible` or scoring eligibility.

No production collectors, cron, main, Render, immutable race predictions or automatic merging were changed.

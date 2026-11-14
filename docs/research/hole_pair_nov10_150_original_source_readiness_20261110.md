# 2026-11-10: real 150-source immutable Git byte inspection for hole-pair ⑤

**Status: Draft #1685 ONLY, independently verified original Git bytes but NONFORMAL.** No source collector/production changes, no main merge, no gateway dispatch, no official-result reads, no D1 or Cloudflare deployment. This report is about the source inputs potentially fed to a future research candidate freezer, NOT actual accepted hole-mode candidate receipts.

## Evidence and exact reproducible inputs

- Exact public main commit: `c4d39245cbc96b6c680585a68c3b9adf6ddeb921`, recorded at 2026-11-10 16:08:32 JST. Its original `four_mode_forecasts/` tree is `f8765fdbd105c3673cde76fe9df80f10b0ad1269`.
- Reference time: **2026-11-10 16:33:00 JST**. This is a *fixed comparison time*, not a receiver/server observed timestamp. Deadlines are source-record **declared** deadline values, not independently authenticated official BOAT RACE deadlines.
- `research/hole_pair_real_main_snapshot_gate.py` parses the exact Git tree, **reuses existing** `parse_tree` from the prior source SHA1 drift audit, opens every source Git blob through `git cat-file blob`, independently recomputes Git blob SHA1 with size header and per-source raw SHA256, validates canonical race ID and the pinned CLEAN four-mode source schema, checks beforeinfo field and compares recorded generation with declared T−12. It does **not** inspect any actual winners, odds, official source ZIPs, candidate frozen manifest, or write to main.
- `research/test_hole_pair_real_main_snapshot_gate.py`: **11 adversarial synthetic tests**, including forged blob identity, different race IDs, mixed/invalid timezones and dates, wrong model/source schema, symlinks or non-forecast Git paths, duplicate tree paths, oversized byte contents, and attempts to convert a populated beforeinfo field into verified official evidence. These tests are not additions to eligible study races.
- The **existing PR-only** research workflow runs the unit tests, fetches that immutable exact commit SHA (not changing main), executes the full 150 original-source analysis, checks the actual count and fail-closed flags, and uploads a separate JSON with **150 per-race original Git blob SHA1, calculated SHA256 and source timing classifications**. Artifact retention **30 days**, so this is not an independent long-term archive.

[Exact code-head CI #42782168914](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42782168914), commit `2e50fb571824fbb60d449f0241c9c81a7178d7e5`, **SUCCESS**. New 11/11 synthetic tests succeeded; **actual** 150-source Git-byte replay and JSON artifact upload succeeded; normal candidate-freeze step and candidate ZIP upload were **SKIPPED**. Artifact: `hole-pair-actual-nov10-main-source-audit-nonformal`, ID **13746766282**. This output is a *real* Git-original replay, not synthetic 150 rows.

## Actual numeric results, not inferred from counts or synthetic samples

| Metric (same original pinned Git snapshot) | Observed |
| --- | ---: |
| `20261110*.json` forecast original race files | **150** |
| Original raw Git blob SHA1 independently recomputed and matched | **150 / 150** |
| Original source SHA256 computed from verified bytes | **150 / 150** |
| `beforeinfo == "optional_not_in_snapshot"` in original forecast | **150 / 150** |
| Other `beforeinfo` in original forecast (not independently certified even if present) | 0 |
| File-declared model generation earlier than file-declared T−12 | **150 / 150** |
| File-declared T−12 already elapsed by 16:33 JST | **125** |
| File-declared T−12 still in future at 16:33 JST | **25** |
| Official six-boat beforeinfo / 120-way original data authenticated by this audit | **0** |
| Independent first signed hole candidate receipt authenticated by this audit | **0** |
| Formal pilot admitted | **0/300** |
| Untouched confirmation admitted | **0/300** |

**Interpretation:** A 150/150 early *local model generation* result does not prove official exhibition sources had been acquired first, that source content was included in model inputs, that a new candidate was created after official source receipt, or that an independent server accepted that candidate before genuine T−12. All 150 originals explicitly say `beforeinfo=optional_not_in_snapshot`; this is **absence of beforeinfo within those 150 forecast JSONs**, not a negative search result across all official archives. The 25 T−12-open at reference are simply **25 theoretical time windows**, not 25 previously frozen/received candidates. No after-the-fact freezing is valid.

The original `four_mode_forecasts` snapshot is also not an independently certified official complete race-day universe. A source JSON's declared deadline is not a verified official cutoff. The four locked hole-pair research source-code Git blob hashes remained unchanged in main as independently checked in the previous source census.

## Effect on blocker priority

1. **Highest blocker — real independent first-acceptance path:** #1702 is still a Draft, not installed in main; its manual workflow has no D1 transport nor independently pinned signing-key custody. #1685's receipt SQL/Ed25519 verifier are offline-only. Until a separately approved, independently controlled append-only receiver accepts original future candidate bytes and proves first acceptance, **no signed eligibility** can be claimed.
2. **Official source dependency belongs to #1694:** six genuine beforeinfo/exhibition boat rows, complete **120 distinct** odds, same-race racelist and official cutoff; independent original-source arrival before T−12 and generation after all required official originals. This cannot be filled by a beforeinfo JSON field, a CSV preview or a local generation timestamp.
3. **Complete-day and longitudinal holdout:** a one-per-day manual snapshot of 150 source race IDs is not the whole official day. Need first-write deduplication and explicit missingness/repeated windows before pilot 300 then confirmation 300. The 125 past cutoffs at 16:33 cannot be made prospectively eligible by backdating.

**Decision: HOLD.** No production model/Top1/3/5/10/UI or main change, no automatic merge, no candidate dispatch, no Cloudflare deployment. Method SHA, original comparisons and historical sample records remain unchanged. Formal accuracy uplift remains **unmeasured**.

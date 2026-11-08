# 2026-11-08 20:59 JST — independent same-day T−12 blocker reconciliation

**Read-only research audit, Draft PR #1694 only.** No main, collector, UI, Render, forecasts, cron or historical evidence modified; formal T−12 scoring remains disabled.

## Correction of an audit-cohort mismatch

The previous audit-only PR workflow combined a schedule audit for **UTC Nov 7** with official-three-original durable Git branch presence for **JST Nov 8**. Their independent observations were each useful, but **their numerical deficits cannot be treated as a single-day collection-and-persistence cohort**. The previous Nov 7 schedule CI reading `1.28%` is **not** the observed Nov 8 scheduled invocation rate.

The corrected workflow now queries **UTC Nov 8** for the collector whose `*/5 0-12 * * *` UTC cron equals **09:00–21:55 JST on Nov 8**, queries **Nov 8 JST** for `research-t12-external-evidence` at a fixed immutable Git SHA, and runs `scripts/audit_t12_blocker_join.py` to explicitly fail if days, schemas, counts, completed/partial clock slots, directory status or truth-valued certificate flags disagree.

## Exact GitHub CI evidence

[Audit-only run #42478094964](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42478094964) on code head `5fc92be9c04ca0ce6b9ca80762988d6efd36a2aa`, completed **success**, **68/68 tests**:

- collector schedule inventory regression 12/12;
- official paired-original vs frozen prediction chronology 20/20;
- three original + frozen SHA/chronology diagnostic 16/16;
- immutable Git branch day presence inventory 10/10;
- strict same-day blocker join 10/10.

Observed timestamp `2026-11-08T11:58:59.931657+00:00` (20:58:59 JST):

| Same-day audit scope | Observed | Interpretation |
|---|---:|---|
| Intended nominal 5-minute official-pair cron slots through 20:55 JST | 144 | `00:00..11:55 UTC` inclusive (12 slots/h; last 12 remain future) |
| Official-pair `event=schedule` run creations | **1** | [run #42450048245](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42450048245) at 14:15 JST |
| In-cron-hours invocation ratio | **1/144 = 0.69%** | **143 count shortfall; not 143 proved HTTP failures or precisely attributed missed triggers** |
| Total all-workflow Nov 8 schedule events in GitHub API query | **44** | Different workflows must not be counted as the official pair collector |
| Persisted three-original Nov 8 race directories on `research-t12-external-evidence` | **0** | Parent contains `20261103` only, pinned evidence commit `d0ed89f146dff117021c2bc042b20259d6715515` |
| Official triple / frozen model consumption / independent first Git remote receipt | **unproven** | Metadata cannot substitute for verified original replay and prospective model input |
| New formal T−12 certificates supplied by this audit | **0** | Formal accuracy denominator remains undefined |

The archive status `no_persisted_three_original_day_directory` is scoped to this Git branch. This is **not** a claim that no separate research Actions ZIP exists: the earlier Edogawa 9R two-source archived original remains validated with 120/120 official trifecta odds but without an official racelist original and without a newer post-receipt frozen model.

## Owner-specific operational handoff

**Owner ① / collector:** First establish actual intended cron activations and error-free official three-source collection on each same race. The absence of scheduled events is not evidence of official HTTP 403/404; inspect GitHub schedule health and actual collector invocations separately. Preserve official racelist original, beforeinfo 6/6, odds3t original HTML and 120/120 unique odds with individual receipt timestamps, URLs and SHA256s, before official T−12; then persist the immutable complete original set in the dedicated Git evidence channel.

**Source-input/model owner ①:** Generate *new* forecast only after the final official original receipt and before official T−12. Independently replay inputs actually consumed by the model; a forecast's self-declared `official_original_sha256` equality is insufficient. Do not rewrite or re-certify frozen morning CSV forecasts.

**Independent auditor:** Re-audit all three raw originals from their exact remote Git blob and commit; independently attest model input consumption, initial GitHub remote acceptance time, and final entry. Until every gate succeeds, output `formal=false`, `t12_eligible=false`, `forecast_usable=false`, `accuracy_scoring_allowed=false`.

This change fixes the audit's **measurement comparability**. It does **not** itself increase real source capture or formal certifications. The continued bottleneck is missing archived official three-original candidates, followed by actual official-input and first-remote chronology.

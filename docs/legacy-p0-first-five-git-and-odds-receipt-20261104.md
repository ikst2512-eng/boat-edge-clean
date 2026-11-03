# Five-race P0 first Git-add and odds chronology receipt — 2026-11-04 JST

Read-only expansion from single race to the earliest five P0 legacy-only prediction race IDs from the pinned 2026-11-03 audit crosswalk. No source originals, live site, scoring, CI or workflows changed.

Legacy pinned tree SHA: `f38204105a979aa6ef5293d1b9cad854056faadd`. All five source JSON snapshots were refetched **at the identified Git-add commit**. Each commit's diff shows `data/site_prediction_snapshots/{race}.json` as a new file (`@@ -0,0`) and its blob SHA equals the indexed snapshot SHA at the pinned later tree.

| Race | Git-add commit | Git commit timestamp UTC | Snapshot blob SHA1 | Self-reported lead before cutoff | Observed odds sidecar |
| --- | --- | --- | --- | ---: | --- |
| `202610080103` | `1d06d01b5cae217f137e71a5a69e92c9ef7fb208` | 07:15:40 | `4758d57a765ee06c56a8f85680b7d600728677ca` | 6.33m | 404 at pinned tree; snapshot odds SHA256 null |
| `202610080104` | `0c631f193f0829f10625161a5b8e016cbfe12b96` | 07:36:49 | `93ff785f5039b0cb6ec616a01ef7480306233ac5` | 11.19m | file has 120 entries; fetched at 16:40:14 JST, **after forecast ~16:36:49 JST**; snapshot odds SHA256 null |
| `202610080105` | `f732faed17b72233240a22e63778521b79500cb7` | 08:06:42 | `e3fb2dd28f07b64511464e9b04fcae0fccc368bb` | 10.3m | file has 120 entries; fetched at 16:40:22 JST, before forecast ~17:06:42 JST; hash link not yet verified |
| `202610080106` | `eecc374eff6b965ad5cdcca21eba5976c0444a73` | 08:46:51 | `bfe4348f8de76d9a74ac83e07cd446e3c9b36cf1` | 1.16m | file has 120 entries; fetched at 17:44:34 JST, before forecast ~17:46:51 JST; hash link not yet verified |
| `202610080107` | `a36371ce87d823107171fcee690491e0798daf74` | 09:01:49 | `e0fa8f601ac33fba6c1b184a65a49f5a83f50a5f` | 15.18m | file has 120 entries; fetched at 17:44:44 JST, before forecast ~18:01:49 JST; hash link not yet verified |

**Interpretation:** These Git-add records support the historical source's presence as of the listed commits, NOT independently verified wall-clock delivery or formal forecast eligibility. The source's own declared lead times of 11.19, 10.3, 1.16 and 15.18 minutes should not be mistaken for a passed strict V229 2–10-minute window. Two are outside by a wide margin, and 10.3/11.19 exceed the upper limit. The legacy evaluation records declare `SITE_REFERENCE_POST_SETTLEMENT_ONLY_NOT_FORMAL_FRESH` for all four newly checked races. No formal Fresh promotion.

An odds JSON file with 120 keys is NOT a verified 120-odds predeadline market in the frozen model's receipt without: a same-race timestamp, source validity, original-source SHA match, unique ticket/value validation, and cutoff. In particular the **4R sidecar postdates the frozen forecast** and must not be used retroactively. 5R/6R/7R sidecars preceded forecast creation based on embedded timestamps, but source hash match is unverified. Source time and Git commit time have different trust levels.

Local handoff CSV: `boat_edge_first_git_proof_5r_20261104.csv`, SHA256 `6b6190c5574d2f50815e02051dba2d1081b9123aeceebef729cce25d536e805b`. It is NOT a backup of the original JSON bytes. No independent durable raw-byte archive / restore has been verified.

**Decision: DELETE_BLOCKED / LEGACY_WRITER_STOP_BLOCKED.**

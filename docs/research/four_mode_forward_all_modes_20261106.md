# 四モード横断・将来時系列検証（2026-11-06登録）

## 目的と固定母集団
- 2026-11-05のV2保存原本106件と独立確定結果106件は、仮説の発見用の**参考データ**。正式認定0件。ここで当たるように調整した候補を11月5日自身で成功判定しない。
- 同一106件の保存順Top1/3/5/10（順に件数）: 絞り **4/21/33/33**、本命 **4/21/33/53**、バランス **4/23/32/52**、穴 **2/6/9/16**。分母はどれも106で、絞りは5点なのでTop10=Top5。
- 全保存買い目内の `covered / 1着頭欠落 / 1-2着組欠落 / 3着欠落` は、絞り **33/39/24/10**、本命 **53/33/12/8**、バランス **63/15/20/8**、穴 **22/6/43/35**。これは**構成診断**で、レースの風・展示・STが原因だとは未証明。
- 検証元は #1678 の main `1a6612f9...` 対照と Actions [#42058585888](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42058585888)。穴用シャドウ研究 #1688/#1685、場別環境研究 #1692 とデータ・変更ファイルを共有せず、再計算した「本番予想」を作らない。

## 別期間での検証ルール
- 本ファイルと `research/four_mode_all_modes_forward_protocol_20261106.json` を**未来のレースが確定する前**に登録。適格候補は2026-11-07以降・V2の**同一バージョン**だけ。モデルバージョンが変われば別評価群。候補選定コード/重みのSHA256を候補初回生成前に固定。未固定のままの日付は実験へさかのぼって組み込まない。
- 同一レースの4モードすべてについて、元の凍結予想と候補を**結果参照より先に**同一レース・同一点数で保存。絞り5、本命10、バランス16、穴22。Top1/3/5/10を保存順位で判定し、全リスト内的中と混同しない。
- レースの締切とレースコードが一致する公式beforeinfo、展示6艇、120通りオッズ、入力受信→予想計算→Git初回追加→**独立した遠隔初回受領**の順序を照合。T−12前の同一秒タイムスタンプは順序不明として**未認定**。GitHub server-Dateで既存原本を「観測した」だけでは初回受領を証明しない。
- 受領・生成の時系列や候補4モードの一つが欠ける場合、成功にも不的中にも含めず、棄却理由と母集団の抜けを残す。結果が未取得なら**pending**にして、後から有利な新規レースで置換しない。収集runの全数監査が完成するまで正式分母0のまま。
- 順序は締切時刻→12桁レースID。あらかじめ適格になった最初の300件をpilot、続く300件をconfirmationとして固定。欠損を新しいレースで補充しない。評価途中の選択法変更、都合のよい期間での早期停止は禁止。confirmationが300件に満たない場合、改善実証は**未完了**。
- 主要評価は4モードのTop10 3連単**同一レース差分**。4検定にHolm法（両側・familywise α=0.05）を適用。Top1/3/5の劣化、失った的中、偏り、レース場別・風帯別のカバー率、同一確率の校正、オッズ独立性も監査。統計的有意差だけで実運用の改善を保証しない。
- 現時点で候補4モードのSHA固定、個別T−12原本、独立遠隔初回受領、先に固定した600件の母集団は**未証明**。したがって`formal=false`、`prospective_improvement_proven=false`、`model_promotion_allowed=false`。

## 24場研究の安全な使い方
- #1692で整理した2026-08-01〜10-31の公式実コース1着率は、場による事前差を見る資料。例えば平和島1コース42.4%、戸田43.1%、下関62.9%、芦屋63.2%。これは過去の場平均であり当日の艇・実進入の勝率ではない。
- 風速0–2m/3–4m/5m+、向かい・追い・横、波高、潮・季節、展示タイム（福岡は計測範囲差）、2コース壁、実進入の候補特徴を**入力原本時刻・場別定義付き**で試験する。事後結果CSVの風を予想入力へ流用しない。観測できない特徴を0扱いしない。測定条件・母数が異なる旧風差ptを一律確率補正に使用しない。
- Geminiは独立証拠として扱わない。助言採用は人間が出典・漏洩・再現テストを確認した後のみ。過去のAI監査では `GEMINI_API_KEY_not_configured` により分析が無効だった事例があり、今回もGemini API分析成功は確認していない。

## 成果と保護
本Draftは未来検証の**判定方法を事前固定する研究作業**であり、未来の新規レースに対する改善証明ではない。既存 #1678/#1685/#1688/#1692 と重複する予想生成、風係数の実装、収集、T−12判定、UI、Render、CIスケジュールの変更はしない。採用は将来の実測・CI・個別原本監査・手動審査後に限る。自動統合は禁止。


## 2026-11-06 続き：同一ジョブ4モード候補凍結・結果後照合の研究実装

- **Draft PR #1693でのみ**、結果を読まない決定的な4モード候補生成器（`four_mode_all_mode_same_job_shadow.py`）を追加。V2原本が現行モデルから**完全再現可能**なことを検査してから、元の点数「絞り5 / 本命10 / バランス16 / 穴22」を維持して候補を生成。確率の校正済みを主張せず、全国勝率のみを使う**研究用ペア分散仮説**（既存PR #1692の風・展示補正係数はまだ投入していない）。
- 実装は元予想Top1を全モードで保護。本命・バランスは元Top3、穴は元Top5を保護する。絞りは元Top1を保護しTop3/5の候補を実験的に変更可能。**的中率が上がる保証は一切ない**。#1685/#1688の穴専用規則はコピー・変更せず独立研究として維持。
- 既存の4モード収集ワークフローに、GitHubで**元予想原本**を観測した後に実行する研究用の任意ステップを追加。新cron・別の収集経路なし。研究成果物は `four-mode-evidence/all-mode-shadow.json` に限定。T−12境界、元原本SHA256、ローカル候補終了時刻、GitHub原本観測の時系列を保存。公式6艇beforeinfo/オッズ120組と**候補自体の初回遠隔受領**は未確認（false固定）。ステップ失敗は独立ステータスに残し、元予想のGit pushは止めない。
- 保存候補と別保存結果を結果後に照合する `four_mode_all_shadow_reference_review.py` を追加。入力候補の事前凍結SHA・時刻・点数と再生成一致を**すべて検証してから**結果ファイルを読む。欠損はpending、結果不正はinvalid、失ったTopN的中も記録。正式採点へ変換する機能はない。
- 実原本106件の**結果を読まない入力適合性試験**では `20261105` の106/106件すべてV2モデルから再現、拒否0。各モード候補は106/106件で買い目に変更があり、Top1は全モード変更0。本命・バランスのTop3変更0、穴Top3/5変更0、絞りTop3変更106件。ただし**買い目が変わったことと的中率が向上したことは全く別**であり、この106件を将来holdoutに流用しない。
- 最初の新規比較対象は依然 `2026-11-07` 以降。正式認定0、将来候補のremote first receiptは未実証、独立した収集run全数確認も未完了。**main未反映**なので定期実行されたとは報告しない。2026-11-06時点で将来実測数値はゼロ、候補の本番採用は不可。
- CI: [既存4モードcaptureのPRテスト #42075854969](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42075854969) **success**（PRイベントのcapture本体は**skip**）、[4モード研究CI #42075854928](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42075854928) **success**。将来の実運用・正式認定の成功を示すものではない。

次に必要なのは、元原本と候補の真の受領証拠の保存、個々の公式T−12完全原本と候補SHAの外部観測の突合、**事前固定した別期間**の実レースで同一レース比較を成立させること。研究PRの本番統合・無人収集への接続は審査後の判断。


## 2026-11-06 03時台以降：候補の長期保存とGitHub候補原本観測

- 研究PRだけに `four_mode_all_shadow_durable_ledger.py` を追加。既存の `v2-third-rate-evidence-ledger` ブランチを共用し、新しいcron・GitHubブランチ・外部保存サービスを増やさない。PRイベントでは**本番captureはskip**。現行main、Render、予想モデル、公開買い目は変更しない。
- 親ファイル `four-mode-evidence/all-mode-shadow.json` を結果閲覧より前に検証して、`four_mode_all/YYYYMMDD/run-ID-attempt-N.json` として**追記専用**で保存する設計。重複保存なら原文完全一致、異なれば競合エラーで拒否。対象runが追加した全予想コード、元原本のfirst-add Git commit/blob、ローカル候補SHA、4モード全点数、締切時刻を整合確認。
- 保存済み候補をGitHub APIから**原文バイト列・Git blob SHA・GitHubサーバーDate**で読戻し、T−12より前か（同一秒の曖昧性を含めて）区別する。観測報告も別の `four_mode_all_observation/YYYYMMDD/run-ID-attempt-N.json` に追記専用で保存。従来の30日Actions artifactだけに依存しない。ただし**GitHub Dateは初回遠隔受領時刻ではなく読取り観測時刻**。候補の真正なfirst remote receiptと独立出走表・展示・オッズの公式T−12整合が証明されない限り `formal=false`。
- [CI #42089031046](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42089031046) 研究側成功、[CI #42089031024](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42089031024) capture既存179テスト成功（本番収集stepはskip）。新たな耐障害・改ざん・日付判定テスト9件が成功。追加途中に発生した「保存ファイルが1個から2個に増えたことに対する旧テスト断言」の失敗はテストを修正して最終CI合格とした。
- 次は手動コード審査で実際の保存・時刻証拠を点検。**Draftのままで、実運用で候補がGitHubへ長期保存されたことを現時点では主張しない。** 2026-11-07以降の候補・結果の前向き比較は依然0件で未開始。

## 2026-11-08 Top1-only pair-order shadow (separate from the existing diversity candidate)

- **Research-only and result-blind.** The saved V2 original, the original diversity candidate, and the production forecast are unchanged. Each mode now has an **additional** `top1_pair_candidate` preserved in the same frozen capture. The rule uses only the six **original saved pre-result national win rates**. Compare the original 1st and 2nd tickets' win rates lexicographically in finishing-position order (1st boat, then 2nd boat, then 3rd boat). Put the stronger of these two already-present tickets first; ties retain original order. This rule is a hypothesis, **not a validated ranking or recalibrated probability**.
- Frozen policy identifier `pre_result_national_win_rates_lexicographic_head_second_third_v1`; per-capture `top1_selector_sha256` is pinned to the committed shadow generator. Tampering, selector drift, fabricated receipt and late cutoff cause rejection before any result is read.
- **Top2 ticket set unchanged; Top3, Top5 and Top10 memberships unchanged in all four modes by construction.** Only the position of the first two tickets can change. This is isolated from the existing candidate's separate Top10-diversity hypothesis and cannot change overall ticket coverage. A change of Top1 does **not** mean a winning prediction. If the two tickets start with the same head (often `1-2-4` and `1-2-3`), head coverage is also unchanged.
- The result-last independent reviewer now emits `top1_pair_by_phase`, reporting same-race original / paired-rank Top1 successes, newly gained and lost successes, and the fixed denominator. Pending or untrusted outcomes are excluded and remain visible. A fabricated or missing `top1_pair_candidate` is rejected before result file access.
- **No retrospective certification.** The observed Nov 5–7 results motivated the question. None of those historical races, or any race whose candidate was first computed after the result, can prove this new Top1 method. Historical input replays are *only* result-blind compatibility and change-exposure checks, never hit-rate evidence.
- The existing registered Top10-primary 300-pilot + 300-confirmation comparison is **not rewritten after results**. The Top1 pair policy is separately exploratory until a prospective pre-result frozen first-remote-receipt cohort and an explicitly preregistered, multiplicity-controlled Top1 confirmation test are available. No first remote receipt, no verified six-boat official T−12 feed, no verified official odds 120, no complete capture-run inventory and no model-promotion approval are claimed. Draft stays Draft; manual review, no auto-merge.

## 2026-11-08 follow-up: standalone Nov9+ Top1 result-last gate (no main merge)

- The earlier four-mode **Top10** prospective protocol is untouched. A separate Top1 protocol now uses **2026-11-09 00:00:00 JST through 2026-12-31 23:59:59 JST**, because the candidate was authored on Nov 8 and any Nov 8 race might straddle registration. Nov 5–8 remain discovery/input-compatibility material and **cannot be prospective Top1 successes**, even if results exist and the new selector can be replayed afterward.
- `four_mode_top1_forward_reference.py` validates the entire supplied original/shadow capture set **before** opening any result, locks the first 300 pilot and next 300 confirmation slots by deadline then race code, rejects **ineligible future frozen rows** rather than opportunistically backfilling, and keeps absent/invalid results pending or invalid, never lost tickets. It independently checks the existing Top2/3/5/10 ticket memberships are preserved and reports Top1 original, candidate, gained, lost and denominator per mode/phase.
- This new reference scorer is intentionally **incapable** of declaring a certified or promotable improvement. It does not assert that its caller supplied a complete Actions run inventory; it has **no independent first remote receipt of the candidate** and lacks official six-boat/120-odds pre-T−12 proof. `formal=false`, `model_improvement_proven=false`, `model_promotion_allowed=false` are unconditional. PR CI is a **research-only** dry run, not a live collection.
- Tests in `test_four_mode_top1_forward_reference.py` cover Nov 7 and Nov 8 exclusion despite confirmed files, Nov 9 pending reservation, both gained and lost Top1, invalid early outcome, missing candidate provenance, and refusal to replace an ineligible frozen slot.
- The immutable ledger on `v2-third-rate-evidence-ledger` had **no `four_mode_all/` directory when inspected Nov 8**; consequently there is no independently frozen Top1 candidate artifact from this Draft's main-branch scheduled job. After explicit manual review, a separately authorized main integration would be needed to begin its real live shadow collection; no automatic merge, no Render changes.

## 2026-11-08 follow-up: run-inventory guard and actual scheduled-run observation

- New `four_mode_top1_capture_run_inventory.py` is an **optional read-only** metadata inventory from GitHub Actions for a **single UTC day**, with `--fetch --utc-day YYYY-MM-DD`. It inspects both `schedule` and `workflow_dispatch` using `GET /actions/runs`, validates every response page against `total_count`, detects duplicate run IDs, missing/truncated pages, cross-date records, name/path drift and rerun attempts. It **does not** prove schedule triggers that never created a run, nor complete job attempts or the candidate's first receipt. It never marks formal evidence true.
- The CI runs local positive/negative fixtures only; it does **not** perform network inventory collection, start a Cron or write any GitHub data. `test_four_mode_top1_capture_run_inventory.py` rejects missing API event pages, truncated pages, wrong clocks and workflow identity, duplicate IDs, and unstable page counts. A live inventory for future eligible days must be collected by an explicitly reviewed read-only process and independently reconciled to the actual scheduled timetable.
- Real GitHub read-only observations on Nov 8: UTC calendar-day `created=2026-11-08` (incomplete while that UTC day is still open) showed the two main scheduled `Four-mode prospective capture (research only)` runs **#42433577233** and **#42438243366**. The former was at **2026-11-08 10:17 JST**, added 116 immutable forecast archives in first-add commit `b6f7ba14a7be3f40650f06353f415f2721580c7e`, and reported 116 early original server observations, **not independent first receipt**. The latter at **11:22 JST** reported `no_eligible_candidates` and added 0. Both capture jobs passed, but they did **not** include the new all-mode Top1 candidate step because Draft #1693 remains unmerged.
- The shared `v2-third-rate-evidence-ledger` branch had **no `four_mode_all/` path**, and the existing main remains separate. This is an actual negative availability check for the new shadow, not a finding that the original source collection failed.
- For Nov 9+ Top1: still **0 certified same-race pairs**, **0 independent candidate first-receipts**, and **0 formal improvements**. Existing #1692 environment research, hole research, live UI and Render are unchanged. Draft review and manual merge decision remain mandatory.

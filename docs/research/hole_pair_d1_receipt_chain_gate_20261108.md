# 穴モード研究：D1受領時刻と候補原本の整合性検査（2026-11-08 JST）

**Status: Draft PR #1685 / research only / NOT deployed / nonformal.** この監査はサーバー受領メッセージの**申告内容の内部整合性**だけを検査する。D1の実配備、実際の受領の成立、候補の独立初回受領、公式T−12完全性、正式的中率の認定、統計的改善は一切主張しない。

## 新しく追加したもの

- `research/hole_pair_d1_receipt_chain_audit.py`: 既存の `hole_pair_remote_receipt_evidence._validate_frozen` を再利用し、2026-11-09以降の3方式10点ずつの固定候補、SHA-256、Top5不変、元1・2着ペア保護を事前確認する。受領メッセージのレースID、候補**全原文**のSHA-256、申告したT−12、受領日時、発信側が明示する `formal=false` などを照合する。
- `research/test_hole_pair_d1_receipt_chain_audit.py`: 10件のfail-closedテスト。偽の正式認定、独立性主張、受領記録と候補の紐付け違反、後追い/同秒受領、タイムゾーン不正、重複候補、別レース証拠流用、受領記録欠落を扱う。
- `.github/workflows/hole-future-pair-precommit.yml`: PRの読取専用CIで追加テストを走らせる。候補固定・候補ZIPアップロードは従来どおり `workflow_dispatch` 時のみで、PR CIでは**スキップ**。

## 意味の違う5種類の「証拠」を絶対に混同しない

| データ | この監査が認めること | この監査が認めないこと |
|---|---|---|
| 候補のSHA-256とローカル生成時刻 | 候補文字列の一致・申告時系列 | 元予想の真の初回取得、結果前に独立した初回受領 |
| D1に由来すると申告されたJSON | 記載されたレースID、ハッシュ、時刻が矛盾しない | JSONの外部真正性、管理者耐改ざん性、署名付き初回受領 |
| 申告 `first_received_at_utc` | T−12前・候補計算後という時刻の形式上の整合性 | GitHub/Cloudflareがその実時刻に初めて受信した証明 |
| 申告 `t_minus_12_jst` | `deadline_jst - 12分` と矛盾しないこと | その締切自体が公式時刻であること |
| 公開のレース結果 | 今回の監査は**開かない** | 結果から新候補を作り直すこと、参考的中を正式認定すること |

合格に見える受領JSONでも `claimed_receiver_receipt_consistent=true` になるだけ。`receiver_receipt_authenticated=false`, `independent_first_receipt_verified=false`, `official_t12_complete_verified=false`, `original_source_independently_verified=false`, `formally_eligible=false`, `production_promotion_allowed=false` を**必ず維持**する。

## 採用前の残作業

1. デフォルトブランチに未登録の研究 `workflow_dispatch` の起動経路を、独立した権限設計と合わせて手動審査する。既存のmainや本番収集フローを自動改変しない。
2. Cloudflare Worker＋D1の実機検証（現時点は未デプロイ）と、管理者と独立した署名・時刻受領証拠を用意する。サーバーの自称JSONだけで正式認定しない。
3. BOAT RACE公式のbeforeinfo/展示6艇・120通りオッズと本当の締切、各原本のT−12前到着と初回保存を独立監査する。存在しない/不正な結果は対象外理由付きで分離する。
4. 2026-11-09以降の新レースのみで事前固定済みの300件pilot、その次の未使用300件confirmationを評価する。Nov6–8参照実績は混ぜない。勝ち/負け、Top1/3/5/10、1・2着ペアの欠落と3着候補の脱落を同一分母で比較する。方法の事後修正は禁止。
5. 必要な独立証拠が揃うまで正式認定はゼロ、モデル・予想・買い目・UI・Render・mainへの反映を禁止する。Draftを維持し、自動統合しない。

## 実行証拠

- [失敗テストrun #42476208940](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42476208940) は1秒境界のテスト入力を誤って1分先にしていたことが原因。テストだけ修正。
- [修正後run #42476312699](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42476312699) **success**。既存Python 49件、SQLite 9件、追加D1照合10件、デフォルトブランチ登録監査8件の各テストは成功。既存Node Workerテストも成功。候補固定・候補アップロードは両方スキップ。
- 同じrunのログでは `DISPATCH_PREREQUISITE False`。main `6b371040fd2fc4398bfa882e6557c333cc0800c8` に研究用 `workflow_dispatch` ワークフローが存在しないことを再確認。

**Main merge: NO. Cloudflare deploy: NO. Research candidate receipt first-acceptance certified: 0. Official T−12 formal cohort: 0.**

# 旧サイト停止・不要物整理の安全判定（2026-10-29）

## 実測
- 旧repo `ikst2512-eng/boat-edge`: `.github/workflows/*.yml` 105ファイル。
- CLEAN `ikst2512-eng/boat-edge-clean`: 同20ファイル。
- PR #184後の実行 40739243140 は成功。原本292件をGitHub blobから再取得し SHA-256を再検証（`verified_legacy_blobs=292`, `all_sha256_valid=true`）。
- PR #185後の実行 40739572811 は確認時点で実行中。圧縮アーカイブからの復元成功は未確定。

## 守るもの
旧原本、旧予想・初回保存時刻の監査証拠、正式Freshの評価証拠、過去の予想コード・ハッシュ、CLEANで再現できないオッズ・払戻金。旧repoの本番更新経路もCLEANの独立稼働と旧URLの利用者影響を調べるまで停止しない。

## 削除の判定
| 区分 | 判定 | 根拠 |
|---|---|---|
| 旧サイトの105 workflow YAML | REVIEW_REQUIRED | スケジュール、最新実行、Secrets、外部参照、他workflowへの依存が未確認。全部を今すぐ削除しない |
| 旧site_results原本 | KEEP | 実際の元バイトを長期独立保管していない |
| 旧予想・監査・Fresh証拠 | KEEP | 締切前の保存時刻と再現性の移行が未完了 |
| CLEANの監査workflow | KEEP | 復元・ハッシュ検証の継続に必要 |
| 確認済み重複に限る追加コピー | SKIP_DUPLICATE_COPY | 元ファイル削除ではなく、余計な複製だけ回避 |
 
## 完了条件
1. PR #185のアーカイブ復元試験で原本292件のSHA-256一致。
2. 保管期限90日のActions artifactとは別の長期保存場所に原本をコピーし、そこから取り出して検証。
3. 旧予想/Freshの証拠に初回Git SHA、時刻、原本 SHA-256、実験条件を紐付け、復元に成功。
4. 旧Actionsの個別稼働・依存関係・旧URL利用を確認。必要なら workflow 単位で停止し、CLEAN単独運用を実測。
5. 上記全条件を満たした対象だけ削除。未検証対象は消さない。

**今回、旧repoのコード・Actions・原本の削除は0件。削除したという主張は禁止。**

## 2026-10-30 旧サイト削除準備の再点検（現行状態）
- CLEAN Pages: 公開ワークフロー `c3666642` は success（直前の失敗を修正したテスト）。
- CLEAN GitHub main: 調査時 `068c2d3f`。CLEAN Render: `boat-edge-clean` は独立リポジトリ main 接続だが、最新の確認済み live deploy は `f9e2fa46`。GitHub mainとの版一致が未証明。Renderが「live」でも最新ソース反映の証明にはならない。
- 旧GitHub repo `ikst2512-eng/boat-edge` は存続中。CLEANのRenderサービス一覧に旧サイトのサービスは見当たらないが、旧Pagesや外部利用の有無は未確認。
- 証拠ギャップ: `docs/legacy-evidence-gap-20261029.md` の旧予想・履歴・raw・odds・結果系列は、CLEAN保存物との完全性・復元性の証明がない。既存アーカイブ検証があっても長期独立保管と完全移行の証明にはならない。

### 廃止作業の順序（安全ゲート）
1. CLEAN Renderを現行mainに一致させ、PagesとRenderの予想・結果・更新API・時刻の実ブラウザ/API試験を成功させる。
2. 旧サイトでしか復元できない締切前予想・正式Fresh原本・初回保存SHA/日時・払戻・入力データを選別し、独立した長期保管先に保存、SHA-256再読出と復元検証を完了する。確認結果はレースコード単位で記録する。
3. 旧サイトのworkflow 105本（過去の観測値）の現在の活動・外部トリガー・他サービス依存・旧URL参照を調べ、書き込み元ごとに停止可否を分類する。
4. 旧更新処理を段階的に止め、CLEAN単独で連続した予想・結果更新および検証が成功することを確認する。停止後に回復できる手順と基準コミットを残す。
5. 旧サイトを先にアーカイブし、閲覧移行案内・リンク先の確認を行う。最終リポジトリ削除は復元証拠・移行完了・利用影響の確認後に別途実施する。

**現判定: DELETE_BLOCKED / 旧repoのコード・Actions・原本・Pagesは今回削除しない。**

## 2026-10-30 追加実測：復元ワークフローと旧サイトの継続実行
- 旧原本のアーカイブ復元を扱うCLEAN workflow実行 `40739572811` は **completed/success**。前節の「実行中」はこの時点で解消。ただし、90日artifactとは別の長期保存や全旧予想・払戻等の網羅性は未証明。
- 旧 `boat-edge` の直近Actionsに、Pages deployment / V133 / 公式 PRE_RESULT 証拠収集 / V250, V251 テストの成功が確認できた。旧サイトは未停止である（全workflowの依存証明ではない）。
- CLEAN Render最新確認済みliveは `f9e2fa46`、CLEAN GitHub mainは確認時 `29351c78`。Render設定は `autoDeploy=yes` だが実際のライブ反映に遅延・欠落がある。自動デプロイが有効なので、コードpush直後の重複手動deployはしない。mainに追従する運用問題の診断が必要。
- 削除判定は引き続き **DELETE_BLOCKED**。旧repoや旧Actionsを停止・削除していない。

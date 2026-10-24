# Fresh予想フィード契約（暫定 v1）

この文書はPR #2のAPI側の受理仕様。予想生成機能の完成や、実レースのFresh認定を意味しない。

## ファイル
- 公開レースキー `YYYYMMDD-JJ-R`（Rは1〜12の整数）。例: `20261024-12-1`
- 固定原本: `fresh_snapshots/YYYYMMDDJJRR.json`、JJ/RRは2桁。例: `fresh_snapshots/202610241201.json`
- `predictions.json` は辞書形式でレースキーに対してAPI表示レコードを格納する

## 原本と配信メタデータ
- 原本JSONには `generated_at`（timezone付きISO8601）、`validated`、`model_version`、`predictions` を含む
- 配信レコードは原本と同じ内容＋`freeze_proof` オブジェクト。ただし `freeze_proof` 自体は原本には含めない
- `freeze_proof`: `commit_sha`（40桁小文字hex）、`path`、`sha256`（原本JSONの**生バイト**SHA-256）、`deadline_at`、`committed_at`（全てtimezone付き）
- 表示前にGitHub commit API、指定コミット配下の固定原本、原本ハッシュ、配信レコードとの一致を確認
- 時刻は `generated_at <= GitHubコミットのcommitter date < deadline_at`、かつ申告 `committed_at` がコミットのcommitter dateと一致
- ここでいうコミット日付はGitのメタデータであり任意設定可能。**独立した公開時刻証明ではない**。実運用のFresh認定にはGitHub Actionsの事前処理実行記録など独立した到達時刻の確認を追加すること
- サイトの `validated:true` は上記フィード検査用フラグであり、監査完了または予想精度の承認を意味しない

## 必須の未完了項目
1. v5の固定JSON形式と本契約の変換・インストールを実装し、実際の原本を生成・commit
2. コミット時刻の独立した証拠を追加（自己申告メタデータだけでFresh採点しない）
3. 結果照合と120通りの分布整合性テスト、正式Freshの母数監査
4. 取得元CSVの各レースについて生成サイクルと締切前の原本取得証拠を残す

研究予想（`status: research`, `validated:false`）を正式予想と混同しないこと。

## Push到達時刻の独立記録（追加）

- `.github/workflows/fresh-snapshot-witness.yml` は `main` 上の `fresh_snapshots/**` 変更を含むpushで起動する。予想を生成せず、結果ファイルにも触れない。
- Github Actions RESTの `run.created_at`、`run.head_sha`、`event=push`、`conclusion=success` と、固定原本のコミットSHAを突合。
- 対象レース締切より `run.created_at` が前であることが必須。締切後に起動したら、たとえコミット時刻が締切前でも失格。
- ワークフローが `main` にマージされていない段階では実運用の証拠にならない。現時点はPR内の未配備実装。
- 実際のスケジューラーと予想生成処理から `fresh_snapshots` をpushする配線は未実装。Github側の記録が成功しても、入力CSVが結果公開前に取得されたことの独立証明は別途必要。

## 2026-10-25 生成元実査と接続判定

- 生成元候補 `ikst2512-eng/boat-edge` の `data/site_prediction_snapshots/20261023-05-01.json` を実査。スキーマ `boat-edge-server-site-final-v123`、`prediction_kind=SITE_REFERENCE_V122`、`mode_policy=PROVISIONAL_V254_THIRD_TAIL10_FIXED_TOP7`。
- 当該記録の `minutes_to_deadline=3.05`。正式FreshのGitHub到達時刻「締切12分前まで」という要件に達しない。元データは `modes.hit` 等の上位買い目リストであり、全120通りの正規化確率を公開するv5原本と同型ではない。
- `site_prediction_snapshots` を `fresh_snapshots` にコピーしたり、上位10点の残確率を均等補完してv5原本を捏造してはならない。サイト暫定モードを固定Freshモデルと誤認してはならない。
- `BOAT_EDGE_V230_FAST_OFFICIAL_PREDEADLINE.yml` は公式ソース取得と別系統の暫定スナップショット生成の処理であり、v5送信元として採用する根拠はまだ確認できない。
- **実運用の接続ブロッカー**：固定モデルによる120通り全確率・原本ハッシュ・実際の締切時刻・独立した入力取得時刻を持つv5生成元が必要。さらに送信用`FRESH_DISPATCH_TOKEN`と公開用`FRESH_PUSH_TOKEN`のGitHub認証設定、mainへのレビュー済み配備、1Rの締切前の実測検証が必要。
- GitHub Actionsテスト成功はコードの回帰テストのみで、実レースFresh取得成功や精度検証ではない。正式採点は現時点 **0R**。

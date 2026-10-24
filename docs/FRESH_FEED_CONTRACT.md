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

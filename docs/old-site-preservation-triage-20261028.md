# 旧BOAT EDGEから必要なものだけ残す：一次抽出表（2026-10-28）

対象: `ikst2512-eng/boat-edge` main。移行先: `ikst2512-eng/boat-edge-clean`。これは**保全の選別表**であり、旧サイト削除・ファイル移行完了の記録ではない。

## A. 必須保全（削除前に実体・完全性確認）

1. 締切前の予想原本、初回Git保存時刻、改訂履歴、予想時のオッズ/出走表/展示等の入力証拠: `data/site_prediction_snapshots/`, `data/site_prediction_audit/`, `data/site_prediction_history/`, `data/site_odds/`。数値だけでなく照合に必要なメタデータも保持。
2. 正式Freshの証拠、事前・事後の分離確認、および結果照合に必要な原本: `data/site_results/`, `data/site_autopilot/` の証拠・凍結・採点サブセット、`data/raw/` の参照先原本。CLEANに移したものはSHA/レースコード/収集時刻で同一性を証明してから重複削除。
3. V13分類の仕様・実データ出力・再現テスト: `scripts/deadline_v9/audit_v13_artifact.py`, `tests/test_deadline_v13_artifact_auditor.py`, `tests/test_deadline_v13_classify.py`。生成先 `page_classification.json` は現時点でmainのtree上に見つかっておらず、Actions artifactも別途確認が必要。
4. 再現に必要な限定的な検証コード: `scripts/fresh_core7_blockers.py`, `scripts/fresh_csv_http_diagnostic.py`, `tests/test_fresh_csv_http_contract.py`, `tests/test_fresh_csv_value_recovery.py`。CLEANへの無条件移植はしない。

## B. 一時保留（CLEANに相当機能があるか確認）

- `data/races/`, `data/early_races/`, `data/site_early_previews/`, `data/site_learning/` は実際の引用・学習依存関係の確認が必要。
- 旧サイトの GitHub Actions 105本は、スケジュール実行・手動トリガー・証拠生成・Pages公開を個別に棚卸しするまで一括削除しない。
- `render.yaml`, Pages公開設定、旧URLの外部利用先を確認するまでインフラ削除はしない。

## C. CLEANへ持ち込まない（原則）

- 旧UI HTML/JS/CSSをCLEAN本体へ上書き移植しない。
- 旧サイト独自の自動デプロイ/自動回復ワークフローを移植しない。
- 重複研究ブランチ、失効したTODOや検証中間生成物は、必要証拠との参照関係が無いことを確認してから削除候補とする。

## 現状の確認値

旧リポジトリ main のGit tree: 約32,978ファイル、`data/` に約32,245ファイル、GitHub Actions設定105本。代表的なデータ群: `data/raw/` 8,051、`data/races/` 3,696、`data/site_results/` 3,366、`data/site_prediction_snapshots/` 2,054、`data/site_prediction_audit/` 1,174、`data/site_prediction_history/` 1,165。これらは**保全候補の全数であって移行必須数ではない**。

## 削除許可ゲート

1. 必須原本とハッシュ/タイムスタンプ/出所を保全し、復元試験を通す。
2. CLEAN独立データ収集・結果・予想・V13等の必要機能を実運用で確認する。
3. 旧Actionsの稼働を止め、CLEANの連続更新に影響しないことを確認する。
4. 外部URL・旧Pages・他サービスの参照を棚卸しした後、旧サイトをアーカイブし、最終削除は別判断。

**このPRでは旧サイトのファイル・Actions・サービスを削除しない。**
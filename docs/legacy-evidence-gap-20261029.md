# 旧BOAT EDGE 証拠保存・CLEAN照合実測（2026-10-29）

対象旧main: `ikst2512-eng/boat-edge` / CLEAN main: `ikst2512-eng/boat-edge-clean`。GitHubのtreeを再帰的に比較した結果。**同名パスがないことと、同じ内容が未移行であることは別**。証拠を削除しない。

| 旧サイトのデータ系列 | 旧mainのファイル数 | CLEANに同じパスのファイル | 扱い |
| --- | ---: | ---: | --- |
| `data/site_prediction_snapshots/` | 2,054 | 0 | 保存必須候補：締切前予想、入力・オッズ履歴との関連を照合 |
| `data/site_prediction_audit/` | 1,174 | 0 | 保存必須候補：監査証拠 |
| `data/site_prediction_history/` | 1,165 | 0 | 保存必須候補：変更履歴・初回保存証拠 |
| `data/site_results/` | 3,397 | 0 | CLEAN確定結果とのレースID・払戻金・出典照合が必要 |
| `data/raw/` | 8,051 | 0 | 予想の再現に使った入力原本を参照関係から選別 |
| `data/site_odds/` | 2,331 | 0 | 予想時刻に紐づくオッズだけを優先保全 |

CLEANで別形式で保持していることを確認した系列: `confirmed_results/` 293件、`four_mode_forecasts/` 133件、`four_mode_performance/` 124件（該当prefix配下のファイル数。原本同一性・対象範囲の一致を意味しない）。

## 実際に抽出・保存を優先する最小セット

- 予想１件ごとに、レースコード・締切・初回保存コミット・原本ハッシュ・全買い目・使用データと収集日時・オッズ・結果・払戻金・検証結果の索引を作る。初回Git SHAを保つ。
- 正式Freshの原本と計測条件・計測対象・採点証拠の索引。研究データは追試可能な範囲のみ。
- V13再現に必要なコードとテスト: `scripts/deadline_v9/classify_pages.py`, `scripts/deadline_v9/audit_v13_artifact.py`, `scripts/deadline_v9/verify_artifacts.py`, `tests/test_deadline_v13_classify.py`。本番への実装移植はCLEAN側の機能・採用判断後。

## 次の削除・移行判定

1. 上記旧データのうちCLEAN予想・結果から参照されるレースと証拠ファイルをIDで結び、索引と検証値を作成する。
2. コピーする場合は元ファイルSHA-256、タイムスタンプ、元Gitパスとcommit IDを添えて**保全専用ディレクトリ**に保存。CLEANの公開予想や自動更新処理には接続しない。
3. 必須原本の完全性・復元性、正式Freshの再現性を確認するまで旧repoを削除しない。
4. 旧GitHub ActionsとPagesの停止はCLEANへの依存と外部URL利用の調査完了後に別途行う。

この記録は棚卸し・ギャップ分析のみ。**データ移行、旧ファイル・Actionsの削除、停止はいずれも実施していない。**

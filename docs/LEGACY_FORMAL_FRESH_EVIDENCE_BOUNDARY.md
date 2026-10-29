# 旧サイトの正式Fresh証拠とCLEAN予想の分離判定（2026-10-30）

目的：旧 `boat-edge` の直接編集をせず、不要な予想ロジックをCLEANに持ち込まず、正式Freshの証拠を誤削除しない。

## 実測済み
- [監査 run 40948388688](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/40948388688) で、レースID共通420、両側に予想原本あり29、上位10点比較29、取得エラー0。
- 29件のモデル識別子は旧 `SITE_REFERENCE_V122`、CLEAN `clean-prospective-national-beta0.4-v1`。同一レースでも予想は同一と見なせない。
- 旧 `data/site_prediction_audit/`、`data/site_prediction_history/`、`data/site_prediction_snapshots/` はサイト専用の予想・監査の原本。旧スナップショットの実例は `scope: SITE_ONLY_NOT_FORMAL_FRESH`。正式Fresh証拠への昇格は禁止。
- [旧 repo docs/C1_MINIMAL_CORE_MIGRATION.md](https://github.com/ikst2512-eng/boat-edge/blob/main/docs/C1_MINIMAL_CORE_MIGRATION.md) に初回Git追加・締切2–10分前・公式入力ソース・独立監査の条件と、旧ワークフローの依存関係調査が指定される。これは移植許可ではない。
- [旧 repo docs/BOAT_EDGE_01_GATE1C_V229_V125_RECEIPT_20261016.md](https://github.com/ikst2512-eng/boat-edge/blob/main/docs/BOAT_EDGE_01_GATE1C_V229_V125_RECEIPT_20261016.md) は履歴証拠に欠損がある場合、過去原本を後付け補完せず不明とする条件を記録。

## 判定
| 対象 | 判定 | 次の条件 |
| --- | --- | --- |
| 旧予想モデル（V122）をCLEANへ移植 | **不要（現行CLEANには採用しない）** | 29レース照合はモデルの非同一性を示す |
| 旧サイト用予想・履歴・監査の29レース原本 | **移植不要、旧repo保持** | 現行CLEAN予想へ上書き・結合しない。旧サイト検証の履歴価値は別途評価 |
| 正式Freshの初回Git原本・入力SHA・時刻・受入監査 | **要保全候補、未選別** | 具体的な原本パス・Git SHA・レース・締切前証明・再現性を突合する |
| 旧 `data/raw/`、旧オッズ、旧結果データ全般 | **必要性未判定** | CLEANの独立ソースで再現できるか、正式Freshの参照鎖があるか確認 |
| 旧ワークフロー・不要ブランチ・Draft PR | **削除未許可** | 実行トリガー、依存する呼び出し、第一原本生成者、復元手段を個別検証 |

## 作業順序
1. 旧repoの正式Fresh / 初回Git凍結の**実ファイル**と参照元を特定（C-1資料だけでは正式Freshの存在を証明できない）。
2. 各証拠に `source_path`、`git_blob_sha`、保存時刻、締切、公式ソースハッシュ、CLEANでの利用有無を記録。
3. 確認済み結果と事前予想の時系列を突合。後付けの的中判定や正式昇格はしない。
4. 消すのはCLEANで不要かつ旧サイトの現役処理・証拠再現から独立し、復元できると**証明できた対象のみ**。削除は別PRで実施。

**この記録自体は削除承認ではない。旧サイトへの変更、データコピー、予想再生成なし。**

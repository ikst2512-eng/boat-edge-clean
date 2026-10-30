# 旧正式Freshの保存先と現状（読取専用調査）

2026-10-30に旧リポジトリの実ファイルを確認。

- `data/formal_status.json` は `prediction_path_template: data/formal_predictions/{race_key}.json` を示す。
- 同状態ファイルで `connected=false`、`predictions_ready=false`、`formalFirst100.races=0`、`freezeManifestSha=null`、`coreSha=null`。2026-10-05の既存cohortは `NOT_ACCEPTED_AS_FORMAL_RESULT`。
- `scripts/site_formal_preflight_v274.py` は `data/formal_predictions/*.json` の100件と承認SHAマップを検査する。ただし**この検査自体は正式Freshの証明ではない**。
- `scripts/site_final_history_v133.py` は `data/formal_predictions` と `data/formal` を旧予想スナップショットとは区別している。
- 3つの候補ファイル `data/formal_predictions/202610300101.json`、`data/formal_predictions/20261005-01-01.json`、`data/formal/20261005-01-01.json` は見つからなかった。これは**全formalディレクトリが空である証明ではない**。
- 旧サイトV123/V125/V229のSITE専用チェーンを正式Freshへ昇格・移植しない。保全対象の一括削除も認めない。

次：旧リポジトリのGit tree全体から `data/formal_predictions/`、`data/formal/`、freeze manifestの実在ファイル、初回Git保存の参照鎖を列挙する。Git初回追加・公式入力・締切前証明を満たしたものだけ正式証拠として検査する。

## 2026-10-30 実行済みGitツリー棚卸し（更新）
- GitHub Actions run [40950644845](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/40950644845) の再試行で、`unit-test` と `audit-evidence` は成功。
- 原本Gitツリーの `data/formal_predictions/` と `data/formal/` に該当する Git blob は **0件**。証拠は Issue [#329](https://github.com/ikst2512-eng/boat-edge-clean/issues/329#issuecomment-6512968248) と保存済み監査artifact。
- 既存の29件の旧・CLEAN予想照合も29件完了、取得失敗0件。レースID一致件数は同一runで440件に増加。
- この0件は**今回のmain Gitツリーの対象パスのみ**の結果であり、過去Git履歴・別格納先や正式Fresh開発の実績全般の不存在は証明しない。
- 旧サイトのV299コード `scripts/boat_edge_v299_workflow_inventory.py` はトリガーと書込候補を識別する既存の読取専用棚卸し実装。旧 `docs/C1_MINIMAL_CORE_MIGRATION.md` は `auto-update.yml`、`site-odds.yml`、`V235.yml`、`BOAT_EDGE_V229_ATOMIC_FREEZE_AUDIT.yml`、`pages-controlled-publish.yml`、`boat-edge-v350-actions-evidence.yml` を**依存調査対象の6候補**として挙げるが、完全な依存網を証明したものではない。
- 現時点で一括削除対象の旧ワークフローは0件。依存関係とCLEAN代替実行の証明が揃った候補のみ別変更で退役させる。

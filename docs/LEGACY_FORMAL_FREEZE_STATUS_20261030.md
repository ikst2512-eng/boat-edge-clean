# 旧正式Freshの保存先と現状（読取専用調査）

2026-10-30に旧リポジトリの実ファイルを確認。

- `data/formal_status.json` は `prediction_path_template: data/formal_predictions/{race_key}.json` を示す。
- 同状態ファイルで `connected=false`、`predictions_ready=false`、`formalFirst100.races=0`、`freezeManifestSha=null`、`coreSha=null`。2026-10-05の既存cohortは `NOT_ACCEPTED_AS_FORMAL_RESULT`。
- `scripts/site_formal_preflight_v274.py` は `data/formal_predictions/*.json` の100件と承認SHAマップを検査する。ただし**この検査自体は正式Freshの証明ではない**。
- `scripts/site_final_history_v133.py` は `data/formal_predictions` と `data/formal` を旧予想スナップショットとは区別している。
- 3つの候補ファイル `data/formal_predictions/202610300101.json`、`data/formal_predictions/20261005-01-01.json`、`data/formal/20261005-01-01.json` は見つからなかった。これは**全formalディレクトリが空である証明ではない**。
- 旧サイトV123/V125/V229のSITE専用チェーンを正式Freshへ昇格・移植しない。保全対象の一括削除も認めない。

次：旧リポジトリのGit tree全体から `data/formal_predictions/`、`data/formal/`、freeze manifestの実在ファイル、初回Git保存の参照鎖を列挙する。Git初回追加・公式入力・締切前証明を満たしたものだけ正式証拠として検査する。
